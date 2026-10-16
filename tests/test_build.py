# -*- coding: utf-8 -*-
"""DailyLingo 构建脚本的自动化测试。

覆盖：文章数据解析与校验、编号规则、Chapter 分组、标题与导航一致性、
单词表 / 题目 / 答案、音频与路径、GitHub Pages 相对路径兼容、构建可重复性。

所有测试均使用临时目录，不会污染或覆盖真实的 ``content/`` 与 ``sources/``。
"""

from __future__ import annotations

import json
import re
import struct
from pathlib import Path

import pytest

import build

# --------------------------------------------------------------------------
# 测试数据构造
# --------------------------------------------------------------------------

WORDS_DEFAULT = """| Word | Pronunciation | 中文释义 |
| --- | --- | --- |
| **hobby** | /ˈhɒbi/ | 爱好 |
| **decide** | /dɪˈsaɪd/ | 决定 |"""

QUESTIONS_DEFAULT = """**What does David want to learn?**

A. How to drive

B. How to cook

C. How to swim"""


def article_md(
    title: str = "A New Hobby",
    article: str = "My name is David.",
    words: str | None = WORDS_DEFAULT,
    questions: str | None = QUESTIONS_DEFAULT,
    answers: str | None = "B",
    front_matter: str | None = None,
) -> str:
    parts: list[str] = []
    if front_matter:
        parts.append("---\n" + front_matter.strip() + "\n---\n")
    parts.append(f"# {title}\n")
    parts.append("## Article\n\n" + article + "\n")
    if words is not None:
        parts.append("## Words\n\n" + words + "\n")
    if questions is not None:
        parts.append("## Questions\n\n" + questions + "\n")
    if answers is not None:
        parts.append("## Answers\n\n" + answers + "\n")
    parts.append("## Continues\n\n- [cataloge](./catalogue.md)\n")
    return "\n".join(parts)


def write_content(tmp_path: Path, files: dict[str, str], audio: list[str] | None = None) -> Path:
    """把 ``{"0001.A_New_Hobby.md": "<md>"}`` 写到临时 content 目录。"""
    content = tmp_path / "content"
    content.mkdir(parents=True, exist_ok=True)
    for name, text in files.items():
        (content / name).write_text(text, encoding="utf-8", newline="\n")
    sources = tmp_path / "sources"
    sources.mkdir(parents=True, exist_ok=True)
    for name in audio or []:
        (sources / name).write_bytes(_MINIMAL_WAV)
    return content


_MINIMAL_WAV = (
    b"RIFF" + (36).to_bytes(4, "little") + b"WAVE"
    + b"fmt " + (16).to_bytes(4, "little") + (1).to_bytes(2, "little")
    + (1).to_bytes(2, "little") + (16000).to_bytes(4, "little")
    + (32000).to_bytes(4, "little") + (2).to_bytes(2, "little")
    + (16).to_bytes(2, "little") + b"data" + (0).to_bytes(4, "little")
)


def make_site(tmp_path: Path, files: dict[str, str], audio: list[str] | None = None):
    content = write_content(tmp_path, files, audio)
    out = tmp_path / "out"
    result = build.build_site(content, out, tmp_path / "sources")
    return result, out, content, tmp_path / "sources"


def read(path: Path) -> str:
    return path.read_text(encoding="utf-8")


# --------------------------------------------------------------------------
# 11.1 文章数据
# --------------------------------------------------------------------------


def test_parse_basic_article(tmp_path):
    (tmp_path / "0001.A_New_Hobby.md").write_text(article_md(), encoding="utf-8", newline="\n")
    art = build.parse_article_file(tmp_path / "0001.A_New_Hobby.md")

    assert art.number == 1
    assert art.number_text == "0001"
    assert art.title == "A New Hobby"
    assert art.slug == "A_New_Hobby"
    assert art.display_title == "0001. A New Hobby"
    assert art.page_title == "0001. A New Hobby | DailyLingo"
    assert art.audio_name == "0001.A_New_Hobby.wav"
    assert art.html_name == "0001.A_New_Hobby.html"
    assert art.paragraphs == ["My name is David."]
    assert [w.word for w in art.words] == ["hobby", "decide"]
    assert art.words[0].ipa == "/ˈhɒbi/"
    assert art.words[0].meaning == "爱好"
    assert len(art.questions) == 1
    assert art.questions[0].qtype == build.TYPE_CHOICE
    assert art.questions[0].answer == "B"
    assert [o.key for o in art.questions[0].options] == ["A", "B", "C"]


def test_missing_number_in_filename(tmp_path):
    bad = tmp_path / "A_New_Hobby.md"
    bad.write_text(article_md(), encoding="utf-8")
    with pytest.raises(build.BuildError, match="文件名不符合编号规则"):
        build.parse_article_file(bad)


def test_zero_number_rejected(tmp_path):
    bad = tmp_path / "0000.A_New_Hobby.md"
    bad.write_text(article_md(), encoding="utf-8")
    with pytest.raises(build.BuildError, match="非法文章编号"):
        build.parse_article_file(bad)


