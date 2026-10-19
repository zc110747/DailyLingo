# -*- coding: utf-8 -*-
"""句子时间轴（朗读高亮）的自动化测试。

覆盖四层：

1. **切句**：缩写 / 引号内的句末标点 / 对白后的短叙述语；
2. **静音检测**：现场合成的 WAV，停顿位置已知，逐段比对；
3. **动态规划选边界**：停顿数量多于句子时，边界要落到「最接近音节比例」的那个停顿上；
4. **构建集成**：页面里是否真的输出了 ``data-start`` / ``data-end``，缺音频时是否退回纯段落。

音频全部现场合成（16 kHz 单声道 16 bit 正弦音 + 静音），不依赖 ``sources/`` 里已有的 WAV；
另有一组用例只用真实文章 + 真实音频做「结构一致性」检查（没有音频就自动跳过）。
"""

from __future__ import annotations

import array
import math
import re
import wave
from pathlib import Path

import pytest

import build
import timeline

ROOT = Path(__file__).resolve().parent.parent
CONTENT = ROOT / "content"
SOURCES = ROOT / "sources"


# --------------------------------------------------------------------------
# 工具
# --------------------------------------------------------------------------


def write_wav(path: Path, segments: list[tuple[str, float]], rate: int = 16000) -> Path:
    """按 ``[("tone", 1.0), ("silence", 0.3), ...]`` 合成一段 WAV。"""
    frames = array.array("h")
    for kind, seconds in segments:
        count = int(rate * seconds)
        if kind == "tone":
            frames.extend(
                int(12000 * math.sin(2 * math.pi * 220 * i / rate)) for i in range(count)
            )
        else:
            frames.extend([0] * count)
    with wave.open(str(path), "wb") as wav:
        wav.setnchannels(1)
        wav.setsampwidth(2)
        wav.setframerate(rate)
        wav.writeframes(frames.tobytes())
    return path


def paragraph_sentences(text: str) -> list[str]:
    return timeline.split_sentences_checked(text)


# 三个音块 / 两段 0.3 s 停顿：句子边界应当落在 1.15 s 与 3.45 s（停顿中心）
THREE_BURSTS = [("tone", 1.0), ("silence", 0.3), ("tone", 2.0), ("silence", 0.3), ("tone", 1.0)]
THREE_SENTENCES = [
    "One two three.",
    "One two three four five six.",
    "One two three.",
]


# --------------------------------------------------------------------------
# 1. 切句
# --------------------------------------------------------------------------


def test_split_basic_sentences():
    assert timeline.split_sentences("My name is David. I am thirty. Do you agree?") == [
        "My name is David.",
        "I am thirty.",
        "Do you agree?",
    ]


def test_split_keeps_abbreviations_together():
    sentences = timeline.split_sentences("His neighbor, Mrs. Green, is very kind. Dr. Smith agrees.")
    assert sentences == ["His neighbor, Mrs. Green, is very kind.", "Dr. Smith agrees."]


def test_split_does_not_break_inside_quotes():
    text = "Tom says, \u201cGood morning, Mrs. Green! Can I help you?\u201d"
    assert timeline.split_sentences(text) == [text]


def test_attribution_after_quote_is_merged():
    text = "\u201cOh no! Where is my ticket?\u201d she says."
    assert timeline.split_sentences(text) == [text]


def test_long_sentence_after_quote_is_not_merged():
    text = "\u201cWhat a lovely day!\u201d Lucy says. Lucy and her family go home together."
    assert timeline.split_sentences(text) == [
        "\u201cWhat a lovely day!\u201d Lucy says.",
        "Lucy and her family go home together.",
    ]


