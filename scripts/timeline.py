#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""DailyLingo — 句子级音频时间轴（朗读到哪句就把哪句标粗）。

问题
----
站点是纯静态的，WAV 由外部 TTS 工具（EnglishAudio / Piper）生成，**不提供任何时间戳**，
而网页端要做「读到哪句高亮哪句」就必须知道每句话在音频里的起止时间。

解法
----
TTS 在句子之间会留下明显停顿（实测 0.10–0.47 s），逗号/短语内的停顿更短。于是：

1. 用 10 ms 峰值包络求「有声 / 静音」；
2. 找出所有静音段作为**候选边界**；
3. 以「文本音节数」为时长先验做动态规划，选出恰好 N-1 个边界（N = 句子数）：
   边界落在停顿上给奖励、落在网格上给惩罚，同时惩罚偏离先验位置。

**不用固定比例切分**：语速并不严格正比于字符数，比例切分在长文里会累积漂移
（28 句的篇目末句实测偏差 > 2 s，肉眼可见错句）。

只依赖标准库（``wave`` / ``array`` / ``re``）。整篇 80 s 的音频转包络约 0.1 s，
20 篇全量构建的额外开销 ≈ 1 s，可以直接挂在构建流程里（watch 也能接受）。

可复现性：全部是确定性算术，同一份 WAV + 同一份文本 ⇒ 同一份时间轴。
"""

from __future__ import annotations

import array
import re
import wave
from pathlib import Path
from typing import Sequence

# --------------------------------------------------------------------------
# 参数（改这里就能调手感；括号内为实测依据）
# --------------------------------------------------------------------------

FRAME_MS = 10.0        # 包络帧长。10 ms 足够分辨 0.1 s 级停顿，又让 80 s 音频只需 8000 帧
SILENCE_REL = 0.03     # 静音阈值 = 全文峰值 × 3%（1%–8% 之间边界判定稳定，取中偏稳）
MIN_GAP_MS = 100       # < 0.1 s 的凹陷不算停顿（词内爆破音 / 齿音常出现）
BRIDGE_MS = 30         # 相邻静音段间 ≤ 30 ms 的杂音视为同一段（避免停顿被劈成两半）
FALLBACK_GRID_MS = 200  # 停顿不够用时退回的候选网格（正常文章走不到这条路径）
SEGMENT_WEIGHT = 2.0   # 每句「有声时长」偏差 1 s 的代价
PAUSE_BONUS = 0.60     # 落在停顿中心的奖励（× 停顿长度，0.5 s 封顶），只用于同等代价时选更深的停顿
OFF_PAUSE_PENALTY = 1.20  # 边界落在连续语音里（退回网格时才会出现）的代价

# 峰值包络阈值 = 峰值 × SILENCE_REL 时，TTS 的句间停顿会整段被识别出来；
# 但停顿内部常混入 -60 dB 级的残余噪声，所以这里按「帧峰值」而不是「帧 RMS」判定，
# 对残余噪声更宽容（RMS 会被少数几个采样点拉高）。

_ABBREVIATIONS = {
    "mr", "mrs", "ms", "dr", "st", "prof", "sr", "jr", "vs", "etc",
    "e.g", "i.e", "a.m", "p.m", "no", "fig", "mt", "inc", "ltd",
}

_OPEN_QUOTES = "\u201c"
_CLOSE_QUOTES = "\u201d"


# --------------------------------------------------------------------------
# 句子切分
# --------------------------------------------------------------------------


def split_sentences(text: str) -> list[str]:
    """按句末标点切句，返回原文顺序的句子列表（已去掉首尾空白）。

    两条必须处理的边界（都真实出现在本项目文章里）：

    1. **引号内的句末标点不是句子边界**：
       ``Tom says, “Good morning, Mrs. Green! Can I help you?”`` 是一句 —— TTS 会把它
       读成一整段（中间确实有停顿，但那是引号内的句号造成的，不是换句）；
    2. **缩写后的点不是句末**：``Mrs.`` / ``Dr.`` / ``a.m.`` 等。

    保证：``" ".join(split_sentences(t)) == " ".join(t.split())``，
    构建侧据此校验切分没有吞字或重复（否则时间轴会整体错位）。
    切完还会把「引号 + 短叙述语」并回一句，见 :func:`_merge_quote_attributions`。
    """
    normalized = " ".join(text.split())
    if not normalized:
        return []

    out: list[str] = []
    depth = 0
    start = 0
    i = 0
    n = len(normalized)

    while i < n:
        ch = normalized[i]
        if ch in _OPEN_QUOTES:
            depth += 1
        elif ch in _CLOSE_QUOTES:
            depth = max(0, depth - 1)
        elif ch == '"':
            depth = 0 if depth else 1
        elif ch in ".!?":
            j = i + 1
            # 连着的句末标点（?!、"..."）和紧随其后的收尾引号都算在句子内
            while j < n and normalized[j] in '.!?\u201d")':
                if normalized[j] in _CLOSE_QUOTES or normalized[j] == '"':
                    depth = max(0, depth - 1)
                j += 1
            tail_word = re.search(r"([A-Za-z.]+)$", normalized[max(0, i - 20):i])
            is_abbr = bool(tail_word) and tail_word.group(1).rstrip(".").lower() in _ABBREVIATIONS
            at_boundary = j >= n or normalized[j] == " "
            if depth <= 0 and at_boundary and not is_abbr:
                piece = normalized[start:j].strip()
                if piece:
                    out.append(piece)
                start = j
            i = j
            continue
        i += 1

    rest = normalized[start:].strip()
    if rest:
        out.append(rest)
    return _merge_quote_attributions(out)


def _merge_quote_attributions(sentences: list[str]) -> list[str]:
    """把紧跟在引号后的短叙述语并回引号句。

    ``“Oh no! Where is my ticket?” she says.`` 在书面上是两句，但 TTS 会把
    ``she says.`` 紧贴着引号读出来 —— **中间没有停顿**，边界在音频里根本不可观测。
    若硬切成两句，DP 只能把这个边界塞到别处，后面整段的对应关系随之错位
    （实测 0020 因此出现「13 个音节挤进 1.17 秒」）。

    判据：前一句以收尾引号结束，且当前句 ≤ 6 个词（叙述语极少超过 6 个词）。
    """
    merged: list[str] = []
    for sentence in sentences:
        if (
            merged
            and merged[-1].rstrip()[-1:] in ('\u201d', '"')
            and len(sentence.split()) <= 6
        ):
            merged[-1] = merged[-1] + " " + sentence
        else:
            merged.append(sentence)
    return merged


def split_sentences_checked(text: str) -> list[str]:
    """切句并自检字面覆盖；对不上就返回空列表（宁可不高亮，也不要把时间轴错位）。"""
    sentences = split_sentences(text)
    if not sentences:
        return []
    if " ".join(sentences) != " ".join(text.split()):
        return []
    return sentences


def estimate_syllables(text: str) -> int:
    """粗估音节数，作为 TTS 时长先验。

    只服务于「句子之间谁更长」的相对比较，不需要精确：元音字母组数近似音节数，
    词尾不发音的 ``e`` 扣掉一个。数字/符号按 1 个音节计（TTS 会逐位或按词读出）。
    """
    total = 0
    for raw in text.split():
        word = re.sub(r"[^a-z']", "", raw.lower())
        if not word:
            total += 1
            continue
        groups = len(re.findall(r"[aeiouy]+", word))
        if word.endswith("e") and not word.endswith(("le", "ee")) and groups > 1:
            groups -= 1
        total += max(1, groups)
    return max(total, 1)


# --------------------------------------------------------------------------
# 音频包络与静音段
# --------------------------------------------------------------------------


def _read_mono_pcm(path: Path) -> tuple[array.array, int] | None:
    """读取 16 bit PCM，立体声取两声道均值；其它位深返回 None（不支持就不高亮）。"""
    try:
        with wave.open(str(path), "rb") as wav:
            if wav.getsampwidth() != 2:
                return None
            channels = wav.getnchannels()
            rate = wav.getframerate()
            raw = wav.readframes(wav.getnframes())
    except (OSError, EOFError, wave.Error):
        return None
    samples = array.array("h")
    samples.frombytes(raw)
    if channels > 1:
        samples = array.array("h", [
            sum(samples[i:i + channels]) // channels
            for i in range(0, len(samples) - channels + 1, channels)
        ])
    return samples, rate


def speech_envelope(path: Path | str) -> tuple[list[int], float] | None:
    """返回 (每帧峰值包络, 帧长秒)。帧峰值比帧 RMS 更能忽略停顿里的 -60 dB 残余噪声。"""
    loaded = _read_mono_pcm(Path(path))
    if loaded is None:
        return None
    samples, rate = loaded
    if not samples or rate <= 0:
        return None
    hop = max(1, int(rate * FRAME_MS / 1000.0))
    envelope = [
        max(map(abs, samples[i:i + hop]))
        for i in range(0, len(samples) - hop + 1, hop)
    ]
    if not envelope:
        return None
    return envelope, hop / float(rate)


def _threshold(envelope: Sequence[int]) -> float:
    return (max(envelope) or 1) * SILENCE_REL


def _voiced_counter(envelope: Sequence[int], frame_seconds: float):
    """返回 ``f(t) -> 截至 t 秒的有声时长``（单调、前缀和）。

    先验比对放在「有声时长」空间里：句内的逗号停顿会把墙钟时长拉长，
    用墙钟时长做先验会系统性地把边界推向长句一侧。
    """
    threshold = _threshold(envelope)
    cumulative = [0] * (len(envelope) + 1)
    for i, value in enumerate(envelope):
        cumulative[i + 1] = cumulative[i] + (1 if value >= threshold else 0)
    last = len(envelope) - 1

    def voiced_upto(seconds: float) -> float:
        index = int(round(seconds / frame_seconds))
        index = 0 if index < 0 else (last if index > last else index)
        return cumulative[index] * frame_seconds

    return voiced_upto


def silence_gaps(envelope: Sequence[int], frame_seconds: float) -> list[tuple[float, float, float]]:
    """把低于阈值的连续帧合并成静音段，返回 [(起始秒, 结束秒, 时长秒)]。"""
    threshold = _threshold(envelope)
    minimum = MIN_GAP_MS / 1000.0
    bridge = BRIDGE_MS / 1000.0

    runs: list[list[float]] = []
    i = 0
    total = len(envelope)
    while i < total:
        if envelope[i] < threshold:
            j = i
            while j < total and envelope[j] < threshold:
                j += 1
            start, end = i * frame_seconds, j * frame_seconds
            if runs and start - runs[-1][1] < bridge:
                runs[-1][1] = end
            else:
                runs.append([start, end])
            i = j
        else:
            i += 1
    return [(a, b, b - a) for a, b in runs if b - a >= minimum]


# --------------------------------------------------------------------------
# 边界对齐（动态规划）
# --------------------------------------------------------------------------


def align_boundaries(
    weights: Sequence[int],
    gaps: Sequence[tuple[float, float, float]],
    speech_start: float,
    speech_end: float,
    voiced_upto=None,
) -> list[float]:
    """为 N 句选出 N-1 个边界时刻。

    候选边界 = 静音段中心（停顿不足时才退回 GRID_MS 网格）。候选只取停顿中心有两个理由：
    1. 听感上的句子起点就是停顿；落在连续语音里的边界会在朗读中途跳字；
    2. 若干个候选挤在同一次长停顿里会切出「全是静音」的空段（实测出现过 1.24 s 里
       只有 0.08 s 有声的句子）。停顿是原子单位 —— 一个停顿最多承载一个边界。

    代价按**每一段**算（``Σ|该句有声时长 - 音节数比例 × 总有声时长|``），
    而不是按「边界位置的累计偏差」算：累计口径允许把某句压扁、再用邻近句的漂移抵消，
    实测会把 13 个音节塞进 0.87 s。逐段口径没有这个漏洞。

    用**有声时长**而不是墙钟时长：句内逗号停顿会把墙钟时长拉长，
    用墙钟时长做先验会系统性地把边界推向长句一侧。
    """
    count = len(weights)
    if count <= 1 or speech_end <= speech_start:
        return []
    if voiced_upto is None:
        voiced_upto = lambda t: t  # noqa: E731 — 退化为墙钟时长

    span = speech_end - speech_start
    total = float(sum(weights)) or 1.0
    voiced_total = max(voiced_upto(speech_end) - voiced_upto(speech_start), 1e-6)
    # expected[k] = 第 k 句（0 起）应占的有声时长
    expected = [voiced_total * w / total for w in weights]

    candidates: list[tuple[float, float, float]] = []  # (时刻, 惩罚, 累计有声时长)
    start_voiced = voiced_upto(speech_start)
    for start, end, duration in gaps:
        if end <= speech_start or start >= speech_end:
            continue
        moment = (start + end) / 2.0
        candidates.append((moment, -min(duration, 0.5) * PAUSE_BONUS, voiced_upto(moment) - start_voiced))
    if len(candidates) < count - 1:
        # 停顿不够用（读得极连贯 / 音频被裁剪过）：退回网格，边界只能近似
        step = FALLBACK_GRID_MS / 1000.0
        for k in range(1, int(span / step)):
            moment = speech_start + k * step
            candidates.append((moment, OFF_PAUSE_PENALTY, voiced_upto(moment) - start_voiced))
    candidates.sort()
    if len(candidates) < count - 1:
        return []

    times = [c[0] for c in candidates]
    penalties = [c[1] for c in candidates]
    voiced = [c[2] for c in candidates]
    audible = voiced_upto(speech_end) - start_voiced
    limit = len(candidates)
    rows = count - 1  # 需要放置的边界数
    infinity = float("inf")

    def segment_cost(voiced_from: float, voiced_to: float, sentence_index: int) -> float:
        return SEGMENT_WEIGHT * abs((voiced_to - voiced_from) - expected[sentence_index])

    # 第 1 个边界：句 0 = [speech_start, 边界)
    cost = [[infinity] * limit for _ in range(rows)]
    back = [[-1] * limit for _ in range(rows)]
    for j in range(limit):
        cost[0][j] = segment_cost(0.0, voiced[j], 0) + penalties[j]

    for k in range(1, rows):
        previous = cost[k - 1]
        for j in range(k, limit):
            best, best_index = infinity, -1
            for i in range(k - 1, j):
                if previous[i] == infinity:
                    continue
                candidate_cost = previous[i] + segment_cost(voiced[i], voiced[j], k)
                if candidate_cost < best:
                    best, best_index = candidate_cost, i
            if best_index >= 0:
                cost[k][j] = best + penalties[j]
                back[k][j] = best_index

    # 最后一段：句 N-1 = [最后一个边界, speech_end)
    best_total, last_index = infinity, -1
    for j in range(rows - 1, limit):
        if cost[rows - 1][j] == infinity:
            continue
        total_cost = cost[rows - 1][j] + segment_cost(voiced[j], audible, count - 1)
        if total_cost < best_total:
            best_total, last_index = total_cost, j
    if last_index < 0:
        return []

    chosen: list[int] = []
    index = last_index
    for k in range(rows - 1, -1, -1):
        chosen.append(index)
        index = back[k][index] if k else -1
        if index < 0 and k:
            return []
    chosen.reverse()
    return [times[j] for j in chosen]


# --------------------------------------------------------------------------
# 对外接口
# --------------------------------------------------------------------------


# 进程内缓存：watch.py 每秒可能重建一次，而一篇 80 s 音频的分析要 ~50 ms。
# 键里带 WAV 的大小/mtime 和句子内容 —— 任何输入变化都会换键，结果与不缓存完全一致。
_CACHE: dict[tuple[str, int, int, int], list[tuple[float, float]]] = {}


def clear_cache() -> None:
    _CACHE.clear()


def build_timeline(wav_path: Path | str, sentences: Sequence[str]) -> list[tuple[float, float]]:
    """返回每句话的 (start, end)，与 ``sentences`` 一一对应；无法分析时返回空列表。

    约定：
    * 首句 start = 0、末句 end = 音频总长 —— 片头/片尾静音期间也算在首末句里，
      避免「刚开始播放却一句都不高亮」的空窗；
    * 相邻句子首尾相接（``end[i] == start[i + 1]``），前端只需按 start 二分定位；
    * 时间保留两位小数（10 ms 精度，与包络帧长同量级）。
    """
    sentences = list(sentences)
    if not sentences:
        return []
    path = Path(wav_path)
    key = None
    try:
        stat = path.stat()
        if not path.is_file():
            return []
        key = (str(path.resolve()), stat.st_size, stat.st_mtime_ns, hash(tuple(sentences)))
        cached = _CACHE.get(key)
        if cached is not None:
            return list(cached)
    except OSError:
        return []

    profile = speech_envelope(path)
    if profile is None:
        return []
    envelope, frame_seconds = profile
    duration = len(envelope) * frame_seconds

    gaps = silence_gaps(envelope, frame_seconds)
    if gaps and gaps[0][0] <= frame_seconds:
        speech_start = gaps[0][1]
    else:
        # 开头直接出声 / 开头没有整段静音：从 0 起算，交界处再细化
        speech_start = 0.0
    if gaps and gaps[-1][1] >= duration - frame_seconds:
        speech_end = gaps[-1][0]
    else:
        speech_end = duration

    if speech_end <= speech_start:
        speech_start, speech_end = 0.0, duration

    weights = [estimate_syllables(s) for s in sentences]
    boundaries = align_boundaries(
        weights, gaps, speech_start, speech_end, _voiced_counter(envelope, frame_seconds)
    )

    starts = [0.0] + boundaries
    ends = boundaries + [duration]
    if len(starts) != len(sentences):
        return []

    timeline: list[tuple[float, float]] = []
    previous = 0.0
    for start, end in zip(starts, ends):
        start = max(round(start, 2), previous)
        end = max(round(end, 2), start + 0.01)
        timeline.append((start, end))
        previous = start
    # 收尾对齐：最后一句覆盖到音频结束
    timeline[-1] = (timeline[-1][0], max(timeline[-1][1], round(duration, 2)))
    if key is not None:
        _CACHE[key] = timeline
    return list(timeline)


def syllables_per_second(sentences: Sequence[str], timeline: Sequence[tuple[float, float]]) -> list[float]:
    """每句话的实际语速（音节/秒），供构建脚本做「对齐是否可疑」的自检。"""
    rates: list[float] = []
    for sentence, (start, end) in zip(sentences, timeline):
        span = end - start
        rates.append(estimate_syllables(sentence) / span if span > 0 else 0.0)
    return rates
