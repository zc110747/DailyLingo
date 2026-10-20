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
import wave
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
        # 构建对属性值做了 HTML 转义，断言也必须用转义后的形式
        link = f'href="src/{build.esc(article.html_name)}"'
        report.check(f"首页链接指向 {article.html_name}", link in index_html)
        report.check(
            f"首页标题格式为「编号. 原始标题」（{article.display_title}）",
            f">{build.esc(article.display_title)}</a>" in index_html,
        )
    report.check("首页无绝对根路径", not ABS_PATH_RE.search(index_html))

    # 学习进度：左上角设置入口 + 统计 + 每篇完成按钮 + Chapter 汇总
    report.check(
        "首页有左上角设置入口（含 ARIA 关联）",
        'data-action="open-settings"' in index_html
        and 'aria-haspopup="dialog"' in index_html
        and 'aria-controls="settings-dialog"' in index_html,
    )
    report.check(
        "首页有设置对话框与导出 / 导入入口",
        '<dialog class="settings-dialog" id="settings-dialog"' in index_html
        and 'data-action="export-progress"' in index_html
        and 'data-action="pick-import"' in index_html
        and "data-import-input" in index_html,
    )
    report.check(
        "首页设置里有「页面语音跟随」开关且默认关闭",
        'id="setting-reading-follow"' in index_html
        and 'data-setting="reading-follow"' in index_html
        and "页面语音跟随" in index_html
        and 'id="setting-reading-follow" checked' not in index_html,
    )
    report.check(
        "首页统计总数等于实际文章数",
        f"data-progress-total>{len(articles)}<" in index_html,
        f"articles={len(articles)}",
    )
    report.check(
        "进度条 aria-valuemax 等于文章总数",
        f'aria-valuemax="{len(articles)}"' in index_html,
    )
    report.check(
        "首页引用 progress.js 且带内容指纹",
        f'src="{build.asset_url(build.PROGRESS_JS)}"' in index_html,
    )
    toggles = index_html.count('data-action="toggle-complete"')
    report.check(
        "每篇文章恰有一个完成切换按钮",
        toggles == len(articles),
        f"toggles={toggles} articles={len(articles)}",
    )
    report.check(
        "完成按钮初始状态全部为未完成",
        index_html.count('aria-pressed="false"') == len(articles),
        f'aria-pressed="false" -> {index_html.count(chr(97) + "ria-pressed=\"false\"")}',
    )
    for article in articles:
        report.check(
            f"完成按钮的编号与文章一致（{article.number_text}）",
            f'data-action="toggle-complete" data-article-id="{article.number_text}"' in index_html,
        )
    report.check(
        "每个 Chapter 都有汇总状态",
        index_html.count("data-chapter-status") == len(chapters),
        f'{index_html.count("data-chapter-status")} != {len(chapters)}',
    )
    generated_totals = sorted(int(m) for m in re.findall(r'data-chapter-total="(\d+)"', index_html))
    expected_totals = sorted(len(c.articles) for c in chapters)
    report.check(
        "Chapter 汇总篇数等于各章实际文章数",
        generated_totals == expected_totals,
        f"{generated_totals} != {expected_totals}",
    )
    # 每章独立的进度条：条数、上限、计数文案都要与本章实际篇数对齐，
    # 不能把首页总进度当作章节进度（那会让多章时每章都显示同一个比例）。
    report.check(
        "每个 Chapter 都有自己的进度条",
        index_html.count("data-chapter-bar") == len(chapters)
        and index_html.count("data-chapter-fill") == len(chapters),
        f'bars={index_html.count("data-chapter-bar")} chapters={len(chapters)}',
    )
    chapter_bar_max = sorted(
        int(m) for m in re.findall(r'data-chapter-bar role="progressbar"[^>]*aria-valuemax="(\d+)"', index_html)
    )
    report.check(
        "章节进度条上限等于本章篇数",
        chapter_bar_max == expected_totals,
        f"{chapter_bar_max} != {expected_totals}",
    )
    report.check(
        "章节进度条初始为空（未完成 0 篇）",
        index_html.count('aria-valuenow="0"') >= len(chapters),
    )
    report.check(
        f"Chapter 容量为 {build.CHUNK} 篇",
        all(c.end - c.start + 1 == build.CHUNK for c in chapters),
        f"{[(c.start, c.end) for c in chapters]}",
    )
    report.check(
        "首页 CSS/JS 带内容指纹",
        f'href="{build.asset_url(build.STYLE_CSS)}"' in index_html
        and f'src="{build.asset_url(build.MAIN_JS)}"' in index_html,
    )

    # 设置面板里的 Android 安装包直链：文件随仓库提交，路径是相对站点的（Pages 子路径）。
    apk_path = build.ROOT / build.ANDROID_APK
    report.check(
        f"安装包 {build.ANDROID_APK} 存在于仓库",
        apk_path.is_file() and apk_path.stat().st_size > 0,
    )
    report.check(
        "设置面板有 Android 安装包下载直链（内容指纹 + download）",
        f'href="{build.ANDROID_APK}?v={build.asset_version(build.ANDROID_APK)}"' in index_html
        and f'download="{build.ANDROID_APK_NAME}"' in index_html
        and 'id="settings-app-title"' in index_html,
        "缺少下载区块（APK 不存在时构建会整块省略）",
    )
    report.check(
        "下载直链是可点击的链接而不是按钮",
        '<a class="btn btn-primary settings-download"' in index_html,
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
        # 左上角返回按钮：必须是链接、指向首页，而且真的排在标题之前
        back_at = html.find('class="back-link"')
        report.check(
            f"{article.html_name} 左上角有返回目录按钮",
            back_at >= 0
            and 'href="../index.html"' in html[back_at : back_at + 200]
            and 0 <= back_at < html.find("<h1"),
            f"back_at={back_at} h1_at={html.find('<h1')}",
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
        # 自动完成：页面必须自带文章编号，并由构建期决定「能不能自动标记」
        # 注意：validate 走的是 load_articles()，此时 has_audio 还没被 build_site 填上，
        # 所以这里要自己看一眼 sources/ 里有没有同名 WAV。
        autoable = bool((sources_dir / article.audio_name).is_file() and article.questions)
        report.check(
            f"{article.html_name} 声明文章编号（自动完成写库用）",
            f'data-article-id="{article.number_text}"' in html,
        )
        report.check(
            f"{article.html_name} 学习状态行与自动标记可用性一致",
            f'data-study-status data-study-auto="{"true" if autoable else "false"}"' in html,
        )
        report.check(
            f"{article.html_name} 引用进度与自动完成脚本（带内容指纹）",
            f'src="../{build.asset_url(build.PROGRESS_JS)}"' in html
            and f'src="../{build.asset_url(build.COMPLETION_JS)}"' in html,
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
        # 缺音频时页面只渲染 player-unavailable 提示、不渲染播放器控件，故分支断言
        if 'data-player' in html:
            rates = re.findall(r'data-rate="([0-9.]+)"', html)
            report.check(
                f"{article.html_name} 播放器控件为音量 + 三档倍速（无 ±5s）",
                rates == ["0.75", "1", "1.25"]
                and 'data-action="back"' not in html
                and 'data-action="forward"' not in html,
                f"rates={rates}",
            )
        else:
            # 用播放器专属标记判断：题目区的 Check / Reset 也带 data-action，不能拿它当依据
            report.check(
                f"{article.html_name} 缺音频时不渲染播放器控件",
                "player-rates" not in html
                and "player-track" not in html
                and "player-toggle" not in html,
            )

        # 音频
        audio_file = sources_dir / article.audio_name
        if audio_file.is_file():
            report.check(
                f"{article.html_name} 关联音频路径 {article.audio_name}",
                f'data-src="../sources/{build.esc(article.audio_name)}"' in html,
            )
        else:
            report.warn(f"{article.html_name} 缺少音频 sources/{article.audio_name}（页面其余部分正常）")
            report.check(
                f"{article.html_name} 缺音频时给出提示且不影响其他区域",
                "player-unavailable" in html and all(h in html for h in SECTION_ORDER),
            )

        # 朗读高亮：正文按句切成 <span data-start/data-end>，时间轴由构建脚本从 WAV 反推
        sentence_re = re.compile(
            r'<span class="sentence" data-start="([0-9.]+)" data-end="([0-9.]+)">(.*?)</span>',
            re.S,
        )
        spans = sentence_re.findall(html)
        if audio_file.is_file():
            starts = [float(s) for s, _e, _t in spans]
            ends = [float(e) for _s, e, _t in spans]
            report.check(
                f"{article.html_name} 正文逐句标注时间轴",
                len(spans) > 1,
                f"spans={len(spans)}",
            )
            report.check(
                f"{article.html_name} 句子时间轴严格递增且首尾相接",
                starts == sorted(starts)
                and len(set(starts)) == len(starts)
                and all(a < b for a, b in zip(starts, ends))
                and all(abs(ends[i] - starts[i + 1]) < 0.005 for i in range(len(starts) - 1)),
                f"starts={starts[:3]}…",
            )
            report.check(
                f"{article.html_name} 第一句时间轴从 0 开始",
                bool(starts) and starts[0] == 0.0,
                f"starts[0]={starts[0] if starts else None}",
            )
            with wave.open(str(audio_file), "rb") as wav:
                audio_duration = wav.getnframes() / float(wav.getframerate())
            report.check(
                f"{article.html_name} 时间轴覆盖到音频结尾",
                bool(ends) and abs(ends[-1] - audio_duration) <= 0.05,
                f"last_end={ends[-1] if ends else None} duration={audio_duration:.2f}",
            )
            # 句子拼回去必须与原文逐字一致（切分不允许吞字或重复，否则高亮会整体错位）
            expected = [" ".join(build.html.unescape(p).split()) for p in article.paragraphs]
            rebuilt = [
                " ".join(build.html.unescape(text).split())
                for paragraph in re.findall(r"<p>(.*?)</p>", html, re.S)
                for text in [" ".join(t for _s, _e, t in sentence_re.findall(paragraph))]
                if text.strip()
            ]
            report.check(
                f"{article.html_name} 逐句切分不丢字、不改字",
                rebuilt == expected,
                f"段落数 {len(rebuilt)} vs 原文 {len(expected)}",
            )
        else:
            report.check(
                f"{article.html_name} 缺音频时不输出句子时间轴",
                not spans,
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
        prev_link = f'href="{build.esc(article.prev.html_name)}"' if article.prev else None
        next_link = f'href="{build.esc(article.next.html_name)}"' if article.next else None
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
        build.PROGRESS_JS,
        build.COMPLETION_JS,
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
    progress_js = out_dir / build.PROGRESS_JS
    progress_src = progress_js.read_text(encoding="utf-8") if progress_js.is_file() else ""
    report.check(
        f"{build.PROGRESS_JS} 声明存储键与 schema 版本",
        "dailylingo_learning_progress_v1" in progress_src and "SCHEMA_VERSION = 1" in progress_src,
    )
    report.check(
        f"{build.PROGRESS_JS} 只操作相对资源、不发网络请求",
        "fetch(" not in progress_src and "XMLHttpRequest" not in progress_src,
    )
    style_src = (out_dir / build.STYLE_CSS).read_text(encoding="utf-8")
    report.check(
        "style.css 定义「当前句」高亮样式",
        ".section-article .sentence" in style_src and ".sentence.is-active" in style_src,
    )
    player_src = (out_dir / build.PLAYER_JS).read_text(encoding="utf-8")
    report.check(
        f"{build.PLAYER_JS} 依据 data-start 驱动句子高亮",
        'querySelectorAll("[data-start]")' in player_src,
    )
    main_src = (out_dir / build.MAIN_JS).read_text(encoding="utf-8")
    report.check(
        f"{build.MAIN_JS} 提供「页面语音跟随」设置（键在两侧一致）",
        "dailylingo_reading_follow_v1" in main_src
        and "readingFollow" in main_src
        and "readingFollow" in player_src
        and "readingFollow" in progress_src,
    )
    report.check(
        "语音跟随开关默认关闭（读取失败一律按不跟随处理）",
        player_src.count("shouldFollow()") >= 1
        and "return false; // 存储不可用 ⇒ 用默认值（不跟随）" in main_src,
    )

    # 文章页自动完成：两个脚本不能各写一套事件名，靠这两个断言锁住契约
    completion_js = out_dir / build.COMPLETION_JS
    completion_src = completion_js.read_text(encoding="utf-8") if completion_js.is_file() else ""
    report.check(
        "收听事件名在播放器与自动完成脚本里一致",
        '"dailylingo:listen"' in player_src and '"dailylingo:listen"' in completion_src,
    )
    report.check(
        "判分事件名在 main.js 与自动完成脚本里一致",
        '"dailylingo:quiz"' in main_src and '"dailylingo:quiz"' in completion_src,
    )
    report.check(
        "自动完成阈值声明为 0.9（听够才打勾）",
        "REQUIRED_RATIO = 0.9" in completion_src,
    )
    report.check(
        f"{build.COMPLETION_JS} 不发起网络请求",
        "fetch(" not in completion_src
        and "XMLHttpRequest" not in completion_src
        and "sendBeacon" not in completion_src,
    )
    report.check(
        f"{build.PROGRESS_JS} 暴露文章页需要的写入接口",
        "markCompleted" in progress_src and "isCompleted" in progress_src,
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
                # 最常见的假失败：工作副本被签出成 CRLF，而构建始终写 LF
                # （core.autocrlf=true 且仓库缺 .gitattributes 时全新 clone 就会这样）
                hint = ""
                if a_bytes.replace(b"\r\n", b"\n") == b_bytes.replace(b"\r\n", b"\n"):
                    hint = "（仅行尾差异：磁盘上是 CRLF —— 检查 .gitattributes 与 core.autocrlf）"
                report.check(f"重复构建 {rel} 字节一致{hint}", False)
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