def test_missing_title(tmp_path):
    bad = tmp_path / "0001.A_New_Hobby.md"
    bad.write_text("## Article\n\nHello world.\n\n## Questions\n\n**Q?**\n\nA. a\n\nB. b\n\n## Answers\n\nA\n",
                   encoding="utf-8")
    with pytest.raises(build.BuildError, match="缺少标题"):
        build.parse_article_file(bad)


def test_missing_article_body(tmp_path):
    bad = tmp_path / "0001.A_New_Hobby.md"
    bad.write_text("# Title\n\n## Words\n\n| Word |\n| --- |\n| a |\n", encoding="utf-8")
    with pytest.raises(build.BuildError, match="缺少 `## Article`"):
        build.parse_article_file(bad)


def test_front_matter_id_must_match_filename(tmp_path):
    bad = tmp_path / "0001.A_New_Hobby.md"
    bad.write_text(article_md(front_matter='id: "0002"\ntitle: "A New Hobby"'), encoding="utf-8")
    with pytest.raises(build.BuildError, match="不一致"):
        build.parse_article_file(bad)


def test_front_matter_overrides_title_and_audio(tmp_path):
    path = tmp_path / "0007.Custom.md"
    path.write_text(
        article_md(front_matter='id: "0007"\ntitle: "Custom Title"\naudio: "custom.wav"'),
        encoding="utf-8",
    )
    art = build.parse_article_file(path)
    assert art.title == "Custom Title"
    assert art.audio_name == "custom.wav"
    assert art.number == 7


def test_duplicate_number_detected(tmp_path):
    files = {
        "0001.A_New_Hobby.md": article_md("A New Hobby"),
        "0001.B_Other.md": article_md("B Other"),
    }
    write_content(tmp_path, files)
    with pytest.raises(build.BuildError, match="重复编号 0001"):
        build.load_articles(tmp_path / "content")


def test_unicode_and_special_characters(tmp_path):
    title = "中文标题 & “Quoted” ‘Title’ — Dash"
    files = {
        "0001.Unicode.md": article_md(
            title=title.replace("&", "and"),
            words="| Word | Pronunciation | 中文释义 |\n| --- | --- | --- |\n| **café** | /kæˈfeɪ/ | 咖啡馆 & 餐厅 |",
            questions="**你喜欢 café 吗？**\n\nA. 是\n\nB. 否",
            answers="B",
        )
    }
    result, out, _, _ = make_site(tmp_path, files)
    art = result.articles[0]
    assert art.words[0].word == "café"
    html = read(out / "src" / art.html_name)
    assert "咖啡馆 &amp; 餐厅" in html
    assert "你喜欢 café 吗？" in html


def test_markdown_escapes_html_in_content(tmp_path):
    files = {"0001.Esc.md": article_md(article="Tom & Jerry <script>alert(1)</script>")}
    result, out, _, _ = make_site(tmp_path, files)
    html = read(out / "src" / result.articles[0].html_name)
    assert "Tom &amp; Jerry" in html
    assert "<script>alert(1)</script>" not in html


@pytest.mark.parametrize(
    "number,expected",
    [
        (1, "0001"),
        (10, "0010"),
        (100, "0100"),
        (999, "0999"),
        (9999, "9999"),
        (10000, "10000"),
        (10001, "10001"),
        (123456, "123456"),
    ],
)
def test_display_number_rules(number, expected):
    assert build.display_number(number) == expected


def test_display_title_uses_number_prefix():
    assert build.display_title(1, "A New Hobby") == "0001. A New Hobby"
    assert build.display_title(10000, "Far Future") == "10000. Far Future"
    assert build.page_title(2, "A Busy Morning") == "0002. A Busy Morning | DailyLingo"


# --------------------------------------------------------------------------
# 11.2 Chapter 分组
# --------------------------------------------------------------------------


@pytest.mark.parametrize(
    "number,expected",
    [
        (1, (1, 100)),
        (100, (1, 100)),
        (101, (101, 200)),
        (200, (101, 200)),
        (201, (201, 300)),
        (300, (201, 300)),
        (301, (301, 400)),
        (9999, (9901, 10000)),
        (10001, (10001, 10100)),
    ],
)
def test_chapter_bounds(number, expected):
    assert build.chapter_bounds(number) == expected


@pytest.mark.parametrize(
    "number,label",
    [
        (1, "Chapter 0001\u20130100"),
        (100, "Chapter 0001\u20130100"),
        (101, "Chapter 0101\u20130200"),
        (200, "Chapter 0101\u20130200"),
        (201, "Chapter 0201\u20130300"),
    ],
)
def test_chapter_label(number, label):
    assert build.chapter_label(*build.chapter_bounds(number)) == label


def test_single_article_creates_one_chapter(tmp_path):
    result, out, _, _ = make_site(tmp_path, {"0001.A.md": article_md("A")})
    assert [c.label for c in result.chapters] == ["Chapter 0001\u20130100"]
    assert "<details class=\"chapter\" open>" in read(out / "index.html")


