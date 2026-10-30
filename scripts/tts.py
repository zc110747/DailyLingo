#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""DailyLingo — 调用本地 TTS（EnglishAudio）生成 WAV 的**唯一入口**。

为什么需要这一层，而不是直接 ``eaudio.cmd <md>``
------------------------------------------------
EnglishAudio 只接受 markdown 文件、只读 ``## Article``，并且把正文原样念出来。
对话体文章的正文是脚本式写法：

    **Anna:** Excuse me. Is this the line for check-in?

页面上需要这个「谁在说话」的标签，音频里却**不该把名字念出来** —— 十几行对话连读
十四次 "Anna:"，既不像对话，也把注意力从内容上带走。

所以生成音频前先把 ``## Article`` 里的 ``**名字:**`` 前缀删掉，写到**同名**临时文件
再交给 TTS；WAV 因此仍然落在 ``sources/<同名>.wav``。原 md **一个字不动**
（页面显示、导航、导出全部照旧）。

``scripts/build.py`` 推导句子时间轴时用的是同一份「去掉标签的文本」，否则音节先验
会比音频多出两个音节，句界被拉偏，高亮就串到上一句去了。

用法
----
    python scripts/tts.py content/0076-0100/0082.A_Conversation_at_the_Airport.md
    python scripts/tts.py <md> [<md> ...] [--dist sources] [--tool <eaudio.cmd>]

