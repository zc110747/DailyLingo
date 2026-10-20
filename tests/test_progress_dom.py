# -*- coding: utf-8 -*-
"""学习进度功能：真实 DOM 交互测试（jsdom，可选依赖）。

``tests/js/progress_dom.js`` 会在真实的 DOM 里执行 ``assets/js/progress.js``，
用真实 click 事件走完需求里能自动化的部分：勾选 / 取消、Chapter 汇总、统计、
刷新恢复、数据损坏、存储禁用、合并导入、覆盖导入（含二次确认）、非法文件、
未知编号、导出载荷、对话框开关。

文章数**从生成结果里读**（``meta.total``），不写死具体篇数 —— 新增文章不用改测试。

jsdom **不是**站点依赖，也不是测试套件的硬依赖：本机没装时这组用例整体 skip，
``pytest -q`` 仍然全绿（其余用例覆盖结构生成与纯逻辑）。
"""

from __future__ import annotations

import json
import os
import re
import subprocess
from datetime import datetime
from pathlib import Path

import pytest

import build
from conftest import find_jsdom, find_node

ROOT = Path(__file__).resolve().parent.parent
DOM_SCRIPT = ROOT / "tests" / "js" / "progress_dom.js"
PROGRESS_JS = ROOT / "assets" / "js" / "progress.js"
MAIN_JS = ROOT / "assets" / "js" / "main.js"

NODE = find_node()
JSDOM_PATH = find_jsdom()

pytestmark = [
    pytest.mark.skipif(NODE is None, reason="未找到 node，跳过 DOM 交互测试"),
    pytest.mark.skipif(JSDOM_PATH is None, reason="未安装 jsdom，跳过 DOM 交互测试"),
]


def expected_percent(done: int, total: int) -> str:
    """与 progress.js 的 Math.round(done / total * 100) 对齐（JS 是四舍五入）。"""
    if not total:
        return "0%"
    return f"{int(done / total * 100 + 0.5)}%"


def assert_fill(actual: str, done: int, total: int) -> None:
    """进度条宽度是 ratio*100 的 1 位小数渲染。

    JS 用 ``toFixed(1)``，Python 的 ``:.1f`` 在 6.25 这种半数上取值不同（6.3 vs 6.2），
    所以按容差比对，而不是逐字比较（否则文章数一变就假红）。
    """
    if not total:
        assert actual == "0%"
        return
    assert actual.endswith("%"), actual
    value = float(actual[:-1])
    assert abs(value - done * 100 / total) <= 0.06, f"{actual} vs {done}/{total}"


@pytest.fixture(scope="module")
def observations(tmp_path_factory) -> dict:
    out = tmp_path_factory.mktemp("dom")
    build.build_site(ROOT / "content", out, ROOT / "sources")
    env = dict(os.environ)
    env["NODE_PATH"] = JSDOM_PATH or ""
    proc = subprocess.run(
        [
            NODE,
            str(DOM_SCRIPT),
            str(out / "index.html"),
            str(PROGRESS_JS),
            str(MAIN_JS),
        ],
        capture_output=True,
        text=True,
        encoding="utf-8",
        env=env,
        cwd=str(ROOT),
    )
    assert proc.returncode == 0, proc.stderr
    return json.loads(proc.stdout)


@pytest.fixture(scope="module")
def total(observations) -> int:
    return observations["meta"]["total"]


def test_dom_script_reports_all_scenarios(observations):
    expected = {
        "meta",
        "fresh",
        "toggle_one",
        "toggle_off",
        "all_done",
        "uncheck_one",
        "reload",
        "corrupt",
        "unavailable",
        "import_preview_merge",
        "import_merge",
        "import_overwrite_confirm",
        "import_overwrite",
        "import_overwrite_cancel",
        "import_bad_json",
        "import_bad_version",
        "import_unknown",
        "import_unknown_after",
        "import_all_unknown",
        "export",
        "dialog_closed",
        "dialog_open",
        "dialog_after_close",
        "follow_default",
        "follow_on",
        "follow_reopen",
        "follow_off",
        "chapters_initial",
        "chapters_after_first",
        "chapters_two",
        "chapters_after_second",
    }
    assert expected <= set(observations)