def test_only_existing_chapters_are_rendered(tmp_path):
    files = {
        "0001.A.md": article_md("A"),
        "0002.B.md": article_md("B"),
        "0005.E.md": article_md("E"),
        "0101.F.md": article_md("F"),
    }
    result, out, _, _ = make_site(tmp_path, files)
    labels = [c.label for c in result.chapters]
    assert labels == ["Chapter 0001\u20130100", "Chapter 0101\u20130200"]
    index = read(out / "index.html")
    assert "Chapter 0201\u20130300" not in index
    assert index.count("<details class=\"chapter\"") == 2


def test_gaps_do_not_change_boundaries(tmp_path):
    files = {
        "0001.A.md": article_md("A"),
        "0002.B.md": article_md("B"),
        "0005.E.md": article_md("E"),
        "0101.F.md": article_md("F"),
    }
    result, _, _, _ = make_site(tmp_path, files)
    first, second = result.chapters
    assert [a.number for a in first.articles] == [1, 2, 5]
    assert [a.number for a in second.articles] == [101]
    assert (first.start, first.end) == (1, 100)
    assert (second.start, second.end) == (101, 200)


def test_articles_sorted_ascending_inside_chapter(tmp_path):
    files = {
        "0009.I.md": article_md("I"),
        "0003.C.md": article_md("C"),
        "0001.A.md": article_md("A"),
    }
    result, _, _, _ = make_site(tmp_path, files)
    assert [a.number for a in result.chapters[0].articles] == [1, 3, 9]
    assert [a.number for a in result.articles] == [1, 3, 9]


def test_first_chapter_open_others_closed(tmp_path):
    files = {"0001.A.md": article_md("A"), "0101.B.md": article_md("B"), "0201.C.md": article_md("C")}
    result, out, _, _ = make_site(tmp_path, files)
    index = read(out / "index.html")
    assert index.count("<details class=\"chapter\" open>") == 1
    assert index.count("<details class=\"chapter\"") == 3
    assert index.index("Chapter 0001\u20130100") < index.index("Chapter 0101\u20130200")


def test_new_article_creates_new_chapter_on_rebuild(tmp_path):
    content = write_content(tmp_path, {"0001.A.md": article_md("A")})
    out = tmp_path / "out"
    sources = tmp_path / "sources"

    first = build.build_site(content, out, sources)
    assert len(first.chapters) == 1

    (content / "0101.B.md").write_text(article_md("B"), encoding="utf-8", newline="\n")
    second = build.build_site(content, out, sources)
    assert [c.label for c in second.chapters] == [
        "Chapter 0001\u20130100",
        "Chapter 0101\u20130200",
    ]
    index = read(out / "index.html")
    assert "Chapter 0101\u20130200" in index
    assert (out / "src" / "0101.B.html").is_file()


def test_removing_last_article_removes_chapter_on_rebuild(tmp_path):
    content = write_content(tmp_path, {"0001.A.md": article_md("A"), "0101.B.md": article_md("B")})
    out = tmp_path / "out"
    sources = tmp_path / "sources"
    build.build_site(content, out, sources)
    assert "Chapter 0101\u20130200" in read(out / "index.html")

    (content / "0101.B.md").unlink()
    result = build.build_site(content, out, sources)
    assert [c.label for c in result.chapters] == ["Chapter 0001\u20130100"]
    assert "Chapter 0101\u20130200" not in read(out / "index.html")


def test_index_links_point_to_existing_pages(tmp_path):
    files = {"0001.A.md": article_md("A"), "0101.B.md": article_md("B")}
    result, out, _, _ = make_site(tmp_path, files)
    hrefs = re.findall(r'href="(src/[^"]+\.html)"', read(out / "index.html"))
    assert len(hrefs) == 2
    for href in hrefs:
        assert (out / href).is_file()


def test_chapter_groups_cover_every_article(tmp_path):
    files = {
        "0001.A.md": article_md("A"),
        "0002.B.md": article_md("B"),
        "0101.C.md": article_md("C"),
        "0301.D.md": article_md("D"),
    }
    result, _, _, _ = make_site(tmp_path, files)
    grouped = sorted(a.number for c in result.chapters for a in c.articles)
    assert grouped == [1, 2, 101, 301]


# --------------------------------------------------------------------------
# 11.3 标题与导航
# --------------------------------------------------------------------------


def test_titles_are_consistent_everywhere(tmp_path):
    files = {"0001.A.md": article_md("Alpha Story"), "0002.B.md": article_md("Beta Story")}
    result, out, _, _ = make_site(tmp_path, files)
    index = read(out / "index.html")
    page1 = read(out / "src" / "0001.A.html")
    page2 = read(out / "src" / "0002.B.html")

    for article, page in ((result.articles[0], page1), (result.articles[1], page2)):
        assert article.display_title in index           # 首页列表
        assert f"<title>{article.page_title}</title>" in page  # 浏览器标签
        assert article.display_title in page            # 导航引用

    # 首页列表标题就是「编号. 原始标题」，与详情页、浏览器标签、导航完全一致
    assert '<a class="article-link" href="src/0001.A.html">0001. Alpha Story</a>' in index
    assert '<a class="article-link" href="src/0002.B.html">0002. Beta Story</a>' in index


