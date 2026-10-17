# -*- coding: utf-8 -*-
"""学习进度功能：首页生成结构 + progress.js 纯逻辑（在 Node 中真实执行）。

覆盖：
* 首页必须为每篇实际存在的文章生成一个完成按钮，编号取自构建脚本，初始一律未完成
* 统计总数 / 进度条上限必须等于实际文章数（空文章列表也不能除零）
* 每个 Chapter 的汇总篇数必须等于该章实际文章数
* 设置入口（左上角）+ 对话框里的导出 / 导入控件必须存在，且 progress.js 带内容指纹
* ID 规整、JSON 校验（语法 / 版本 / 结构）、去重、忽略未知编号、合并、统计、Chapter 判定、
  导出载荷结构与文件名

浏览器交互（真实点击 / 存储 / 导入导出流程）在 ``test_progress_dom.py``，依赖可选的 jsdom。
"""

from __future__ import annotations

import json
import subprocess
from pathlib import Path

import pytest

import build
from conftest import find_node

ROOT = Path(__file__).resolve().parent.parent
PROGRESS_JS = ROOT / "assets" / "js" / "progress.js"

NODE = find_node()
pytestmark = pytest.mark.skipif(NODE is None, reason="未找到 node，跳过 progress.js 逻辑测试")

HARNESS = r"""
const fs = require('fs');
const vm = require('vm');
const src = fs.readFileSync(process.argv[2], 'utf8');
const payload = JSON.parse(fs.readFileSync(process.argv[3], 'utf8'));

const ctx = {};
vm.createContext(ctx);
vm.runInContext(src, ctx, { filename: 'progress.js' });

const P = ctx.DailyLingoProgress;
if (!P) {
  process.stderr.write('progress.js did not expose globalThis.DailyLingoProgress');
  process.exit(2);
}

const out = {
  ids: payload.ids.map(function (v) { return P.normalizeId(v); }),
  parse: payload.parse.map(function (t) { return P.parseProgressPayload(t); }),
  stats: payload.stats.map(function (c) { return P.computeStats(c[0], c[1]); }),
  chapter: payload.chapter.map(function (c) { return P.chapterStatus(c[0], c[1]); }),
  merge: payload.merge.map(function (c) { return P.mergeIds(c[0], c[1]); }),
  partition: payload.partition.map(function (c) { return P.partition(c[0], c[1]); }),
  fileName: P.exportFileName(new Date(Date.UTC(2026, 9, 17, 4))),
  exportPayload: P.buildExport(
    payload.exportIds,
    '2026-01-02T03:04:05.000Z',
    new Date('2026-10-17T04:00:00.000Z')
  ),
  constants: { storageKey: P.STORAGE_KEY, schemaVersion: P.SCHEMA_VERSION }
};
process.stdout.write(JSON.stringify(out));
"""


@pytest.fixture(scope="module")
def run_js(tmp_path_factory):
    def _run(**payload) -> dict:
        work = tmp_path_factory.mktemp("progress-js")
        harness = work / "harness.js"
        data = work / "payload.json"
        harness.write_text(HARNESS, encoding="utf-8", newline="\n")
        data.write_text(json.dumps(payload, ensure_ascii=False), encoding="utf-8")
        proc = subprocess.run(
            [NODE, str(harness), str(PROGRESS_JS), str(data)],
            capture_output=True,
            text=True,
            encoding="utf-8",
        )
        assert proc.returncode == 0, proc.stderr
        return json.loads(proc.stdout)

    return _run


def run_js_cases(**payload):
    """给不需要 fixture 的断言用的小包装。"""
    payload.setdefault("ids", [])
    payload.setdefault("parse", [])
    payload.setdefault("stats", [])
    payload.setdefault("chapter", [])
    payload.setdefault("merge", [])
    payload.setdefault("partition", [])
    payload.setdefault("exportIds", [])
    return payload


# --------------------------------------------------------------------------
# 1. 首页生成结构
# --------------------------------------------------------------------------


@pytest.fixture(scope="module")
def site(tmp_path_factory):
    out = tmp_path_factory.mktemp("progress-site")
    result = build.build_site(ROOT / "content", out, ROOT / "sources")
    return result, out, (out / "index.html").read_text(encoding="utf-8")


def test_index_has_one_toggle_per_article(site):
    result, _out, html = site
    assert html.count('data-action="toggle-complete"') == len(result.articles)
    for article in result.articles:
        assert (
            f'data-action="toggle-complete" data-article-id="{article.number_text}"' in html
        ), article.number_text


