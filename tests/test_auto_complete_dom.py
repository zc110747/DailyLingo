# -*- coding: utf-8 -*-
"""文章页「自动完成」：真实 DOM 交互测试（jsdom，可选依赖）。

``tests/js/auto_complete_dom.js`` 在**真实生成的文章页**里执行三个真实脚本
（main.js / progress.js / study-completion.js），用真实 click 答题，并直接派发
``dailylingo:listen`` 模拟播放器上报，走完这些场景：

    首次进入 / 只答题没听 / 只听不答题 / 听一半 / 听完且全对 /
    重新打开已完成的页面 / 完成后再改答案 / 已有别的记录 / 存储损坏 / 存储不可用

文章编号与题目数都从生成结果里读，不写死 —— 换一篇文章不用改测试。

jsdom 不是站点依赖，也不在测试硬依赖里：本机没装时整组 skip。
"""

from __future__ import annotations

import json
import os
import subprocess
from pathlib import Path

import pytest

import build
from conftest import find_jsdom, find_node

ROOT = Path(__file__).resolve().parent.parent
DOM_SCRIPT = ROOT / "tests" / "js" / "auto_complete_dom.js"
PROGRESS_JS = ROOT / "assets" / "js" / "progress.js"
MAIN_JS = ROOT / "assets" / "js" / "main.js"
COMPLETION_JS = ROOT / "assets" / "js" / "study-completion.js"

NODE = find_node()
JSDOM_PATH = find_jsdom()

pytestmark = [
    pytest.mark.skipif(NODE is None, reason="未找到 node，跳过 DOM 交互测试"),
    pytest.mark.skipif(JSDOM_PATH is None, reason="未安装 jsdom，跳过 DOM 交互测试"),
]


@pytest.fixture(scope="module")
def observations(tmp_path_factory) -> dict:
    out = tmp_path_factory.mktemp("auto-complete-dom")
    result = build.build_site(ROOT / "content", out, ROOT / "sources")
    # 取第一篇既有音频又有题目的文章（自动标记只在这种页面上成立）
    article = next(a for a in result.articles if a.has_audio and a.questions)
    env = dict(os.environ)
    env["NODE_PATH"] = JSDOM_PATH or ""
    proc = subprocess.run(
        [
            NODE,
            str(DOM_SCRIPT),
            str(out / "src" / article.html_name),
            str(PROGRESS_JS),
            str(MAIN_JS),
            str(COMPLETION_JS),
        ],
        capture_output=True,
        text=True,
        encoding="utf-8",
        env=env,
        cwd=str(ROOT),
    )
    assert proc.returncode == 0, proc.stderr
    data = json.loads(proc.stdout)
    data["_article"] = article.number_text
    data["_questions"] = len(article.questions)
    return data


def test_all_scenarios_reported(observations):
    expected = {
        "meta",
        "fresh",
        "quiz_only",
        "listen_only",
        "partial",
        "complete",
        "listen_then_quiz",
        "reopen_done",
        "change_after_done",
        "union_with_existing",
        "corrupt",
        "storage_unavailable",
    }
    assert expected <= set(observations)


def test_meta_matches_generated_page(observations):
    assert observations["meta"]["articleId"] == observations["_article"]
    assert observations["meta"]["questions"] == observations["_questions"]
    assert observations["meta"]["hasPlayer"] is True
    assert observations["meta"]["autoAttr"] == "true"


def test_first_visit_is_untouched(observations):
    step = observations["fresh"]
    assert step["storage"] is None
    assert step["status"]["done"] is False
    assert "会自动标记" in step["status"]["text"]


def test_quiz_alone_does_not_complete(observations):
    step = observations["quiz_only"]
    assert step["answered"] == observations["_questions"]
    assert step["storage"] is None
    assert step["status"]["done"] is False
    # 提示里能看出答对了几题
    assert f"答对 {observations['_questions']}/{observations['_questions']}" in step["status"]["text"]
    assert "听力 0%" in step["status"]["text"]


def test_playback_alone_does_not_complete(observations):
    step = observations["listen_only"]
    assert step["storage"] is None
    assert step["status"]["done"] is False


def test_partial_playback_does_not_complete(observations):
    step = observations["partial"]
    assert step["storage"] is None
    assert step["status"]["done"] is False
    assert "听力 50%" in step["status"]["text"]


def test_full_playback_plus_all_correct_completes(observations):
    step = observations["complete"]
    storage = step["storage"]
    assert storage is not None
    assert storage["schemaVersion"] == 1
    assert storage["completedArticles"] == [step["id"]]
    assert storage["updatedAt"].endswith("Z")
    assert step["status"]["done"] is True
    assert "已标记为完成" in step["status"]["text"]


def test_marking_works_in_either_order(observations):
    """先听完再答题也要打勾：两个事件任意一个后到都会触发判定。"""
    step = observations["listen_then_quiz"]
    assert step["beforeQuiz"] is None  # 只听完、还没答题时不能打勾
    assert step["status"]["done"] is True
    assert step["storage"]["completedArticles"] == [observations["_article"]]


def test_reopen_already_completed_page(observations):
    step = observations["reopen_done"]
    assert step["status"]["done"] is True
    assert step["storage"]["completedArticles"] == [observations["_article"]]


def test_auto_mark_is_not_revoked_by_later_wrong_answer(observations):
    """完成是「做到过」的事实；改错答案不会把记录抹掉，撤销权留给首页手动开关。"""
    step = observations["change_after_done"]
    assert step["before"]["completedArticles"] == step["after"]["completedArticles"]
    assert step["status"]["done"] is True


def test_auto_mark_unions_with_existing_records(observations):
    step = observations["union_with_existing"]
    ids = step["storage"]["completedArticles"]
    assert step["id"] in ids
    assert "0002" in ids and "0003" in ids  # 原有的勾没有被覆盖
    assert ids == sorted(ids)


def test_corrupt_storage_is_quarantined_then_marked(observations):
    step = observations["corrupt"]
    assert step["backup"] == "{oops"  # 坏数据留档
    assert step["storage"]["completedArticles"] == [observations["_article"]]
    assert step["status"]["done"] is True


def test_storage_unavailable_is_reported(observations):
    step = observations["storage_unavailable"]
    assert step["status"]["error"] is True
    assert "没能保存" in step["status"]["text"]