def test_browser_title_contains_number(tmp_path):
    result, out, _, _ = make_site(tmp_path, {"0001.A.md": article_md("Alpha")})
    page = read(out / "src" / result.articles[0].html_name)
    assert "<title>0001. Alpha | DailyLingo</title>" in page


def test_prev_next_navigation(tmp_path):
    files = {
        "0001.A.md": article_md("A"),
        "0002.B.md": article_md("B"),
        "0003.C.md": article_md("C"),
    }
    result, out, _, _ = make_site(tmp_path, files)
    p2 = read(out / "src" / "0002.B.html")
    assert 'href="0001.A.html"' in p2 and "上一篇：0001. A" in p2
    assert 'href="0003.C.html"' in p2 and "下一篇：0003. C" in p2


def test_first_and_last_article_navigation_boundaries(tmp_path):
    files = {"0001.A.md": article_md("A"), "0002.B.md": article_md("B")}
    result, out, _, _ = make_site(tmp_path, files)
    first = read(out / "src" / "0001.A.html")
    last = read(out / "src" / "0002.B.html")
    assert "上一篇：无" in first and "下一篇：0002. B" in first
    assert "下一篇：无" in last and "上一篇：0001. A" in last


def test_navigation_is_independent_of_chapter_grouping(tmp_path):
    files = {"0001.A.md": article_md("A"), "0101.B.md": article_md("B")}
    result, out, _, _ = make_site(tmp_path, files)
    a = read(out / "src" / "0001.A.html")
    b = read(out / "src" / "0101.B.html")
    assert "下一篇：0101. B" in a
    assert "上一篇：0001. A" in b


def test_every_article_links_back_to_index(tmp_path):
    result, out, _, _ = make_site(tmp_path, {"0001.A.md": article_md("A")})
    page = read(out / "src" / result.articles[0].html_name)
    assert 'href="../index.html"' in page


# --------------------------------------------------------------------------
# 11.4 单词、题目与答案
# --------------------------------------------------------------------------


def test_words_table_generated(tmp_path):
    result, out, _, _ = make_site(tmp_path, {"0001.A.md": article_md("A")})
    html = read(out / "src" / result.articles[0].html_name)
    assert html.count('<td class="word-cell">hobby</td>') == 1
    assert html.count('class="word-cell"') == 2
    assert "爱好" in html


def test_words_extended_columns(tmp_path):
    words = (
        "| 单词 | 音标 | 词性 | 中文释义 | 例句 |\n"
        "| --- | --- | --- | --- | --- |\n"
        "| hobby | /ˈhɒbi/ | noun | 爱好 | Reading is my hobby. |"
    )
    result, out, _, _ = make_site(tmp_path, {"0001.A.md": article_md("A", words=words)})
    html = read(out / "src" / result.articles[0].html_name)
    assert "Reading is my hobby." in html
    for header in ("单词", "音标", "词性", "中文释义", "例句"):
        assert f">{header}</th>" in html


def test_empty_words_shows_placeholder(tmp_path):
    result, out, _, _ = make_site(tmp_path, {"0001.A.md": article_md("A", words=None)})
    html = read(out / "src" / result.articles[0].html_name)
    assert "暂时没有重点单词" in html


def test_choice_question_type_inferred_from_options(tmp_path):
    result, _, _, _ = make_site(tmp_path, {"0001.A.md": article_md("A")})
    assert result.articles[0].questions[0].qtype == build.TYPE_CHOICE


def test_fill_question_without_options_is_fill(tmp_path):
    questions = (
        "Question 1: What day is it?\n\nA. Monday\n\nB. Saturday\n\n"
        "Question 2: Why does Tom feel happy?"
    )
    answers = "B\n\nQuestion2: He helped someone."
    result, out, _, _ = make_site(tmp_path, {"0001.A.md": article_md("A", questions=questions, answers=answers)})
    qs = result.articles[0].questions
    assert qs[0].qtype == build.TYPE_CHOICE
    assert qs[0].answer == "B"  # 紧凑字母串按顺序补齐
    assert qs[1].qtype == build.TYPE_FILL
    assert qs[1].answer == "He helped someone."
    html = read(out / "src" / result.articles[0].html_name)
    assert 'class="fill-input"' in html