def test_meta_matches_generated_pages(observations, total, tmp_path):
    """DOM 里的文章数 / Chapter 篇数 / ID 列表必须等于生成结果（测试不能与构建脱节）。"""
    result = build.build_site(ROOT / "content", tmp_path, ROOT / "sources")
    assert total == len(result.articles)
    assert observations["meta"]["chapterTotal"] == len(result.chapters[0].articles)
    assert observations["meta"]["ids"] == [a.number_text for a in result.articles]


# 需求 1：第一次访问没有任何文章被标记
def test_first_visit_is_empty(observations, total):
    fresh = observations["fresh"]
    assert fresh["stats"]["done"] == "0"
    assert fresh["stats"]["total"] == str(total)
    assert fresh["stats"]["percent"] == "0%"
    assert set(fresh["pressed"]) == {"false"}
    assert len(fresh["pressed"]) == total
    assert fresh["chapter"]["count"] == f"0/{total}"
    assert fresh["chapter"]["complete"] is False
    assert fresh["storage"] is None
    assert fresh["notice"] == ""


# 需求 2/3：勾选立即更新统计与存储，取消正确回退
def test_toggle_updates_stats_and_storage(observations, total):
    step = observations["toggle_one"]
    stats = step["stats"]
    assert (stats["done"], stats["total"], stats["valuenow"]) == ("1", str(total), "1")
    assert stats["percent"] == expected_percent(1, total)
    assert_fill(stats["fill"], 1, total)
    assert step["chapter"] == {"count": f"1/{total}", "state": "未完成", "complete": False}
    assert step["pressed0001"] == "true"
    assert "未完成" in step["label0001"]  # 标签切换成「取消」语义
    assert step["itemDone"] is True
    assert step["storage"]["schemaVersion"] == 1
    assert step["storage"]["completedArticles"] == ["0001"]
    assert step["storage"]["updatedAt"].endswith("Z")
    # 需求 1 的关键约束：点图标不跳转、也不折叠 Chapter
    assert step["locationSame"] is True
    assert step["detailsUnchanged"] is True

    off = observations["toggle_off"]
    assert (off["stats"]["done"], off["stats"]["percent"]) == ("0", "0%")
    assert off["chapter"]["count"] == f"0/{total}"
    assert off["pressed0001"] == "false"
    assert off["storage"]["completedArticles"] == []


# 需求 4/5：Chapter 全完成才显示勾，取消任意一篇立即失效
def test_chapter_auto_aggregates(observations, total):
    done = observations["all_done"]
    assert (done["stats"]["done"], done["stats"]["percent"]) == (str(total), "100%")
    assert done["stats"]["fill"] == "100%"
    assert done["chapter"] == {
        "count": f"{total}/{total}",
        "state": "已完成",
        "complete": True,
    }

    after = observations["uncheck_one"]
    assert after["stats"]["done"] == str(total - 1)
    assert after["stats"]["percent"] == expected_percent(total - 1, total)
    assert after["chapter"] == {
        "count": f"{total - 1}/{total}",
        "state": "未完成",
        "complete": False,
    }


# 需求 6/7：刷新、关闭浏览器后重开，状态仍在
def test_state_survives_reload(observations, total):
    step = observations["reload"]
    assert step["stats"]["done"] == str(total - 1)
    assert step["stats"]["percent"] == expected_percent(total - 1, total)
    assert step["chapter"]["count"] == f"{total - 1}/{total}"
    assert step["pressed0003"] == "false"


# 需求 9：数据损坏要提示 + 安全恢复
def test_corrupt_storage_is_quarantined(observations, total):
    step = observations["corrupt"]
    assert "损坏" in step["notice"]
    assert step["backup"] == "{oops"  # 原始数据留存
    assert step["stats"]["done"] == "0"
    assert step["stats"]["total"] == str(total)  # 页面统计仍可用
    assert step["rewritten"] == {"schemaVersion": 1, "completedArticles": [], "updatedAt": ""}


