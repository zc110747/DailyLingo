# -*- coding: utf-8 -*-
"""前端判分逻辑的自动化测试（在 Node 中执行 assets/js/main.js 暴露的纯函数）。

浏览器交互（真实点击、音频播放）不在本文件的覆盖范围内，见 README-CH.md「尚未完成与需人工
验证的事项」（README.md 的 "Known Limitations and Manual Verification"）。本文件覆盖的是
可以被真实验证的判分规则：单选 / 填空、
多个可接受答案、大小写不敏感、首尾空格、空白答案不判正确，以及与
``build.normalize_answer`` 的一致性。
"""

from __future__ import annotations

import glob
import json
import os
import shutil
import subprocess
import sys
from pathlib import Path

import pytest

import build

ROOT = Path(__file__).resolve().parent.parent
MAIN_JS = ROOT / "assets" / "js" / "main.js"

HARNESS = r"""
const fs = require('fs');
const vm = require('vm');
const src = fs.readFileSync(process.argv[2], 'utf8');
const payload = JSON.parse(fs.readFileSync(process.argv[3], 'utf8'));

const ctx = {};
vm.createContext(ctx);
vm.runInContext(src, ctx, { filename: 'main.js' });

const dl = ctx.DailyLingo;
if (!dl) {
  process.stderr.write('main.js did not expose globalThis.DailyLingo');
  process.exit(2);
}

const result = {
  judge: payload.judge.map(function (c) {
    return { name: c.name, result: dl.judge(c.entry, c.value) };
  }),
  normalize: payload.normalize.map(function (s) {
    return dl.normalizeAnswer(s);
  })
};
process.stdout.write(JSON.stringify(result));
"""


def _find_node() -> str | None:
    found = shutil.which("node")
    if found:
        return found
    patterns = [
        os.path.expanduser("~/.workbuddy/binaries/node/versions/*/node.exe"),
        os.path.expanduser("~/.workbuddy/binaries/node/versions/*/bin/node"),
        r"C:\Program Files\nodejs\node.exe",
    ]
    for pattern in patterns:
        matches = sorted(glob.glob(pattern))
        if matches:
            return matches[-1]
    return None


NODE = _find_node()
pytestmark = pytest.mark.skipif(NODE is None, reason="未找到 node，跳过前端判分逻辑测试")


@pytest.fixture(scope="module")
def run_js(tmp_path_factory):
    def _run(judge_cases: list[dict], normalize_cases: list[str]) -> dict:
        work = tmp_path_factory.mktemp("js")
        harness = work / "harness.js"
        payload = work / "payload.json"
        harness.write_text(HARNESS, encoding="utf-8", newline="\n")
        payload.write_text(
            json.dumps({"judge": judge_cases, "normalize": normalize_cases}, ensure_ascii=False),
            encoding="utf-8",
        )
        proc = subprocess.run(
            [NODE, str(harness), str(MAIN_JS), str(payload)],
            capture_output=True,
            text=True,
            encoding="utf-8",
        )
        assert proc.returncode == 0, proc.stderr
        return json.loads(proc.stdout)

    return _run


CHOICE = {"type": "choice", "answer": "B", "acceptable": ["B"], "explanation": ""}
FILL = {"type": "fill", "answer": "cook", "acceptable": ["cook", "to cook"], "explanation": ""}

JUDGE_CASES = [
    ("choice correct", CHOICE, "B", "correct"),
    ("choice lowercase", CHOICE, "b", "correct"),
    ("choice with spaces", CHOICE, "  b  ", "correct"),
    ("choice wrong", CHOICE, "C", "wrong"),
    ("choice empty", CHOICE, "", "empty"),
    ("choice blank spaces", CHOICE, "   ", "empty"),
    ("fill exact", FILL, "cook", "correct"),
    ("fill uppercase", FILL, "COOK", "correct"),
    ("fill spaces", FILL, "  Cook  ", "correct"),
    ("fill trailing period", FILL, "cook.", "correct"),
    ("fill alternate accepted answer", FILL, " to cook ", "correct"),
    ("fill wrong", FILL, "bake", "wrong"),
    ("fill empty", FILL, "", "empty"),
    ("fill blank spaces", FILL, "    ", "empty"),
    ("fill single-answer entry", {"type": "fill", "answer": "happy", "acceptable": ["happy"]}, "happy", "correct"),
    ("fill multi-word answer", {"type": "fill", "answer": "He helped someone.", "acceptable": ["He helped someone."]},
     " he helped someone ", "correct"),
]


def test_judge_rules(run_js):
    cases = [{"name": n, "entry": e, "value": v} for n, e, v, _ in JUDGE_CASES]
    out = run_js(cases, [])["judge"]
    actual = {item["name"]: item["result"]["status"] for item in out}
    for name, _entry, _value, expected in JUDGE_CASES:
        assert actual[name] == expected, f"{name}: 期望 {expected}，实际 {actual[name]}"


def test_judge_echoes_correct_answer(run_js):
    out = run_js([{"name": "wrong", "entry": CHOICE, "value": "C"}], [])["judge"]
    assert out[0]["result"]["answer"] == "B"


