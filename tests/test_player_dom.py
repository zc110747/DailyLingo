# -*- coding: utf-8 -*-
"""朗读高亮：真实 DOM 交互测试（jsdom，可选依赖）。

``tests/js/player_dom.js`` 用替身 Audio 在真实 DOM 里跑 ``assets/js/audio-player.js``：
播放前不高亮、时间推进时高亮跟随、点句子跳转、选中文字时不跳转、键盘快退后高亮回退。

页面由**现场构建**生成（三句话 + 现场合成的音频），所以期望的高亮下标是确定的，
不依赖 ``content/`` 里现有文章的具体句数。

jsdom 与 node 都不是站点依赖：本机没装时整组 skip，``pytest -q`` 仍然全绿。
"""

from __future__ import annotations

import array
import json
import math
import os
import shutil
import subprocess
import wave
from pathlib import Path

import pytest

import build
from conftest import find_jsdom, find_node

ROOT = Path(__file__).resolve().parent.parent
DOM_SCRIPT = ROOT / "tests" / "js" / "player_dom.js"
PLAYER_JS = ROOT / "assets" / "js" / "audio-player.js"

NODE = find_node()
JSDOM_PATH = find_jsdom()

pytestmark = [
    pytest.mark.skipif(NODE is None, reason="未找到 node，跳过 DOM 交互测试"),
    pytest.mark.skipif(JSDOM_PATH is None, reason="未安装 jsdom，跳过 DOM 交互测试"),
]

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


def write_wav(path: Path, rate: int = 16000) -> Path:
    """三个音块 + 两段 0.3 s 停顿：时间轴确定为 0 / 1.15 / 3.45 / 4.6 秒。"""
    segments = [("tone", 1.0), ("silence", 0.3), ("tone", 2.0), ("silence", 0.3), ("tone", 1.0)]
    frames = array.array("h")
    for kind, seconds in segments:
        count = int(rate * seconds)
        if kind == "tone":
            frames.extend(
                int(12000 * math.sin(2 * math.pi * 220 * i / rate)) for i in range(count)
            )
        else:
            frames.extend([0] * count)
    with wave.open(str(path), "wb") as handle:
        handle.setnchannels(1)
        handle.setsampwidth(2)
        handle.setframerate(rate)
        handle.writeframes(frames.tobytes())
    return path


@pytest.fixture(scope="module")
def observations(tmp_path_factory) -> dict:
    work = tmp_path_factory.mktemp("player")
    content = work / "content"
    content.mkdir()
    (content / "0001.Three_Sentences.md").write_text(ARTICLE_MD, encoding="utf-8", newline="\n")
    sources = work / "sources"
    sources.mkdir()
    write_wav(sources / "0001.Three_Sentences.wav")
    out = work / "out"
    build.build_site(content, out, sources)

    env = dict(os.environ)
    env["NODE_PATH"] = JSDOM_PATH or ""
    proc = subprocess.run(
        [
            NODE,
            str(DOM_SCRIPT),
            str(out / "src" / "0001.Three_Sentences.html"),
            str(PLAYER_JS),
        ],
        capture_output=True,
        text=True,
        encoding="utf-8",
        env=env,
        cwd=str(ROOT),
    )
    assert proc.returncode == 0, proc.stderr
    return json.loads(proc.stdout)


def test_dom_script_ran_without_errors(observations):
    assert observations["errors"] == []
    assert observations["sentenceCount"] == 3


def test_no_highlight_before_playback(observations):
    """页面刚打开时一句都不该加粗（否则看起来像正在播放）。"""
    assert observations["beforePlay"] == -1
    assert observations["beforePlayStillNone"] is True


def test_highlight_follows_playback(observations):
    assert observations["at05"] == 0
    assert observations["at20"] == 1
    assert observations["at40"] == 2


def test_click_sentence_seeks_and_plays(observations):
    clicked = observations["afterClick"]
    assert clicked["active"] == 2
    assert clicked["time"] == pytest.approx(observations["clickStart"], abs=0.01)
    assert observations["clickedAndPlaying"] is True


def test_click_ignored_when_text_selected(observations):
    guard = observations["selectionGuard"]
    assert guard["unchanged"] is True


def test_highlight_moves_back_after_rewind(observations):
    seek = observations["seekBack"]
    assert seek["after"] < seek["before"]
    assert seek["active"] == 0


def test_only_one_sentence_is_active(observations):
    assert observations["activeCount"] == 1