def test_explicit_type_and_acceptable_answers(tmp_path):
    questions = (
        "## Q1\n\n题型：单选\n\nWhat does David want to learn?\n\n- A. How to drive\n- B. How to cook\n\n"
        "## Q2\n\n题型：填空\n\nDavid wants to learn how to ______."
    )
    answers = "## Q1\n\n答案：B\n\n解释：文中明确提到 cook。\n\n## Q2\n\n答案：cook\n\n可接受答案：cook, to cook"
    result, out, _, _ = make_site(tmp_path, {"0001.A.md": article_md("A", questions=questions, answers=answers)})
    q1, q2 = result.articles[0].questions
    assert q1.qtype == build.TYPE_CHOICE and q1.answer == "B"
    assert q1.explanation == "文中明确提到 cook。" or q1.explanation.startswith("文中明确提到")
    assert q2.qtype == build.TYPE_FILL
    assert q2.answer == "cook"
    assert q2.acceptable == ["cook", "to cook"]
    assert q2.blank is True
    html = read(out / "src" / result.articles[0].html_name)
    assert "可接受答案：cook，to cook" in html


def test_compact_answer_key_maps_in_order(tmp_path):
    questions = (
        "**Q one?**\n\nA. a\n\nB. b\n\nC. c\n\n"
        "**Q two?**\n\nA. a\n\nB. b\n\nC. c\n\n"
        "**Q three?**\n\nA. a\n\nB. b\n\nC. c"
    )
    result, _, _, _ = make_site(tmp_path, {"0001.A.md": article_md("A", questions=questions, answers="BAC")})
    assert [q.answer for q in result.articles[0].questions] == ["B", "A", "C"]


def test_numbered_answer_list_with_bold_option_and_explanation(tmp_path):
    """``1. **B. To the library.** 解释文字`` —— 编号列表 + 粗体选项 + 解释。"""
    questions = (
        "Question 1：Where does Emma go?\n\nA. To the supermarket.\n\nB. To the library.\n\nC. To the park.\n\n"
        "Question 2：Which floor are the books on?\n\nA. The first floor.\n\nB. The second floor.\n\nC. The third floor.\n\n"
        "Question 3：What do pandas eat?\n\nA. Bamboo.\n\nB. Fish.\n\nC. Rice."
    )
    answers = (
        "1. **B. To the library.** Emma goes to the library.\n\n"
        "2. **B. The second floor.** The woman tells Emma.\n\n"
        "3. **A. Bamboo.** Emma learns that pandas eat bamboo."
    )
    result, out, _, _ = make_site(
        tmp_path, {"0001.A.md": article_md("A", questions=questions, answers=answers)}
    )
    questions_parsed = result.articles[0].questions
    assert [q.qtype for q in questions_parsed] == ["choice", "choice", "choice"]
    assert [q.answer for q in questions_parsed] == ["B", "B", "A"]
    assert [q.explanation for q in questions_parsed] == [
        "Emma goes to the library.",
        "The woman tells Emma.",
        "Emma learns that pandas eat bamboo.",
    ]
    html = read(out / "src" / result.articles[0].html_name)
    assert "Emma goes to the library." in html


def test_numbered_answer_list_with_escaped_dot(tmp_path):
    """``1\\. **B. …** 解释`` —— 序号点被反斜杠转义时同样要能解析。

    编辑器常把 ``1.`` 自动写成 ``1\\.`` 以免被转成有序列表（CommonMark 里 ``\\.`` 就是
    字面句点），所以这是等价的合法写法，不能被判成「缺少答案」。
    """
    questions = (
        "Question 1：Where does Emma go?\n\nA. To the supermarket.\n\nB. To the library.\n\nC. To the park.\n\n"
        "Question 2：Which floor are the books on?\n\nA. The first floor.\n\nB. The second floor.\n\nC. The third floor."
    )
    answers = (
        "1\\. **B. To the library.** Emma goes to the library.\n\n"
        "2\\. **B. The second floor.** The woman tells Emma."
    )
    result, out, _, _ = make_site(
        tmp_path, {"0001.A.md": article_md("A", questions=questions, answers=answers)}
    )
    parsed = result.articles[0].questions
    assert [q.answer for q in parsed] == ["B", "B"]
    assert [q.explanation for q in parsed] == [
        "Emma goes to the library.",
        "The woman tells Emma.",
    ]
    html = read(out / "src" / result.articles[0].html_name)
    assert "1\\." not in html          # 转义反斜杠不能漏到页面上
    assert "Emma goes to the library." in html


def test_numbered_question_with_escaped_dot(tmp_path):
    """题干写成 ``1\\. **…**`` 时也要被识别成第 1 题。"""
    questions = (
        "1\\. **Where does Emma go?**\n\nA. To the supermarket.\n\nB. To the library.\n\nC. To the park.\n\n"
        "2\\. **Which floor are the books on?**\n\nA. The first floor.\n\nB. The second floor.\n\nC. The third floor."
    )
    result, _, _, _ = make_site(
        tmp_path, {"0001.A.md": article_md("A", questions=questions, answers="BA")}
    )
    parsed = result.articles[0].questions
    assert len(parsed) == 2
    assert [q.text for q in parsed] == [
        "Where does Emma go?",
        "Which floor are the books on?",
    ]
    assert [q.answer for q in parsed] == ["B", "A"]