def test_index_toggles_start_unchecked(site):
    result, _out, html = site
    assert html.count('aria-pressed="false"') == len(result.articles)
    assert 'aria-pressed="true"' not in html


def test_index_stats_total_matches_articles(site):
    result, _out, html = site
    total = len(result.articles)
    assert f"data-progress-total>{total}<" in html
    assert f'aria-valuemax="{total}"' in html
    assert 'aria-valuenow="0"' in html
    assert "data-progress-done>0<" in html
    assert "data-progress-percent>0%<" in html


def test_index_chapter_totals_match_each_chapter(site):
    result, _out, html = site
    import re

    generated = sorted(int(m) for m in re.findall(r'data-chapter-total="(\d+)"', html))
    expected = sorted(len(c.articles) for c in result.chapters)
    assert generated == expected
    assert html.count("data-chapter-status") == len(result.chapters)


def test_index_has_settings_entry_and_dialog(site):
    _result, _out, html = site
    assert 'data-action="open-settings"' in html
    assert 'aria-haspopup="dialog"' in html
    assert 'aria-controls="settings-dialog"' in html
    assert 'aria-expanded="false"' in html
    assert '<dialog class="settings-dialog" id="settings-dialog"' in html
    assert 'data-action="export-progress"' in html
    assert 'data-action="pick-import"' in html
    assert "data-import-input" in html
    assert 'name="import-mode" value="merge"' in html
    assert 'name="import-mode" value="overwrite"' in html
    assert 'data-action="confirm-overwrite"' in html


def test_index_references_progress_js_with_fingerprint(site):
    _result, _out, html = site
    # assets/ 不是构建产物（随仓库提交），由 validate.py 校验存在性
    assert (ROOT / build.PROGRESS_JS).is_file()
    assert f'src="{build.asset_url(build.PROGRESS_JS)}"' in html


def test_index_keeps_existing_structure(site):
    _result, _out, html = site
    # 折叠目录、原生 details/summary、文章链接都还在
    assert 'class="catalogue"' in html
    assert "<details class=\"chapter\" open>" in html
    assert "<summary" in html
    # 首页仍然不出现文章页专属内容
    for forbidden in ("words-table", "question-list", "player", "quiz-data"):
        assert forbidden not in html


def test_index_is_deterministic(site):
    _result, out, html = site
    assert build.render_index(build.group_chapters(build.load_articles(ROOT / "content")[0])) == html


def test_empty_site_has_zero_total(tmp_path):
    """没有文章时首页仍要能生成，统计总数 0（不能除零）。"""
    (tmp_path / "content").mkdir()
    out = tmp_path / "out"
    result = build.build_site(tmp_path / "content", out, tmp_path / "sources")
    assert result.articles == []
    html = (out / "index.html").read_text(encoding="utf-8")
    assert "data-progress-total>0<" in html
    assert 'aria-valuemax="0"' in html
    assert "data-chapter-status" not in html


# --------------------------------------------------------------------------
# 2. progress.js 纯逻辑
# --------------------------------------------------------------------------


def test_storage_contract(run_js):
    out = run_js(**run_js_cases())
    assert out["constants"]["storageKey"] == "dailylingo_learning_progress_v1"
    assert out["constants"]["schemaVersion"] == 1
    source = PROGRESS_JS.read_text(encoding="utf-8")
    assert "dailylingo_learning_progress_v1" in source
    assert "SCHEMA_VERSION = 1" in source


def test_normalize_id_keeps_leading_zeros(run_js):
    cases = ["0001", "1", 1, "10", 10, "12345", " 0002 ", "0000", "", "abc", "-1", 1.5, None, True, []]
    out = run_js(**run_js_cases(ids=cases))
    assert out["ids"] == [
        "0001",
        "0001",
        "0001",
        "0010",
        "0010",
        "12345",
        "0002",
        "0000",
        "",
        "",
        "",
        "",
        "",
        "",
        "",
    ]


def test_parse_valid_payload(run_js):
    text = json.dumps({"schemaVersion": 1, "completedArticles": ["0001", "0002"], "updatedAt": "2026-10-16T00:00:00.000Z"})
    out = run_js(**run_js_cases(parse=[text]))["parse"][0]
    assert out["ok"] is True
    assert out["ids"] == ["0001", "0002"]
    assert out["duplicates"] == 0
    assert out["invalidCount"] == 0
    assert out["updatedAt"] == "2026-10-16T00:00:00.000Z"