def test_normalize_matches_python(run_js):
    samples = [
        "cook",
        "  Cook  ",
        "cook.",
        "COOK!",
        "cook   it",
        "hello world?",
        "   ",
        "",
        "happy...",
        "a, b",
        "中文答案",
        "café",
    ]
    js_values = run_js([], samples)["normalize"]
    for raw, js_value in zip(samples, js_values):
        assert js_value == build.normalize_answer(raw), f"{raw!r}: JS={js_value!r} PY={build.normalize_answer(raw)!r}"


def test_js_blank_guard_exists_in_source():
    """静态检查：main.js 中必须有空白输入的显式拦截（不依赖颜色 / 仅靠比较）。"""
    source = MAIN_JS.read_text(encoding="utf-8")
    assert "空白答案永远不判为正确" in source
    assert "judge" in source and "normalizeAnswer" in source


# ---------------------------------------------------------------- 本地设置
# 「页面语音跟随」的存储层在 main.js（文章页与首页共用），这里用假 window 直接跑。

READING_FOLLOW_KEY = "dailylingo_reading_follow_v1"
AUDIO_LOOP_KEY = "dailylingo_audio_loop_v1"

FOLLOW_HARNESS = r"""
const fs = require('fs');
const vm = require('vm');
const src = fs.readFileSync(process.argv[2], 'utf8');
const mode = process.argv[3]; // memory | broken | no-window

function memoryStorage() {
  const data = new Map();
  return {
    getItem: function (k) { return data.has(k) ? data.get(k) : null; },
    setItem: function (k, v) { data.set(k, String(v)); }
  };
}

const ctx = {};
if (mode !== 'no-window') {
  ctx.window = {
    localStorage: mode === 'broken'
      ? { getItem: function () { throw new Error('denied'); },
          setItem: function () { throw new Error('denied'); } }
      : memoryStorage()
  };
}
vm.createContext(ctx);
vm.runInContext(src, ctx, { filename: 'main.js' });

const api = ctx.DailyLingo && ctx.DailyLingo.readingFollow;
if (!api) {
  process.stderr.write('main.js did not expose DailyLingo.readingFollow');
  process.exit(2);
}
const loop = ctx.DailyLingo.audioLoop;
if (!loop) {
  process.stderr.write('main.js did not expose DailyLingo.audioLoop');
  process.exit(2);
}

const out = { key: api.key, initial: api.enabled() };
out.setTrue = api.set(true);
out.afterTrue = api.enabled();
out.raw = mode === 'memory' ? ctx.window.localStorage.getItem(api.key) : null;
out.setFalse = api.set(false);
out.afterFalse = api.enabled();
out.rawFalse = mode === 'memory' ? ctx.window.localStorage.getItem(api.key) : null;

out.loopKey = loop.key;
out.loopInitial = loop.enabled();
out.loopSetFalse = loop.set(false);
out.loopAfterFalse = loop.enabled();
out.loopRawFalse = mode === 'memory' ? ctx.window.localStorage.getItem(loop.key) : null;
out.loopSetTrue = loop.set(true);
out.loopAfterTrue = loop.enabled();
process.stdout.write(JSON.stringify(out));
"""


def _run_follow(mode: str) -> dict:
    import tempfile

    with tempfile.TemporaryDirectory() as tmp:
        harness = Path(tmp) / "follow.js"
        harness.write_text(FOLLOW_HARNESS, encoding="utf-8", newline="\n")
        proc = subprocess.run(
            [NODE, str(harness), str(MAIN_JS), mode],
            capture_output=True,
            text=True,
            encoding="utf-8",
        )
    assert proc.returncode == 0, proc.stderr
    return json.loads(proc.stdout)


def test_reading_follow_defaults_to_off():
    """没设置过 ⇒ 关闭；这正是「边听边做题页面别乱跳」的默认行为。"""
    out = _run_follow("memory")
    assert out["key"] == READING_FOLLOW_KEY
    assert out["initial"] is False


def test_reading_follow_round_trips():
    out = _run_follow("memory")
    assert out["setTrue"] is True
    assert out["afterTrue"] is True
    assert out["raw"] == "1"
    assert out["setFalse"] is True
    assert out["afterFalse"] is False
    assert out["rawFalse"] == "0"


def test_reading_follow_degrades_to_off():
    """存储不可用（隐私模式 / 无 window）时既不报错、也不假装已开启。"""
    for mode in ("broken", "no-window"):
        out = _run_follow(mode)
        assert out["initial"] is False, mode
        assert out["setTrue"] is False, mode
        assert out["afterTrue"] is False, mode


# 「播完循环播放」：同一个存储层，默认值反过来（默认开）
def test_audio_loop_defaults_to_on():
    """没设置过 ⇒ 循环；这正是「播完自动重播、不用手动再点」的默认行为。"""
    out = _run_follow("memory")
    assert out["loopKey"] == AUDIO_LOOP_KEY
    assert out["loopInitial"] is True


def test_audio_loop_round_trips():
    out = _run_follow("memory")
    assert out["loopSetFalse"] is True
    assert out["loopAfterFalse"] is False
    assert out["loopRawFalse"] == "0"
    assert out["loopSetTrue"] is True
    assert out["loopAfterTrue"] is True


def test_audio_loop_degrades_to_on():
    """存储不可用时不报错，并按默认值（循环）处理，而不是静默变成「不循环」。"""
    for mode in ("broken", "no-window"):
        out = _run_follow(mode)
        assert out["loopInitial"] is True, mode
        assert out["loopSetFalse"] is False, mode
        assert out["loopAfterFalse"] is True, mode