# 需求 10：本地存储不可用时明确提示，页面主体仍能用
def test_storage_unavailable_degrades_gracefully(observations):
    step = observations["unavailable"]
    assert "本地存储" in step["noticeBefore"]
    assert "保存失败" in step["noticeAfter"]
    assert step["stats"]["done"] == "1"  # 内存态仍然生效


# 需求 8 + 合并模式
def test_import_preview_and_merge(observations):
    preview = observations["import_preview_merge"]
    assert preview["previewVisible"] is True
    assert preview["fileCount"] == "3"
    assert preview["currentCount"] == "2"
    assert preview["mergedCount"] == "4"  # 2 篇 ∪ 3 篇，重叠 1 篇
    assert preview["overwriteCount"] == "3"

    merged = observations["import_merge"]
    assert merged["stats"]["done"] == "4"
    assert merged["storage"]["completedArticles"] == ["0001", "0002", "0003", "0004"]
    assert "合并" in merged["message"]


# 覆盖模式：必须先确认，确认后才替换
def test_import_overwrite_requires_confirmation(observations):
    confirm = observations["import_overwrite_confirm"]
    assert confirm["confirmVisible"] is True
    # 确认之前进度不能动
    assert confirm["statsBeforeConfirm"]["done"] == "3"
    assert confirm["storageBeforeConfirm"]["completedArticles"] == ["0001", "0002", "0003"]

    done = observations["import_overwrite"]
    assert done["stats"]["done"] == "1"
    assert done["storage"]["completedArticles"] == ["0005"]  # 覆盖取消原有记录

    cancel = observations["import_overwrite_cancel"]
    assert cancel["confirmVisible"] is False
    assert cancel["stats"]["done"] == "1"  # 取消确认后进度不变


# 需求 11：非法 JSON / 不支持的版本不得破坏现有进度
def test_invalid_import_keeps_progress(observations):
    bad_json = observations["import_bad_json"]
    assert "导入失败" in bad_json["message"]
    assert bad_json["stats"]["done"] == "1"
    assert bad_json["previewVisible"] is False

    bad_version = observations["import_bad_version"]
    assert "版本" in bad_version["message"]
    assert bad_version["stats"]["done"] == "1"


# 需求 12：不存在的编号安全忽略并报告数量
def test_unknown_ids_are_ignored(observations):
    step = observations["import_unknown"]
    assert step["fileCount"] == "1"  # 0001 有效，9999 / 8888 不存在
    assert "忽略 2 条" in step["message"]

    after = observations["import_unknown_after"]
    assert after["stats"]["done"] == "1"
    assert after["storage"]["completedArticles"] == ["0001"]

    rejected = observations["import_all_unknown"]
    assert "都不存在" in rejected["message"]
    assert rejected["previewVisible"] is False
    assert rejected["stats"]["done"] == "1"


# 导出：文件名、JSON 结构、只含有效编号
def test_export_produces_importable_json(observations):
    step = observations["export"]
    name = step["downloaded"]["download"]
    assert re.fullmatch(r"dailylingo-progress-\d{8}\.json", name), name
    datetime.strptime(name[len("dailylingo-progress-") : -len(".json")], "%Y%m%d")
    assert step["downloaded"]["href"] == "blob:test"
    payload = step["payload"]
    assert payload["schemaVersion"] == 1
    assert payload["completedArticles"] == ["0001", "0002"]
    assert set(payload) == {"schemaVersion", "completedArticles", "updatedAt", "exportedAt"}
    assert "导出" in step["message"]
    assert payload["exportedAt"] and payload["updatedAt"]