@pytest.mark.parametrize("path", sorted(CONTENT.glob("*.md")), ids=lambda p: p.stem)
def test_split_is_lossless_on_real_articles(path: Path):
    """切句不允许吞字/重复 —— 否则时间轴会整体错位。"""
    text = path.read_text(encoding="utf-8")
    body = re.search(r"^##\s+Article\s*$(.*?)(?=^##\s|\Z)", text, re.S | re.M)
    assert body is not None, f"{path.name} 缺少 Article 区"
    for raw in [p for p in re.split(r"\n\s*\n", body.group(1)) if p.strip()]:
        paragraph = " ".join(raw.split())
        sentences = timeline.split_sentences_checked(paragraph)
        assert sentences, f"{path.name} 的段落切句自检失败：{paragraph[:40]}"
        assert " ".join(sentences) == paragraph


@pytest.mark.parametrize(
    "text, expected",
    [
        ("the", 1),
        ("beautiful", 3),
        ("tree", 1),
        ("computer", 3),
        ("", 1),
    ],
)
def test_estimate_syllables(text, expected):
    assert timeline.estimate_syllables(text) == expected


# --------------------------------------------------------------------------
# 2. 静音检测
# --------------------------------------------------------------------------


def test_silence_gaps_found(tmp_path):
    wav = write_wav(tmp_path / "a.wav", THREE_BURSTS)
    profile = timeline.speech_envelope(wav)
    assert profile is not None
    envelope, frame = profile
    gaps = timeline.silence_gaps(envelope, frame)
    assert len(gaps) == 2
    for gap, expected in zip(gaps, (1.0, 3.3)):
        assert gap[0] == pytest.approx(expected, abs=0.03)
        assert gap[2] == pytest.approx(0.3, abs=0.03)


def test_envelope_rejects_non_16bit(tmp_path):
    path = tmp_path / "8bit.wav"
    with wave.open(str(path), "wb") as wav:
        wav.setnchannels(1)
        wav.setsampwidth(1)
        wav.setframerate(8000)
        wav.writeframes(b"\x80" * 800)
    assert timeline.speech_envelope(path) is None
    assert timeline.build_timeline(path, ["One."]) == []


def test_envelope_rejects_missing_file(tmp_path):
    assert timeline.build_timeline(tmp_path / "nope.wav", ["One."]) == []


# --------------------------------------------------------------------------
# 3. 动态规划
# --------------------------------------------------------------------------


def test_align_picks_pause_closest_to_syllable_ratio():
    """两句话、两个停顿：音节比 1:3 时该挑靠近 1/4 有声时长的那个停顿。"""
    gaps = [(1.0, 1.3, 0.3), (2.0, 2.3, 0.3)]
    boundaries = timeline.align_boundaries([1, 3], gaps, 0.0, 5.0)
    assert boundaries == [pytest.approx(1.15, abs=0.02)]


def test_align_falls_back_to_grid_without_pauses():
    """完全没有停顿（读得极连贯）时退回网格：仍给 N-1 个边界，只是位置靠比例估。"""
    boundaries = timeline.align_boundaries([1, 1, 1], [], 0.0, 3.0)
    assert len(boundaries) == 2
    assert boundaries[0] == pytest.approx(1.0, abs=0.2)
    assert boundaries[1] == pytest.approx(2.0, abs=0.2)


def test_align_returns_empty_for_zero_length_speech():
    assert timeline.align_boundaries([1, 1], [(1.0, 1.3, 0.3)], 2.0, 2.0) == []


def test_align_single_sentence_has_no_boundary():
    assert timeline.align_boundaries([5], [(1.0, 1.3, 0.3)], 0.0, 3.0) == []


# --------------------------------------------------------------------------
# 4. 时间轴整体
# --------------------------------------------------------------------------


def test_timeline_matches_known_pause_positions(tmp_path):
    wav = write_wav(tmp_path / "b.wav", THREE_BURSTS)
    result = timeline.build_timeline(wav, THREE_SENTENCES)
    assert len(result) == 3
    starts = [start for start, _end in result]
    assert starts[0] == 0.0
    assert starts[1] == pytest.approx(1.15, abs=0.02)
    assert starts[2] == pytest.approx(3.45, abs=0.02)
    # 首尾相接且覆盖整段音频
    for (_a, end), (start, _b) in zip(result, result[1:]):
        assert end == start
    assert result[-1][1] == pytest.approx(4.6, abs=0.02)