def test_numbered_answer_without_explanation_uses_option_text(tmp_path):
    """粗体后没有解释时，把选项原文当解释，Answers 区不会只剩一个字母。"""
    result, _, _, _ = make_site(tmp_path, {"0001.A.md": article_md("A", answers="1. **B. How to cook**")})
    q = result.articles[0].questions[0]
    assert q.answer == "B"
    assert q.explanation == "B. How to cook"


def test_numbered_fill_answer_is_not_read_as_choice_letter(tmp_path):
    """``cook`` 以 c 开头，但不能被误判成选项 C。"""
    questions = "Question 1: David wants to learn how to ______."
    result, _, _, _ = make_site(
        tmp_path, {"0001.A.md": article_md("A", questions=questions, answers="1. cook")}
    )
    q = result.articles[0].questions[0]
    assert q.qtype == "fill"
    assert q.answer == "cook"
    assert q.acceptable == ["cook"]


def test_numbered_fill_answer_with_bold_wrapper(tmp_path):
    questions = "Question 1: David wants to learn how to ______."
    result, _, _, _ = make_site(
        tmp_path, {"0001.A.md": article_md("A", questions=questions, answers="1. **cook**")}
    )
    q = result.articles[0].questions[0]
    assert q.answer == "cook"
    assert q.explanation == ""


@pytest.mark.parametrize(
    "raw,expected",
    [
        ("B", "B"),
        ("b", "B"),
        ("B. To the library.", "B"),
        ("B) To the library.", "B"),
        ("B、到图书馆", "B"),
        ("**B. To the library.**", "B"),
        ("Cook", None),
        ("cook", None),
        ("He helped someone.", None),
        ("bamboo", None),
        ("", None),
    ],
)
def test_extract_choice_key(raw, expected):
    assert build.extract_choice_key(raw) == expected


def test_blank_marker_is_preserved(tmp_path):
    questions = "Question 1: Lucy is tired, but she is very ______."
    result, _, _, _ = make_site(
        tmp_path,
        {"0001.A.md": article_md("A", questions=questions, answers="Question1: happy")},
    )
    q = result.articles[0].questions[0]
    assert "______" in q.text
    assert q.blank is True


def test_invalid_choice_answer_is_rejected(tmp_path):
    with pytest.raises(build.BuildError, match="不在选项"):
        make_site(tmp_path, {"0001.A.md": article_md("A", answers="D")})


def test_missing_answer_is_rejected(tmp_path):
    with pytest.raises(build.BuildError, match="缺少答案"):
        make_site(tmp_path, {"0001.A.md": article_md("A", answers=None)})


def test_question_without_question_section_is_rejected(tmp_path):
    with pytest.raises(build.BuildError, match="没有解析到任何题目"):
        make_site(tmp_path, {"0001.A.md": article_md("A", questions=None, answers=None)})


def test_unknown_question_type_is_rejected(tmp_path):
    questions = "## Q1\n\n题型：连线\n\nWhat?\n\nA. a\n\nB. b"
    with pytest.raises(build.BuildError, match="无法识别的题型"):
        make_site(tmp_path, {"0001.A.md": article_md("A", questions=questions, answers="## Q1\n\n答案：A")})


def test_quiz_data_matches_answers_section(tmp_path):
    result, out, _, _ = make_site(tmp_path, {"0001.A.md": article_md("A")})
    html = read(out / "src" / result.articles[0].html_name)
    match = re.search(r'id="quiz-data">\s*(\{.*?\})\s*</script>', html, re.S)
    assert match
    quiz = json.loads(match.group(1))
    for q in result.articles[0].questions:
        assert quiz[q.qid]["answer"] == q.answer
        assert quiz[q.qid]["acceptable"] == q.acceptable


def test_answers_are_collapsed_by_default(tmp_path):
    result, out, _, _ = make_site(tmp_path, {"0001.A.md": article_md("A")})
    html = read(out / "src" / result.articles[0].html_name)
    assert '<details class="answers-disclosure">' in html
    assert '<summary>显示全部答案与解释</summary>' in html
    assert 'answers-disclosure" open' not in html


@pytest.mark.parametrize(
    "raw,expected",
    [
        ("cook", "cook"),
        ("  Cook  ", "cook"),
        ("cook.", "cook"),
        ("COOK", "cook"),
        ("cook   it", "cook it"),
        ("   ", ""),
        ("", ""),
        ("cook！", "cook"),
    ],
)
def test_normalize_answer(raw, expected):
    assert build.normalize_answer(raw) == expected


def test_blank_answer_can_never_match(tmp_path):
    """空白输入不能被判定为正确：归一化后为空，且不会命中任何可接受答案。"""
    questions = "Question 1: David wants to learn how to ______."
    answers = "Question1: cook"
    result, _, _, _ = make_site(tmp_path, {"0001.A.md": article_md("A", questions=questions, answers=answers)})
    q = result.articles[0].questions[0]
    accepted = [build.normalize_answer(a) for a in q.acceptable]
    assert build.normalize_answer("   ") == ""
    assert "" not in accepted
    assert build.normalize_answer("  COOK ") in accepted


