# -*- coding: utf-8 -*-
"""学习进度功能：真实 DOM 交互测试（jsdom，可选依赖）。

``tests/js/progress_dom.js`` 会在真实的 DOM 里执行 ``assets/js/progress.js``，
用真实 click 事件走完 17 项需求里能自动化的部分：勾选 / 取消、Chapter 汇总、统计、
刷新恢复、数据损坏、存储禁用、合并导入、覆盖导入（含二次确认）、非法文件、
未知编号、导出载荷、对话框开关。

jsdom **不是**站点依赖，也不是测试套件的硬依赖：本机没装时这组用例整体 skip，
``pytest -q`` 仍然全绿（其余用例覆盖结构生成与纯逻辑）。
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
DOM_SCRIPT = ROOT / "tests" / "js" / "progress_dom.js"
PROGRESS_JS = ROOT / "assets" / "js" / "progress.js"

NODE = find_node()
JSDOM_PATH = find_jsdom()

pytestmark = [
    pytest.mark.skipif(NODE is None, reason="未找到 node，跳过 DOM 交互测试"),
    pytest.mark.skipif(JSDOM_PATH is None, reason="未安装 jsdom，跳过 DOM 交互测试"),
]


@pytest.fixture(scope="module")
def observations(tmp_path_factory) -> dict:
    out = tmp_path_factory.mktemp("dom")
    build.build_site(ROOT / "content", out, ROOT / "sources")
    env = dict(os.environ)
    env["NODE_PATH"] = JSDOM_PATH or ""
    proc = subprocess.run(
        [NODE, str(DOM_SCRIPT), str(out / "index.html"), str(PROGRESS_JS)],
        capture_output=True,
        text=True,
        encoding="utf-8",
        env=env,
        cwd=str(ROOT),
    )
    assert proc.returncode == 0, proc.stderr
    return json.loads(proc.stdout)


def test_dom_script_reports_all_scenarios(observations):
    expected = {
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
    }
    assert expected <= set(observations)


# 需求 1：第一次访问没有任何文章被标记
def test_first_visit_is_empty(observations):
    fresh = observations["fresh"]
    assert fresh["stats"]["done"] == "0"
    assert fresh["stats"]["total"] == "10"
    assert fresh["stats"]["percent"] == "0%"
    assert set(fresh["pressed"]) == {"false"}
    assert fresh["chapter"]["count"] == "0/10"
    assert fresh["chapter"]["complete"] is False
    assert fresh["storage"] is None
    assert fresh["notice"] == ""


# 需求 2/3：勾选立即更新统计，取消正确回退
def test_toggle_updates_stats_and_storage(observations):
    step = observations["toggle_one"]
    assert step["stats"] == {
        "done": "1",
        "total": "10",
        "percent": "10%",
        "fill": "10%",
        "valuenow": "1",
    }
    assert step["chapter"] == {"count": "1/10", "state": "未完成", "complete": False}
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
    assert off["chapter"]["count"] == "0/10"
    assert off["pressed0001"] == "false"
    assert off["storage"]["completedArticles"] == []


# 需求 4/5：Chapter 全完成才显示勾，取消任意一篇立即失效
def test_chapter_auto_aggregates(observations):
    done = observations["all_done"]
    assert (done["stats"]["done"], done["stats"]["percent"]) == ("10", "100%")
    assert done["stats"]["fill"] == "100%"
    assert done["chapter"] == {"count": "10/10", "state": "已完成", "complete": True}

    after = observations["uncheck_one"]
    assert after["stats"]["done"] == "9"
    assert after["chapter"] == {"count": "9/10", "state": "未完成", "complete": False}


# 需求 6/7：刷新、关闭浏览器后重开，状态仍在
def test_state_survives_reload(observations):
    step = observations["reload"]
    assert step["stats"]["done"] == "9"
    assert step["stats"]["percent"] == "90%"
    assert step["chapter"]["count"] == "9/10"
    assert step["pressed0003"] == "false"


# 需求 9：数据损坏要提示 + 安全恢复
def test_corrupt_storage_is_quarantined(observations):
    step = observations["corrupt"]
    assert "损坏" in step["notice"]
    assert step["backup"] == "{oops"  # 原始数据留存
    assert step["stats"]["done"] == "0"
    assert step["stats"]["total"] == "10"  # 页面统计仍可用
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
    assert step["downloaded"]["download"] == "dailylingo-progress-20261017.json"
    assert step["downloaded"]["href"] == "blob:test"
    payload = step["payload"]
    assert payload["schemaVersion"] == 1
    assert payload["completedArticles"] == ["0001", "0002"]
    assert set(payload) == {"schemaVersion", "completedArticles", "updatedAt", "exportedAt"}
    assert "导出" in step["message"]
    # 导出内容必须能被同一套解析器读回
    assert payload["exportedAt"] and payload["updatedAt"]


# 设置对话框：左上角入口 → 打开 → 关闭
def test_settings_dialog_toggles(observations):
    assert observations["dialog_closed"] == {"expanded": "false", "open": False}
    assert observations["dialog_open"] == {"expanded": "true", "open": True}
    closed = observations["dialog_after_close"]
    assert closed["expanded"] == "false"
    assert closed["previewVisible"] is False