# 设置对话框：左上角入口 → 打开 → 关闭
def test_settings_dialog_toggles(observations):
    assert observations["dialog_closed"] == {"expanded": "false", "open": False}
    assert observations["dialog_open"] == {"expanded": "true", "open": True}
    closed = observations["dialog_after_close"]
    assert closed["expanded"] == "false"
    assert closed["previewVisible"] is False


# 设置里的「页面语音跟随」：默认关闭，切换写进独立的存储键
def test_reading_follow_off_by_default(observations):
    step = observations["follow_default"]
    assert step["exists"] is True
    assert step["checked"] is False
    assert step["stored"] is None


def test_reading_follow_toggle_persists(observations):
    on = observations["follow_on"]
    assert on["checked"] is True
    assert on["stored"] == "1"
    assert "已开启" in on["message"]
    assert observations["follow_reopen"]["checked"] is True

    off = observations["follow_off"]
    assert off["checked"] is False
    assert off["stored"] == "0"
    assert "已关闭" in off["message"]


# --------------------------------------------------------------------------
# 每章独立的计数与进度条（一章 25 篇，跨章时互不影响）
# --------------------------------------------------------------------------

MARKER_MD = """# {title}

## Article

{title} is a very short story. It only has two sentences.

## Words

| Word | IPA | Meaning |
| --- | --- | --- |
| **story** | /ˈstɔːri/ | 故事 |

## Questions

Question 1：Is this a story?

A. Yes.

B. No.

## Answers

1\\. **A. Yes.** It is a story.
"""


@pytest.fixture(scope="module")
def two_chapters(tmp_path_factory) -> dict:
    """0001–0003 属第一章、0026–0027 属第二章（CHUNK = 25）。"""
    root = tmp_path_factory.mktemp("two-chapters")
    content = root / "content"
    content.mkdir()
    for number in (1, 2, 3, 26, 27):
        (content / f"{number:04d}.Story_N{number}.md").write_text(
            MARKER_MD.format(title=f"Story N{number}"), encoding="utf-8", newline="\n"
        )
    out = root / "out"
    build.build_site(content, out, root / "sources")
    env = dict(os.environ)
    env["NODE_PATH"] = JSDOM_PATH or ""
    proc = subprocess.run(
        [
            NODE,
            str(DOM_SCRIPT),
            str(out / "index.html"),
            str(PROGRESS_JS),
            str(MAIN_JS),
        ],
        capture_output=True,
        text=True,
        encoding="utf-8",
        env=env,
        cwd=str(ROOT),
    )
    assert proc.returncode == 0, proc.stderr
    return json.loads(proc.stdout)


def _percent(entry: dict) -> float:
    """jsdom 会把 `0.0%` 归一成 `0%`，所以按数值比，而不是逐字比。"""
    width = entry["width"] or "0%"
    assert width.endswith("%"), width
    return float(width[:-1])


def test_two_chapters_are_grouped_by_twenty_five(two_chapters):
    assert two_chapters["chapters_two"] is True
    initial = two_chapters["chapters_initial"]
    assert len(initial) == 2
    assert [c["max"] for c in initial] == ["3", "2"]
    assert [c["count"] for c in initial] == ["0/3", "0/2"]
    assert [_percent(c) for c in initial] == [0.0, 0.0]


def test_chapter_meters_move_independently(two_chapters):
    """勾第一章的一篇：只有第一章的条和计数变，第二章必须原地不动。"""
    after_first = two_chapters["chapters_after_first"]
    assert after_first[0]["count"] == "1/3"
    assert after_first[0]["now"] == "1"
    assert after_first[0]["max"] == "3"
    assert _percent(after_first[0]) == pytest.approx(100 / 3, abs=0.05)

    assert after_first[1]["count"] == "0/2"
    assert after_first[1]["now"] == "0"
    assert after_first[1]["max"] == "2"
    assert _percent(after_first[1]) == 0.0

    after_second = two_chapters["chapters_after_second"]
    assert after_second[0]["count"] == "1/3"
    assert after_second[1]["count"] == "1/2"
    assert _percent(after_second[1]) == pytest.approx(50.0, abs=0.05)
