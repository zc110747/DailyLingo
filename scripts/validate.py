#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""DailyLingo 项目验证脚本。

对 ``content/`` 中的数据与 ``index.html`` / ``src/*.html`` 的生成结果做端到端校验，
并检查 GitHub Pages 项目子路径兼容性（所有资源路径必须是相对路径）。

    python scripts/validate.py
    python scripts/validate.py --content content --out . --sources sources

退出码：0 = 全部通过；1 = 存在失败项。
"""

from __future__ import annotations

import argparse
import importlib.util
import json
import re
import shutil
import sys
import tempfile
from pathlib import Path
from typing import Sequence

_HERE = Path(__file__).resolve().parent


def _load_build_module():
    spec = importlib.util.spec_from_file_location("dl_build", _HERE / "build.py")
    module = importlib.util.module_from_spec(spec)
    sys.modules["dl_build"] = module
    spec.loader.exec_module(module)
    return module


build = _load_build_module()


class Report:
    def __init__(self) -> None:
        self.passed = 0
        self.failed: list[str] = []
        self.warnings: list[str] = []

    def check(self, name: str, condition: bool, detail: str = "") -> bool:
        if condition:
            self.passed += 1
            print(f"  [PASS] {name}")
        else:
            self.failed.append(f"{name}{(' — ' + detail) if detail else ''}")
            print(f"  [FAIL] {name}{(' — ' + detail) if detail else ''}")
        return condition

    def warn(self, message: str) -> None:
        self.warnings.append(message)
        print(f"  [WARN] {message}")

    def summary(self) -> int:
        print()
        print(f"结果：PASS {self.passed} / FAIL {len(self.failed)} / WARN {len(self.warnings)}")
        if self.failed:
            print("失败项：")
            for item in self.failed:
                print(f"  - {item}")
            return 1
        return 0


SECTION_ORDER = ["Article", "Words", "Questions", "Answers", "Continue"]
ABS_PATH_RE = re.compile(r'(?:href|src)="/(?!/)')


def validate(content_dir: Path, out_dir: Path, sources_dir: Path) -> int:
    report = Report()

    print("== 1. 文章数据 ==")
    try:
        articles, _ = build.load_articles(content_dir)
    except build.BuildError as exc:
        report.check("content/ 文章解析", False, str(exc))
        return report.summary()
    report.check("content/ 文章解析", True)
    report.check("文章数量 > 0", len(articles) > 0, f"实际 {len(articles)}")

    numbers = [a.number for a in articles]
    report.check("编号唯一", len(numbers) == len(set(numbers)))
    report.check("编号升序排列", numbers == sorted(numbers))
    for article in articles:
        report.check(
            f"文件名与编号一致（{article.source.name}）",
            article.html_name.startswith(build.display_number(article.number) + "."),
        )
        report.check(
            f"标题含编号（{article.display_title}）",
            article.display_title.startswith(build.display_number(article.number) + "."),
        )

    print("== 2. Chapter 分组 ==")
    chapters = build.group_chapters(articles)
    report.check("Chapter 数量 > 0", len(chapters) > 0)
    for chapter in chapters:
        report.check(
            f"{chapter.label} 区间边界正确",
            all(
                build.chapter_bounds(a.number) == (chapter.start, chapter.end)
                for a in chapter.articles
            ),
        )
        report.check(
            f"{chapter.label} 组内升序",
            [a.number for a in chapter.articles] == sorted(a.number for a in chapter.articles),
        )
    expected_labels = sorted({build.chapter_label(*build.chapter_bounds(n)) for n in numbers})
    report.check(
        "只输出含真实文章的 Chapter",
        [c.label for c in chapters] == expected_labels,
        f"{[c.label for c in chapters]} != {expected_labels}",
    )
    report.check(
        "不存在空 Chapter",
        all(c.articles for c in chapters),
    )

    print("== 3. 首页 index.html ==")
    index_path = out_dir / "index.html"
    if not report.check("index.html 存在", index_path.is_file()):
        return report.summary()
    index_html = index_path.read_text(encoding="utf-8")

    report.check("首页包含品牌名", build.BRAND in index_html)
    report.check("首页包含折叠目录容器", 'class="catalogue"' in index_html)
    report.check("首页使用原生 <details>/<summary>", "<details" in index_html and "<summary" in index_html)
    report.check(
        "首页声明 SVG + PNG + apple-touch 图标",
        f'href="{build.FAVICON_SVG}"' in index_html
        and f'href="{build.FAVICON_PNG32}"' in index_html
        and f'href="{build.FAVICON_PNG180}"' in index_html,
    )
    report.check(
        "首页品牌名旁显示站点图标",
        'class="brand-icon"' in index_html and f'src="{build.FAVICON_SVG}"' in index_html,
    )

    open_count = len(re.findall(r"<details class=\"chapter\" open>", index_html))
    detail_count = len(re.findall(r'<details class="chapter"', index_html))
    report.check("chapter 分组数量与数据一致", detail_count == len(chapters), f"{detail_count} != {len(chapters)}")
    report.check("仅第一个 Chapter 默认展开", open_count == (1 if chapters else 0), f"open={open_count}")

    for chapter in chapters:
        report.check(f"首页显示 {chapter.label}", chapter.label in index_html)

    # 首页不得出现额外信息
    for forbidden in ("words-table", "question-list", "player", "article-summary", "难度", "音频状态"):
        report.check(f"首页不出现 “{forbidden}”", forbidden not in index_html)

    # 首页链接
    for article in articles:
        link = f'href="src/{article.html_name}"'
        report.check(f"首页链接指向 {article.html_name}", link in index_html)
        report.check(
            f"首页标题格式为「编号. 原始标题」（{article.display_title}）",
            f">{build.esc(article.display_title)}</a>" in index_html,
        )
    report.check("首页无绝对根路径", not ABS_PATH_RE.search(index_html))
    report.check(
        "首页 CSS/JS 带内容指纹",
        f'href="{build.asset_url(build.STYLE_CSS)}"' in index_html
        and f'src="{build.asset_url(build.MAIN_JS)}"' in index_html,
    )

    print("== 4. 文章页 ==")
    for article in articles:
        page = out_dir / "src" / article.html_name
        if not report.check(f"{article.html_name} 存在", page.is_file()):
            continue
        html = page.read_text(encoding="utf-8")

        positions = [html.find(f'id="{s.lower()}"') for s in SECTION_ORDER]
        headings = [f">{s}</h2>" in html for s in SECTION_ORDER]
        report.check(
            f"{article.html_name} 五个区域齐全且顺序正确",
            all(p >= 0 for p in positions) and positions == sorted(positions) and all(headings),
            f"positions={positions} headings={headings}",
        )
        report.check(
            f"{article.html_name} 浏览器标签包含编号",
            f"<title>{build.esc(article.page_title)}</title>" in html,
        )
        report.check(
            f"{article.html_name} 主标题与首页一致",
            f'>{build.esc(article.title)}</h1>' in html,
        )
        report.check(f"{article.html_name} 无绝对根路径", not ABS_PATH_RE.search(html))
        report.check(
            f"{article.html_name} 引用的 CSS/JS 路径正确",
            f'href="../{build.asset_url(build.STYLE_CSS)}"' in html
            and f'src="../{build.asset_url(build.MAIN_JS)}"' in html
            and f'src="../{build.asset_url(build.PLAYER_JS)}"' in html,
        )
        report.check(
            f"{article.html_name} 返回目录链接存在",
            'href="../index.html"' in html,
        )
        report.check(
            f"{article.html_name} 声明站点图标（相对路径 ../）",
            f'href="../{build.FAVICON_SVG}"' in html
            and f'href="../{build.FAVICON_PNG32}"' in html
            and f'href="../{build.FAVICON_PNG180}"' in html,
        )

        # 播放器必须位于 Article 标题之下、正文之上（先播放再阅读）
        article_at = html.find('id="article"')
        words_at = html.find('id="words"')
        player_at = html.find("data-player")
        if player_at < 0:
            player_at = html.find("player-unavailable")
        first_p = html.find("<p>", article_at)
        report.check(
            f"{article.html_name} 播放器在 Article 区内且位于正文之前",
            article_at >= 0
            and player_at > article_at
            and player_at < words_at
            and (first_p < 0 or player_at < first_p),
            f"article={article_at} player={player_at} words={words_at} first_p={first_p}",
        )

        # 播放器与正文之间的分隔线
        divider_at = html.find('<hr class="player-divider">')
        report.check(
            f"{article.html_name} 播放器与正文之间有分隔线",
            divider_at > player_at and (first_p < 0 or divider_at < first_p),
            f"player={player_at} divider={divider_at} first_p={first_p}",
        )

        # 播放器控件：±5s 已移除，倍速只保留 0.75x / 1x / 1.25x
        rates = re.findall(r'data-rate="([0-9.]+)"', html)
        report.check(
            f"{article.html_name} 播放器控件为音量 + 三档倍速（无 ±5s）",
            rates == ["0.75", "1", "1.25"]
            and 'data-action="back"' not in html
            and 'data-action="forward"' not in html,
            f"rates={rates}",
        )

        # 音频
        audio_file = sources_dir / article.audio_name
        if audio_file.is_file():
            report.check(
                f"{article.html_name} 关联音频路径 {article.audio_name}",
                f'data-src="../sources/{article.audio_name}"' in html,
            )
        else:
            report.warn(f"{article.html_name} 缺少音频 sources/{article.audio_name}（页面其余部分正常）")
            report.check(
                f"{article.html_name} 缺音频时给出提示且不影响其他区域",
                "player-unavailable" in html and all(h in html for h in SECTION_ORDER),
            )

        # 单词表
        if article.words:
            report.check(
                f"{article.html_name} 单词表行数与数据一致",
                html.count('<td class="word-cell">') == len(article.words),
            )

        # 题目与答案
        report.check(
            f"{article.html_name} 题目数量与数据一致",
            html.count('class="question"') == len(article.questions),
        )
        match = re.search(
            r'<script type="application/json" id="quiz-data">\s*(\{.*?\})\s*</script>',
            html,
            re.S,
        )
        if report.check(f"{article.html_name} 内嵌判分数据", match is not None):
            quiz = json.loads(match.group(1))
            report.check(
                f"{article.html_name} 判分数据覆盖全部题目",
                set(quiz) == {q.qid for q in article.questions},
            )
            for q in article.questions:
                entry = quiz.get(q.qid, {})
                report.check(
                    f"{article.html_name} {q.qid} 判分答案与数据一致",
                    entry.get("answer") == q.answer and entry.get("acceptable") == q.acceptable,
                )
                if q.qtype == build.TYPE_CHOICE:
                    report.check(
                        f"{article.html_name} {q.qid} 正确答案出现在 Answers",
                        q.answer.upper() in html,
                    )
        report.check(
            f"{article.html_name} Answers 默认折叠",
            '<details class="answers-disclosure">' in html
            and '<details class="answers-disclosure" open' not in html,
        )

        # 导航
        prev_link = f'href="{article.prev.html_name}"' if article.prev else None
        next_link = f'href="{article.next.html_name}"' if article.next else None
        if prev_link:
            report.check(f"{article.html_name} 上一篇链接正确", prev_link in html)
            report.check(
                f"{article.html_name} 上一篇标题正确",
                build.esc(article.prev.display_title) in html,
            )
        else:
            report.check(f"{article.html_name} 首篇无上一篇链接", "上一篇：无" in html)
        if next_link:
            report.check(f"{article.html_name} 下一篇链接正确", next_link in html)
            report.check(
                f"{article.html_name} 下一篇标题正确",
                build.esc(article.next.display_title) in html,
            )
        else:
            report.check(f"{article.html_name} 末篇无下一篇链接", "下一篇：无" in html)

    print("== 5. 静态资源 ==")
    for rel in (
        "assets/css/style.css",
        "assets/js/main.js",
        "assets/js/audio-player.js",
        build.FAVICON_SVG,
        build.FAVICON_PNG32,
        build.FAVICON_PNG180,
    ):
        report.check(f"{rel} 存在", (out_dir / rel).is_file())
    for rel in (build.FAVICON_PNG32, build.FAVICON_PNG180):
        icon = out_dir / rel
        report.check(
            f"{rel} 是有效 PNG",
            icon.is_file() and icon.read_bytes()[:8] == b"\x89PNG\r\n\x1a\n",
        )
    svg_icon = out_dir / build.FAVICON_SVG
    report.check(
        f"{build.FAVICON_SVG} 是有效 SVG",
        svg_icon.is_file() and b"<svg" in svg_icon.read_bytes()[:400],
    )

    print("== 6. 构建可重复性 ==")
    with tempfile.TemporaryDirectory() as tmp:
        tmp_out = Path(tmp)
        build.build_site(content_dir, tmp_out, sources_dir)
        identical = True
        for rel in [Path("index.html")] + [Path("src") / a.html_name for a in articles]:
            a_bytes = (out_dir / rel).read_bytes()
            b_bytes = (tmp_out / rel).read_bytes()
            if a_bytes != b_bytes:
                identical = False
                report.check(f"重复构建 {rel} 字节一致", False)
        report.check("重复构建结果稳定（字节级一致）", identical)

    return report.summary()


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="验证 DailyLingo 站点")
    parser.add_argument("--content", default=str(build.DEFAULT_CONTENT_DIR))
    parser.add_argument("--out", default=str(build.DEFAULT_OUT_DIR))
    parser.add_argument("--sources", default=str(build.DEFAULT_SOURCES_DIR))
    args = parser.parse_args(argv)

    return validate(Path(args.content), Path(args.out), Path(args.sources))


if __name__ == "__main__":
    raise SystemExit(main())
