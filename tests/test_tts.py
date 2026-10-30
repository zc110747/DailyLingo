# -*- coding: utf-8 -*-
"""TTS 调用层（``scripts/tts.py``）的测试。

覆盖：对话体说话人标签的剥离范围（只动 ``## Article``）、非对话文章逐字不变、
工具查找顺序，以及「合成前把去掉标签的文本交给 TTS」这条端到端契约
（用一个假工具记录它实际读到的内容，因此不需要真的装 EnglishAudio）。
"""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

import tts


DIALOGUE_MD = """# A Conversation

## Article

**Anna:** Excuse me. Is this the line?

**Man:** Yes, it is.

## Questions

**Question 1:** Where is Anna?

A. At a hotel

## Answers

1. **B. At an airport.**
"""

PLAIN_MD = """# A Plain Story

## Article

This story has no speaker labels at all.

## Questions

**Question 1:** What is it?
"""

# 假 TTS：把「它实际读到的 md 全文」写到 dist/seen.txt，并造一个同名 WAV。
# 这样断言的是**送给工具的内容**，而不是我们自己写进临时文件的猜测。
FAKE_TOOL = """import pathlib
import sys

src = pathlib.Path(sys.argv[1])
dist = pathlib.Path(next(a for a in sys.argv[1:] if a.startswith("--dist=")).split("=", 1)[1])
dist.mkdir(parents=True, exist_ok=True)
(dist / (src.stem + ".wav")).write_bytes(b"RIFF")
(dist / "seen.txt").write_text(src.read_text(encoding="utf-8"), encoding="utf-8")
"""


def _fake_tool(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    tool = tmp_path / "fake_tts.py"
    tool.write_text(FAKE_TOOL, encoding="utf-8", newline="\n")
    monkeypatch.setattr(
        tts,
        "_command",
        lambda binary, source, dist: [sys.executable, str(binary), str(source), f"--dist={dist}"],
    )
    return tool


# --------------------------------------------------------------------------
# 说话人标签
# --------------------------------------------------------------------------


def test_dialogue_labels_removed_from_article():
    script, replaced = tts.spoken_script(DIALOGUE_MD)
    assert replaced == 2
    body = script.split("## Article")[1]
    assert "**Anna:**" not in body and "**Man:**" not in body
    assert "Excuse me. Is this the line?" in body


def test_questions_section_untouched():
    """``## Questions`` 里的 ``**Question 1:**`` 是题目内容，绝不能被当标签删掉。"""
    script, _ = tts.spoken_script(DIALOGUE_MD)
    assert "**Question 1:** Where is Anna?" in script
    assert "1. **B. At an airport.**" in script


def test_plain_article_is_byte_identical():
    script, replaced = tts.spoken_script(PLAIN_MD)
    assert replaced == 0
    assert script == PLAIN_MD


def test_idempotent():
    once, _ = tts.spoken_script(DIALOGUE_MD)
    twice, replaced = tts.spoken_script(once)
    assert replaced == 0
    assert twice == once


@pytest.mark.parametrize(
    "line",
    [
        "**important:** this is bold, not a speaker\n",  # 小写开头
        "**A Very Long Speaker Name Indeed:** hello\n",  # 超过 28 字符
        "Anna: no bold markers here\n",  # 没有 markdown 粗体
        "**Anna** spoke first.\n",  # 没有冒号
    ],
)
def test_non_label_lines_kept(line: str):
    md = f"# T\n\n## Article\n\n{line}"
    script, replaced = tts.spoken_script(md)
    assert replaced == 0
    assert line in script


def test_heading_detection_ignores_trailing_spaces():
    md = "# T\n\n##  Article  \n\n**Anna:** Hi.\n"
    script, replaced = tts.spoken_script(md)
    assert replaced == 1
    assert script.endswith("Hi.\n")


# --------------------------------------------------------------------------
# 工具查找
# --------------------------------------------------------------------------


def test_resolve_prefers_explicit_path(tmp_path: Path):
    tool = tmp_path / "my-eaudio.cmd"
    tool.write_text("@echo off\n", encoding="utf-8")
    assert tts.resolve_audio_tool(str(tool)) == tool.resolve()


def test_resolve_returns_none_when_nothing_found(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    monkeypatch.delenv(tts.AUDIO_TOOL_ENV, raising=False)
    monkeypatch.setattr(tts.shutil, "which", lambda name: None)
    monkeypatch.setattr(tts, "AUDIO_TOOL_CANDIDATES", (tmp_path / "nope.cmd",))
    assert tts.resolve_audio_tool(None) is None


# --------------------------------------------------------------------------
# 合成：真正送给 TTS 的文本
# --------------------------------------------------------------------------


def test_synthesize_feeds_stripped_text(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    md = tmp_path / "0082.A_Conversation_at_the_Airport.md"
    md.write_text(DIALOGUE_MD, encoding="utf-8", newline="\n")
    tool = _fake_tool(tmp_path, monkeypatch)
    dist = tmp_path / "sources"

    ok, detail = tts.synthesize(md, dist, tool)

    assert ok, detail
    assert "去掉 2 处说话人标签" in detail
    assert (dist / "0082.A_Conversation_at_the_Airport.wav").is_file()
    seen = (dist / "seen.txt").read_text(encoding="utf-8")
    assert "**Anna:**" not in seen
    assert "Excuse me. Is this the line?" in seen
    assert "**Question 1:**" in seen  # 只动正文，题目保持原样


def test_synthesize_passes_plain_article_through(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    md = tmp_path / "0086.A_Plain_Story.md"
    md.write_text(PLAIN_MD, encoding="utf-8", newline="\n")
    tool = _fake_tool(tmp_path, monkeypatch)
    dist = tmp_path / "sources"

    ok, detail = tts.synthesize(md, dist, tool)

    assert ok, detail
    assert "说话人标签" not in detail
    assert (dist / "seen.txt").read_text(encoding="utf-8") == PLAIN_MD


def test_synthesize_reports_missing_wav(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    """工具报成功却没产出 WAV 时要明确失败 —— 否则构建只会显示「缺音频」，查不到根因。"""
    md = tmp_path / "0087.Empty.md"
    md.write_text(PLAIN_MD, encoding="utf-8", newline="\n")
    tool = tmp_path / "silent.py"
    tool.write_text("import sys\nsys.exit(0)\n", encoding="utf-8", newline="\n")
    monkeypatch.setattr(
        tts,
        "_command",
        lambda binary, source, dist: [sys.executable, str(binary)],
    )

    ok, detail = tts.synthesize(md, tmp_path / "sources", tool)

    assert ok is False
    assert "没有生成 WAV" in detail


def test_command_wraps_batch_files(tmp_path: Path):
    """``.cmd`` 必须经 cmd.exe 转一手，否则 subprocess 直接报 WinError 193。"""
    cmd = tts._command(Path("eaudio.cmd"), Path("a.md"), Path("sources"))
    assert cmd[0] == "cmd" and cmd[1] == "/c"

    exe = tts._command(Path("EnglishAudio.exe"), Path("a.md"), Path("sources"))
    assert exe[0] == "EnglishAudio.exe"
    assert exe[-1] == "--dist=sources"