def test_parse_dedupes_and_counts(run_js):
    text = json.dumps({"schemaVersion": 1, "completedArticles": ["0002", "0001", "0002", "2", "oops"]})
    out = run_js(**run_js_cases(parse=[text]))["parse"][0]
    assert out["ok"] is True
    assert out["ids"] == ["0001", "0002"]
    assert out["duplicates"] == 2  # "0002" 重复两次 + "2" 归一后与 "0002" 撞车
    assert out["invalidCount"] == 1


@pytest.mark.parametrize(
    "text, keyword",
    [
        ("", "空"),
        ("   ", "空"),
        ("{ not json", "JSON"),
        (json.dumps([]), "JSON 对象"),
        (json.dumps({"completedArticles": []}), "schemaVersion"),
        (json.dumps({"schemaVersion": 2, "completedArticles": []}), "版本"),
        (json.dumps({"schemaVersion": "1", "completedArticles": []}), "版本"),
        (json.dumps({"schemaVersion": 1}), "数组"),
        (json.dumps({"schemaVersion": 1, "completedArticles": "0001"}), "数组"),
    ],
)
def test_parse_rejects_bad_payload(run_js, text, keyword):
    out = run_js(**run_js_cases(parse=[text]))["parse"][0]
    assert out["ok"] is False
    assert keyword in out["error"]


def test_stats_ignore_unknown_and_duplicates(run_js):
    out = run_js(
        **run_js_cases(
            stats=[
                [["0001", "0002", "9999"], ["0001", "0002", "0003"]],
                [["0001", "0001"], ["0001"]],
                [[], ["0001", "0002"]],
            ]
        )
    )["stats"]
    assert (out[0]["done"], out[0]["total"], out[0]["percent"]) == (2, 3, 67)
    assert (out[1]["done"], out[1]["total"], out[1]["percent"]) == (1, 1, 100)
    assert (out[2]["done"], out[2]["total"], out[2]["percent"]) == (0, 2, 0)
    assert out[2]["set"] == {}


def test_stats_empty_site_does_not_divide_by_zero(run_js):
    out = run_js(**run_js_cases(stats=[[[], []]]))["stats"][0]
    assert out["done"] == 0
    assert out["total"] == 0
    assert out["percent"] == 0
    assert out["ratio"] == 0


def test_chapter_status_uses_actual_count(run_js):
    complete = {"0001": True, "0002": True}
    partial = {"0001": True}
    out = run_js(
        **run_js_cases(
            chapter=[
                [["0001", "0002"], complete],
                [["0001", "0002"], partial],
                [[], {}],
                [["0003"], {"0003": True}],
            ]
        )
    )["chapter"]
    assert out[0] == {"done": 2, "total": 2, "complete": True}
    assert out[1] == {"done": 1, "total": 2, "complete": False}
    assert out[2] == {"done": 0, "total": 0, "complete": False}  # 空章节不算完成
    assert out[3]["complete"] is True  # 一章只有 1 篇也能判定为完成


def test_merge_takes_union(run_js):
    out = run_js(**run_js_cases(merge=[[["0002", "0003"], ["0001", "0002"]], [[], ["0004"]]]))["merge"]
    assert out[0] == ["0001", "0002", "0003"]
    assert out[1] == ["0004"]


def test_partition_splits_known_and_unknown(run_js):
    out = run_js(
        **run_js_cases(partition=[[["0001", "8888", "0002"], ["0001", "0002"]]])
    )["partition"][0]
    assert out["valid"] == ["0001", "0002"]
    assert out["unknown"] == ["8888"]


def test_export_payload_shape(run_js):
    out = run_js(**run_js_cases(exportIds=["0003", "0001", "0001"]))
    payload = out["exportPayload"]
    assert payload["schemaVersion"] == 1
    assert payload["completedArticles"] == ["0001", "0003"]
    assert payload["updatedAt"] == "2026-01-02T03:04:05.000Z"
    assert payload["exportedAt"] == "2026-10-17T04:00:00.000Z"
    assert set(payload) == {"schemaVersion", "completedArticles", "updatedAt", "exportedAt"}
    assert out["fileName"] == "dailylingo-progress-20261017.json"


def test_export_round_trips_through_parser(run_js):
    """导出的 JSON 必须能被导入解析器原样吃下（导入 / 导出同一套结构）。"""
    out = run_js(**run_js_cases(exportIds=["0002", "0004"]))
    text = json.dumps(out["exportPayload"])
    parsed = run_js(**run_js_cases(parse=[text]))["parse"][0]
    assert parsed["ok"] is True
    assert parsed["ids"] == ["0002", "0004"]