退出码：0 全部成功；1 有文件失败；2 参数错误。
"""

from __future__ import annotations

import argparse
import os
import re
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent

# 工具已加入系统 PATH，因此**不写任何绝对路径**：各台电脑安装位置不同，写死一条
# 只会在换机后失效。仓库内仍认 tools/eaudio.cmd 作为兜底（可选，默认不进 Git）。
AUDIO_TOOL_ENV = "DAILYLINGO_AUDIO_TOOL"
AUDIO_TOOL_NAMES = ("eaudio.cmd", "EnglishAudio.exe", "EnglishAudio")
AUDIO_TOOL_CANDIDATES = (ROOT / "tools" / "eaudio.cmd",)

# `**Anna:**` / `**Doctor Lin:**` —— 说话人标签。只认行首、大写开头、名字短，
# 这样正文里普通的行内粗体（`**important**`、`**Question 1:**`）不会被误删。
SPEAKER_LABEL_RE = re.compile(r"^\*\*\s*([A-Z][A-Za-z.'\- ]{0,28}?)\s*:\s*\*\*\s*")

# 单篇合成上限：实测 80 s 音频约 20 s，10 分钟足够富余。
TIMEOUT = 600


def resolve_audio_tool(explicit: str | None = None) -> Path | None:
    """返回可直接调用的音频工具路径；找不到返回 None。

    顺序：``explicit`` > 环境变量 ``DAILYLINGO_AUDIO_TOOL`` > 系统 PATH（按名称查找）
    > ``<仓库>/tools/eaudio.cmd``。
    """
    candidates: list[Path] = []
    if explicit:
        candidates.append(Path(explicit))
    from_env = os.environ.get(AUDIO_TOOL_ENV)
    if from_env:
        candidates.append(Path(from_env))
    for name in AUDIO_TOOL_NAMES:
        found = shutil.which(name)
        if found:
            candidates.append(Path(found))
    candidates.extend(AUDIO_TOOL_CANDIDATES)

    for candidate in candidates:
        if candidate.is_file():
            return candidate.resolve()
    return None


def _is_article_heading(line: str) -> bool:
    return re.fullmatch(r"##\s+Article\s*", line.strip(), re.IGNORECASE) is not None


def _is_heading(line: str) -> bool:
    return re.match(r"#{1,6}\s", line.strip()) is not None


def spoken_script(text: str) -> tuple[str, int]:
    """把 ``## Article`` 里行首的说话人标签删掉，其余部分原样返回。

    返回 ``(新全文, 删掉标签的段落数)``。只动 Article：``## Questions`` 里
    也可能有 ``**Question 1:**``，那是题目内容，绝不能碰。
    """
    out: list[str] = []
    inside = False
    replaced = 0
    for line in text.splitlines(keepends=True):
        if _is_heading(line):
            inside = _is_article_heading(line)
            out.append(line)
            continue
        if inside:
            stripped = SPEAKER_LABEL_RE.sub("", line, count=1)
            if stripped != line:
                replaced += 1
            out.append(stripped)
        else:
            out.append(line)
    return "".join(out), replaced


def _command(tool: Path, source: Path, dist: Path) -> list[str]:
    """``.cmd`` / ``.bat`` 必须经 cmd.exe 转一手，exe 直接调。"""
    base = [str(tool), str(source), f"--dist={dist}"]
    if tool.suffix.lower() in (".cmd", ".bat"):
        return ["cmd", "/c", *base]
    return base


def synthesize(
    md_path: Path | str,
    dist_dir: Path | str,
    tool: Path | str | None = None,
    timeout: int = TIMEOUT,
) -> tuple[bool, str]:
    """为单个 md 生成 ``<同名>.wav`` 到 ``dist_dir``。

    返回 ``(是否成功, 说明)``。说明里会带「删掉了几处说话人标签」，方便核对
    对话体文章确实走了预处理。
    """
    resolved = resolve_audio_tool(str(tool) if tool else None)
    if resolved is None:
        return False, (
            "未找到 EnglishAudio（PATH 里既没有 eaudio.cmd 也没有 EnglishAudio.exe）；"
            f"可用 --tool 或环境变量 {AUDIO_TOOL_ENV} 指定"
        )

    md_file = Path(md_path).resolve()
    if not md_file.is_file():
        return False, f"找不到 md 文件：{md_file}"
    dist = Path(dist_dir).resolve()
    dist.mkdir(parents=True, exist_ok=True)

    try:
        text = md_file.read_text(encoding="utf-8")
    except UnicodeDecodeError as exc:
        return False, f"{md_file.name} 不是有效的 UTF-8：{exc}"

    script, replaced = spoken_script(text)
    target = dist / f"{md_file.stem}.wav"

    with tempfile.TemporaryDirectory(prefix="dailylingo-tts-") as tmp:
        source = md_file
        if replaced:
            # 同名临时文件：EnglishAudio 用文件名决定 WAV 名字，改名就前功尽弃
            source = Path(tmp) / md_file.name
            source.write_text(script, encoding="utf-8")
        try:
            proc = subprocess.run(
                _command(resolved, source, dist),
                cwd=str(ROOT),
                capture_output=True,
                text=True,
                timeout=timeout,
            )
        except subprocess.TimeoutExpired:
            return False, f"合成超时（>{timeout}s）"
        except OSError as exc:
            return False, f"启动 {resolved.name} 失败：{exc}"

    if proc.returncode != 0:
        detail = (proc.stderr or proc.stdout or "").strip().splitlines()
        tail = f"：{detail[-1]}" if detail else ""
        return False, f"EnglishAudio 退出码 {proc.returncode}{tail}"
    if not target.is_file():
        return False, "工具报告成功，但没有生成 WAV"

    size_kb = target.stat().st_size / 1024
    note = f"，去掉 {replaced} 处说话人标签" if replaced else ""
    return True, f"{target.name}（{size_kb:.0f} KB{note}）"


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="tts.py",
        description="调用本地 EnglishAudio 生成 WAV；对话体文章自动不念说话人名字。",
    )
    parser.add_argument("markdown", nargs="+", help="要生成音频的 md 文件")
    parser.add_argument(
        "--dist",
        default=str(ROOT / "sources"),
        help="WAV 输出目录（默认 sources/）",
    )
    parser.add_argument(
        "--tool",
        default=None,
        help=f"eaudio.cmd 路径；也可用环境变量 {AUDIO_TOOL_ENV} 指定",
    )
    args = parser.parse_args(argv)

    failures = 0
    for name in args.markdown:
        path = Path(name)
        ok, detail = synthesize(path, args.dist, args.tool)
        mark = "[ok]" if ok else "[FAIL]"
        print(f"{mark} {path.name} -> {detail}", flush=True)
        if not ok:
            failures += 1
    return 0 if failures == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