def test_fill_with_all_blank_acceptable_answers_is_rejected(tmp_path):
    questions = "Question 1: David wants to learn how to ______."
    answers = "Question1: \n\n可接受答案： ,  "
    with pytest.raises(build.BuildError):
        make_site(tmp_path, {"0001.A.md": article_md("A", questions=questions, answers=answers)})


# --------------------------------------------------------------------------
# 11.5 音频与路径
# --------------------------------------------------------------------------


def test_audio_linked_when_file_exists(tmp_path):
    result, out, _, _ = make_site(tmp_path, {"0001.A.md": article_md("A")}, audio=["0001.A.wav"])
    html = read(out / "src" / result.articles[0].html_name)
    assert 'data-src="../sources/0001.A.wav"' in html
    assert "player-unavailable" not in html


def test_missing_audio_warns_but_keeps_everything_else(tmp_path):
    result, out, _, _ = make_site(tmp_path, {"0001.A.md": article_md("A")})
    assert any("缺少音频" in w for w in result.warnings)
    html = read(out / "src" / result.articles[0].html_name)
    assert "player-unavailable" in html
    for section in ("article", "words", "questions", "answers", "continue"):
        assert f'id="{section}"' in html
    assert "hobby" in html and "检查答案" in html


def test_missing_audio_does_not_block_other_articles(tmp_path):
    files = {"0001.A.md": article_md("A"), "0002.B.md": article_md("B")}
    result, out, _, _ = make_site(tmp_path, files, audio=["0002.B.wav"])
    assert (out / "src" / "0001.A.html").is_file()
    assert (out / "src" / "0002.B.html").is_file()
    assert "player-unavailable" in read(out / "src" / "0001.A.html")
    assert "player-unavailable" not in read(out / "src" / "0002.B.html")


def test_css_and_js_paths_are_relative(tmp_path):
    result, out, _, _ = make_site(tmp_path, {"0001.A.md": article_md("A")}, audio=["0001.A.wav"])
    index = read(out / "index.html")
    page = read(out / "src" / result.articles[0].html_name)
    assert 'href="assets/css/style.css"' in index
    assert 'src="assets/js/main.js"' in index
    assert 'href="../assets/css/style.css"' in page
    assert 'src="../assets/js/audio-player.js"' in page


def test_player_sits_above_article_body(tmp_path):
    """播放器必须在 Article 标题之下、正文之上：先按播放，再读文字。"""
    result, out, _, _ = make_site(tmp_path, {"0001.A.md": article_md("A")}, audio=["0001.A.wav"])
    html = read(out / "src" / result.articles[0].html_name)
    article_at = html.index('id="article"')
    player_at = html.index("data-player")
    words_at = html.index('id="words"')
    first_p = html.index("<p>", article_at)
    assert article_at < player_at < words_at
    assert player_at < first_p
    assert html.index("My name is David.") > player_at


def test_player_placeholder_also_above_article_body(tmp_path):
    """缺音频时替换出来的提示同样位于正文之前。"""
    result, out, _, _ = make_site(tmp_path, {"0001.A.md": article_md("A")})
    html = read(out / "src" / result.articles[0].html_name)
    article_at = html.index('id="article"')
    placeholder_at = html.index("player-unavailable")
    assert article_at < placeholder_at < html.index('id="words"')
    assert placeholder_at < html.index("My name is David.")


def test_divider_between_player_and_article_body(tmp_path):
    """播放器与正文之间必须有一条分隔线（有音频 / 缺音频两种情形都要有）。"""
    # 先测「缺音频」再测「有音频」：两次 make_site 共用同一个 sources/ 目录，
    # 已写入的 WAV 不会被清掉，顺序颠倒会让「缺音频」那条断言失真。
    for audio, marker in (([], "player-unavailable"), (["0001.A.wav"], "data-player")):
        result, out, _, _ = make_site(tmp_path, {"0001.A.md": article_md("A")}, audio=audio)
        html = read(out / "src" / result.articles[0].html_name)
        player_at = html.index(marker)
        divider_at = html.index('<hr class="player-divider">')
        assert player_at < divider_at < html.index("My name is David.")


def test_player_has_no_plus_minus_five_second_buttons(tmp_path):
    """±5s 按钮已按要求移除；跳转只靠点击 / 拖动进度条与键盘方向键。"""
    result, out, _, _ = make_site(tmp_path, {"0001.A.md": article_md("A")}, audio=["0001.A.wav"])
    html = read(out / "src" / result.articles[0].html_name)
    assert 'data-action="back"' not in html
    assert 'data-action="forward"' not in html