def test_timeline_single_sentence_covers_audio(tmp_path):
    wav = write_wav(tmp_path / "c.wav", [("tone", 1.0), ("silence", 0.2)])
    assert timeline.build_timeline(wav, ["Only one sentence."]) == [(0.0, 1.2)]


def test_timeline_is_stable_and_cached(tmp_path):
    wav = write_wav(tmp_path / "d.wav", THREE_BURSTS)
    first = timeline.build_timeline(wav, THREE_SENTENCES)
    second = timeline.build_timeline(wav, THREE_SENTENCES)
    assert first == second
    timeline.clear_cache()
    assert timeline.build_timeline(wav, THREE_SENTENCES) == first


def test_syllables_per_second_reports_zero_for_empty_window():
    assert timeline.syllables_per_second(["a b"], [(1.0, 1.0)]) == [0.0]


# --------------------------------------------------------------------------
# 5. 真实文章 × 真实音频：结构一致性
# --------------------------------------------------------------------------


@pytest.mark.parametrize("path", sorted(CONTENT.glob("*.md")), ids=lambda p: p.stem)
def test_real_article_timeline_is_consistent(path: Path):
    wav = SOURCES / f"{path.stem}.wav"
    if not wav.is_file():
        pytest.skip("缺少音频，跳过时间轴一致性检查")
    text = path.read_text(encoding="utf-8")
    body = re.search(r"^##\s+Article\s*$(.*?)(?=^##\s|\Z)", text, re.S | re.M)
    sentences = [
        sentence
        for raw in [p for p in re.split(r"\n\s*\n", body.group(1)) if p.strip()]
        for sentence in timeline.split_sentences(" ".join(raw.split()))
    ]
    result = timeline.build_timeline(wav, sentences)
    assert len(result) == len(sentences)
    with wave.open(str(wav), "rb") as handle:
        duration = handle.getnframes() / float(handle.getframerate())
    assert result[0][0] == 0.0
    assert result[-1][1] == pytest.approx(duration, abs=0.02)
    for (start, end), (next_start, _next_end) in zip(result, result[1:]):
        assert start < end
        assert end == next_start


# --------------------------------------------------------------------------
# 6. 构建集成
# --------------------------------------------------------------------------


ARTICLE_MD = """# Three Sentences

## Article

One two three. One two three four five six. One two three.

## Words

| Word | IPA | Meaning |
| --- | --- | --- |
| **three** | /θriː/ | 三 |

## Questions

Question 1：How many sentences?

A. One.

B. Three.

C. Ten.

## Answers

1\\. **B. Three.**
"""


def build_site(tmp_path: Path, with_audio: bool):
    content = tmp_path / "content"
    content.mkdir()
    (content / "0001.Three_Sentences.md").write_text(ARTICLE_MD, encoding="utf-8", newline="\n")
    sources = tmp_path / "sources"
    sources.mkdir()
    if with_audio:
        write_wav(sources / "0001.Three_Sentences.wav", THREE_BURSTS)
    out = tmp_path / "out"
    result = build.build_site(content, out, sources)
    return result, out / "src" / "0001.Three_Sentences.html"


def test_build_emits_sentence_timeline(tmp_path):
    result, page = build_site(tmp_path, with_audio=True)
    html = page.read_text(encoding="utf-8")
    assert result.warnings == []
    assert html.count('class="sentence"') == 3
    assert 'data-start="0.00"' in html
    assert "reading-hint" not in html  # 正文上方不放使用提示，避免干扰阅读
    article = result.articles[0]
    assert len(article.sentence_timeline) == 3
    assert len(article.sentence_paragraphs) == 1


def test_build_without_audio_keeps_plain_paragraphs(tmp_path):
    result, page = build_site(tmp_path, with_audio=False)
    html = page.read_text(encoding="utf-8")
    assert 'class="sentence"' not in html
    assert "data-start" not in html
    assert '<p>One two three. One two three four five six. One two three.</p>' in html
    assert any("缺少音频" in w for w in result.warnings)
