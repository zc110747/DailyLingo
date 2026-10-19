# -*- coding: utf-8 -*-
"""文章页「自动完成」：判定逻辑 + 页面生成结构。

功能定义（本项目约定）：
    音频听到 ≥90% **且** 全部题目答对 ⇒ 自动把本篇写入学习进度（首页下次打开就有勾）。
    只自动打勾，不自动取消 —— 撤销权留给首页的手动开关。

覆盖：
* ``audio-player.js`` 的收听累计：正常步进累加、跳转丢弃、基准重置
* ``study-completion.js`` 的判定边界：0.89 不算、0.9 算、未全对不算、无题目不算
* 两个脚本用**同一个**事件名通信（``dailylingo:listen`` / ``dailylingo:quiz``）
* 每篇文章页带 ``data-article-id``、学习状态行、自动标记可用性标记
* 文章页引用 progress.js 与 study-completion.js，且都带内容指纹
* 首页原有「手动勾选 / 取消」入口必须保留（新功能不替代手动）

真实 DOM 交互（答题 + 播放上报 + 落库）在 ``test_auto_complete_dom.py``（需要 jsdom）。
"""

from __future__ import annotations

import json
import re
import subprocess
from pathlib import Path

import pytest

import build
from conftest import find_node

ROOT = Path(__file__).resolve().parent.parent
PLAYER_JS = ROOT / "assets" / "js" / "audio-player.js"
COMPLETION_JS = ROOT / "assets" / "js" / "study-completion.js"
LOGIC_SCRIPT = ROOT / "tests" / "js" / "completion_logic.js"

NODE = find_node()

pytestmark = pytest.mark.skipif(NODE is None, reason="未找到 node，跳过自动完成逻辑测试")


@pytest.fixture(scope="module")
def logic() -> dict:
    proc = subprocess.run(
        [NODE, str(LOGIC_SCRIPT), str(PLAYER_JS), str(COMPLETION_JS)],
        capture_output=True,
        text=True,
        encoding="utf-8",
    )
    assert proc.returncode == 0, proc.stderr
    return json.loads(proc.stdout)


@pytest.fixture(scope="module")
def site(tmp_path_factory):
    out = tmp_path_factory.mktemp("auto-complete-site")
    result = build.build_site(ROOT / "content", out, ROOT / "sources")
    pages = {
        a.number_text: (out / "src" / a.html_name).read_text(encoding="utf-8")
        for a in result.articles
    }
    index_html = (out / "index.html").read_text(encoding="utf-8")
    return result, pages, index_html


# --------------------------------------------------------------------------
# 1. 纯逻辑
# --------------------------------------------------------------------------


def test_event_contract_is_shared(logic):
    contract = logic["contract"]
    assert contract["listenEvent"] == "dailylingo:listen"
    assert contract["quizEvent"] == "dailylingo:quiz"
    assert contract["listenEventMatchesPlayer"] is True
    assert contract["requiredRatio"] == 0.9
    assert contract["stepLimit"] == 1.5
    assert contract["rates"] == [0.75, 1, 1.25]


def test_listen_accumulator_ignores_seeks(logic):
    steps = logic["steps"]
    assert steps["firstTick"] == 0  # 第一拍只记基准
    assert abs(steps["normal"] - 0.25) < 1e-9  # 正常推进累加
    assert abs(steps["exactLimit"] - 1.5) < 1e-9  # 恰好等于上限仍算
    assert steps["seekForward"] == 3.0  # 跳到中间：丢掉那一段，不涨
    assert steps["seekBackward"] == 3.0
    assert steps["frozen"] == 3.0


def test_completion_boundaries(logic):
    cases = logic["cases"]
    assert cases["complete"] is True
    assert cases["atThreshold"] is True  # 0.90 恰好够
    assert cases["belowThreshold"] is False  # 0.89 不够
    assert cases["notAllCorrect"] is False  # 答错一题就不算
    assert cases["partialAnswers"] is False
    assert cases["emptyQuiz"] is False  # 没有题目 ⇒ 永不自动完成
    assert cases["noQuiz"] is False


# --------------------------------------------------------------------------
# 2. 文章页结构
# --------------------------------------------------------------------------


def test_article_page_exposes_its_id(site):
    result, pages, _index = site
    for article in result.articles:
        assert f'data-article-id="{article.number_text}"' in pages[article.number_text], (
            article.html_name
        )


def test_study_status_branch_matches_content(site):
    result, pages, _index = site
    for article in result.articles:
        html = pages[article.number_text]
        match = re.search(r'<p class="article-progress" data-study-status data-study-auto="(true|false)"[^>]*>(.*?)</p>', html, re.S)
        assert match, article.html_name
        autoable, text = match.group(1), match.group(2)
        expected = bool(article.has_audio and article.questions)
        assert autoable == ("true" if expected else "false"), article.html_name
        if expected:
            assert "会自动标记" in text
        else:
            assert "无法自动标记" in text and "首页手动勾选" in text


def test_article_page_loads_progress_and_completion(site):
    _result, pages, _index = site
    for number, html in pages.items():
        assert f'src="../{build.asset_url(build.PROGRESS_JS)}"' in html, number
        assert f'src="../{build.asset_url(build.COMPLETION_JS)}"' in html, number


def test_completion_script_has_no_network_calls():
    source = COMPLETION_JS.read_text(encoding="utf-8")
    for forbidden in ("fetch(", "XMLHttpRequest", "navigator.sendBeacon"):
        assert forbidden not in source, forbidden


def test_home_manual_toggle_still_exists(site):
    """新功能是「自动打勾」，但不接管手动开关 —— 首页的勾选 / 取消必须还在。"""
    result, _pages, index_html = site
    assert index_html.count('data-action="toggle-complete"') == len(result.articles)
    assert f'src="{build.asset_url(build.PROGRESS_JS)}"' in index_html