def test_player_rate_buttons_are_the_three_requested_values(tmp_path):
    """倍速只保留 0.75x / 1x / 1.25x，默认 1x 激活。"""
    result, out, _, _ = make_site(tmp_path, {"0001.A.md": article_md("A")}, audio=["0001.A.wav"])
    html = read(out / "src" / result.articles[0].html_name)
    rates = re.findall(r'data-rate="([0-9.]+)"', html)
    assert rates == ["0.75", "1", "1.25"]
    assert re.search(r'class="rate is-active" data-rate="1"', html)


def test_icons_declared_with_correct_relative_prefix(tmp_path):
    result, out, _, _ = make_site(tmp_path, {"0001.A.md": article_md("A")}, audio=["0001.A.wav"])
    index = read(out / "index.html")
    page = read(out / "src" / result.articles[0].html_name)

    for rel in (build.FAVICON_SVG, build.FAVICON_PNG32, build.FAVICON_PNG180):
        assert f'href="{rel}"' in index, rel
        assert f'href="../{rel}"' in page, rel

    assert 'type="image/svg+xml"' in index
    assert 'rel="apple-touch-icon"' in index
    assert f'<meta name="theme-color" content="{build.THEME_COLOR}">' in index
    # 首页品牌名旁显示站点图标（品牌的一部分，不属于「额外信息」）
    assert 'class="brand-icon"' in index
    assert f'src="{build.FAVICON_SVG}"' in index
    # 图标不应出现在第五章要求的「首页禁止内容」里
    assert "words-table" not in index and "data-player" not in index


def test_icon_assets_exist_and_are_valid():
    """图标是随仓库提交的静态资产，必须真实存在且格式有效。"""
    root = Path(__file__).resolve().parent.parent
    svg = (root / build.FAVICON_SVG).read_bytes()
    assert b"<svg" in svg and b"viewBox" in svg

    for rel, size in ((build.FAVICON_PNG32, 32), (build.FAVICON_PNG180, 180)):
        data = (root / rel).read_bytes()
        assert data[:8] == b"\x89PNG\r\n\x1a\n", rel
        width, height, depth, color_type = struct.unpack(">IIBB", data[16:26])
        assert (width, height) == (size, size), rel
        assert depth == 8 and color_type == 6, rel  # 8 bit / RGBA


def test_no_absolute_root_paths(tmp_path):
    files = {"0001.A.md": article_md("A"), "0101.B.md": article_md("B")}
    result, out, _, _ = make_site(tmp_path, files)
    for path in [out / "index.html"] + [out / "src" / a.html_name for a in result.articles]:
        html = read(path)
        assert not re.search(r'(?:href|src)="/(?!/)', html), path.name


def test_github_pages_subpath_compatibility(tmp_path):
    """模拟 https://<user>.github.io/DailyLingo/ ：所有资源必须靠相对路径解析。

    ``assets/`` 与 ``sources/`` 是随仓库提交的静态资源，构建只往输出根写
    ``index.html`` 与 ``src/*.html``，因此这里按真实仓库布局拼出部署目录。
    """
    import shutil

    root = Path(__file__).resolve().parent.parent
    files = {"0001.A.md": article_md("A")}
    result, out, _, sources = make_site(tmp_path, files, audio=["0001.A.wav"])

    served = tmp_path / "DailyLingo"
    served.mkdir()
    shutil.copy(out / "index.html", served / "index.html")
    shutil.copytree(out / "src", served / "src")
    shutil.copytree(root / "assets", served / "assets")
    shutil.copytree(sources, served / "sources")

    index = read(served / "index.html")
    assert 'href="src/0001.A.html"' in index
    assert (served / "src" / "0001.A.html").is_file()
    page = read(served / "src" / "0001.A.html")
    for rel in (
        "assets/css/style.css",
        "assets/js/main.js",
        "assets/js/audio-player.js",
    ):
        assert (served / rel).is_file(), rel
    assert (served / "sources" / "0001.A.wav").is_file()
    assert 'href="../index.html"' in page
    assert 'data-src="../sources/0001.A.wav"' in page


def test_build_is_reproducible(tmp_path):
    files = {"0001.A.md": article_md("A"), "0101.B.md": article_md("B")}
    content = write_content(tmp_path, files, audio=["0001.A.wav"])
    sources = tmp_path / "sources"
    out1 = tmp_path / "out1"
    out2 = tmp_path / "out2"
    r1 = build.build_site(content, out1, sources)
    r2 = build.build_site(content, out2, sources)
    assert (out1 / "index.html").read_bytes() == (out2 / "index.html").read_bytes()
    for a, b in zip(r1.article_paths, r2.article_paths):
        assert a.read_bytes() == b.read_bytes()
    assert r1.warnings == r2.warnings


def test_sections_appear_in_fixed_order(tmp_path):
    result, out, _, _ = make_site(tmp_path, {"0001.A.md": article_md("A")})
    html = read(out / "src" / result.articles[0].html_name)
    positions = [html.index(f">{name}</h2>") for name in ("Article", "Words", "Questions", "Answers", "Continue")]
    assert positions == sorted(positions)
