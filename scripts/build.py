#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""DailyLingo 静态网站构建脚本（只依赖 Python 标准库）。

职责
----
1.  扫描 ``content/`` 下的 Markdown 文章源
2.  解析元数据 / 正文 / 单词表 / 题目 / 答案
3.  校验编号、标题、结构、重复编号、文件名与编号一致性
4.  按编号数值升序排列
5.  计算 Chapter 分组（每 100 个编号一个固定区间，只输出含真实文章的分组）
6.  生成首页 ``index.html``（Chapter 折叠目录）
7.  生成 ``src/*.html`` 文章详情页（Article / Words / Questions / Answers / Continue）
8.  自动关联 ``sources/*.wav``
9.  自动生成上一篇 / 下一篇导航
10. 输出构建摘要

本脚本【不】做的事情（与需求一致）
----------------------------------
* 不生成语音、不调用 TTS、不把 WAV 转换成 MP3
* 不生成没有真实文章的 Chapter
* 不生成虚构文章或占位链接
* 不在首页显示摘要 / 难度 / 音频状态
* 不在不同页面重复硬编码标题
* 不因单篇文章缺少音频而阻止其他正常页面构建

用法
----
    python scripts/build.py
    python scripts/build.py --content content --out . --verbose
"""

from __future__ import annotations

import argparse
import hashlib
import html
import json
import re
import sys
import unicodedata
from dataclasses import dataclass, field
from pathlib import Path
from typing import Iterable, Sequence

# --------------------------------------------------------------------------
# 常量
# --------------------------------------------------------------------------

BRAND = "DailyLingo"
CHUNK = 100  # 每个 Chapter 覆盖的编号数量
EN_DASH = "\u2013"  # – 用于 "Chapter 0001–0100"

ROOT = Path(__file__).resolve().parent.parent
DEFAULT_CONTENT_DIR = ROOT / "content"
DEFAULT_OUT_DIR = ROOT
DEFAULT_SOURCES_DIR = ROOT / "sources"

# 站点图标（静态资产，随仓库提交；相对路径随页面深度加前缀）
FAVICON_SVG = "assets/images/favicon.svg"
FAVICON_PNG32 = "assets/images/favicon-32.png"
FAVICON_PNG180 = "assets/images/favicon-180.png"
THEME_COLOR = "#3166a4"  # 与图标底色中值一致

# CSS / JS：URL 上挂内容指纹。GitHub Pages 对这些文件回的是
# ``Cache-Control: max-age=600``，只改文件内容不改文件名的话，手机上最长 10 分钟
# 仍旧拿缓存（曾因此误判「移动端样式修复没生效」）。内容一变 URL 就变 ⇒ 必然重新拉取。
STYLE_CSS = "assets/css/style.css"
MAIN_JS = "assets/js/main.js"
PLAYER_JS = "assets/js/audio-player.js"
PROGRESS_JS = "assets/js/progress.js"  # 仅首页引用：学习进度的本地存储 / 导入导出


def asset_version(rel: str) -> str:
    """静态资源内容指纹（sha256 前 8 位十六进制）。文件缺失时返回 ``"0"``。

    只依赖文件内容，所以构建仍然字节级可复现。
    """
    try:
        data = (ROOT / rel).read_bytes()
    except OSError:
        return "0"
    return hashlib.sha256(data).hexdigest()[:8]


def asset_url(rel: str) -> str:
    """带缓存指纹的相对资源 URL，如 ``assets/css/style.css?v=1a2b3c4d``。"""
    return f"{rel}?v={asset_version(rel)}"

# Markdown 章节名（大小写不敏感）→ 内部键
SECTION_ALIASES = {
    "article": "article",
    "text": "article",
    "文章": "article",
    "正文": "article",
    "words": "words",
    "word": "words",
    "vocabulary": "words",
    "单词": "words",
    "重点单词": "words",
    "questions": "questions",
    "question": "questions",
    "exercises": "questions",
    "题目": "questions",
    "练习": "questions",
    "answers": "answers",
    "answer": "answers",
    "答案": "answers",
    "continues": "continues",
    "continue": "continues",
    "navigation": "continues",
    "catalogue": "continues",
    "catalog": "continues",
}

# 单词表列别名 → 内部键
WORD_COLUMN_ALIASES = {
    "word": "word",
    "单词": "word",
    "pronunciation": "ipa",
    "ipa": "ipa",
    "音标": "ipa",
    "发音": "ipa",
    "pos": "pos",
    "partofspeech": "pos",
    "词性": "pos",
    "meaning": "meaning",
    "中文释义": "meaning",
    "释义": "meaning",
    "中文": "meaning",
    "example": "example",
    "例句": "example",
    "sentence": "example",
}

_ARTICLE_FILE_RE = re.compile(r"^(\d+)\.([^.]+)\.md$")
_HEADING_RE = re.compile(r"^(#{1,6})\s+(.+?)\s*$")
_Q_HEAD_RE = re.compile(r"^#{2,6}\s*Q(\d+)\s*[:：.]?\s*(.*)$", re.I)
_Q_LABEL_RE = re.compile(r"^Question\s+(\d+)\s*[:：.]\s*(.*)$", re.I)
_Q_BOLD_RE = re.compile(r"^\*\*(.+?)\*\*\s*$")
# 序号后的分隔点允许被反斜杠转义：``1. 题干`` 与 ``1\. 题干`` 等价
# （CommonMark 里 ``\.`` 就是字面句点，编辑器常为防自动列表而自动加上）
_Q_NUMBERED_RE = re.compile(r"^(\d+)\\?\s*[.、)]\s+(.+)$")
_OPTION_RE = re.compile(r"^[-*+]?\s*([A-Za-z])\s*[.、)]\s*(.+)$")
_TYPE_RE = re.compile(r"^(?:题型|类型|type)\s*[:：]\s*(.+?)\s*$", re.I)
_BLANK_RE = re.compile(r"_{2,}|…{2,}|\.{4,}")

_ANS_HEAD_RE = re.compile(r"^#{2,6}\s*Q(\d+)\s*$", re.I)
_ANS_LABEL_RE = re.compile(r"^Question\s*(\d+)\s*[:：.]\s*(.*)$", re.I)
_ANS_KEY_RE = re.compile(r"^(?:答案|answer)\s*[:：]\s*(.*)$", re.I)
_ANS_ACCEPT_RE = re.compile(r"^(?:可接受答案|接受的答案|acceptable|accept)\s*[:：]\s*(.*)$", re.I)
_ANS_EXPLAIN_RE = re.compile(r"^(?:解释|说明|explanation|解析)\s*[:：]\s*(.*)$", re.I)
_COMPACT_KEY_RE = re.compile(r"^[A-Da-d]+$")
_ACCEPT_SPLIT_RE = re.compile(r"\s*[,，、;；/|]\s*")
# 编号答案列表：``1. **B. To the library.** 解释文字``
# 分隔点同样允许 ``1\.`` 这种被转义的写法。
_ANS_NUMBERED_RE = re.compile(r"^(\d+)\\?\s*[.、)]\s+(.*)$")
_ANS_BOLD_HEAD_RE = re.compile(r"^\*\*(.+?)\*\*\s*(.*)$")
_ANS_CHOICE_KEY_RE = re.compile(r"^([A-Za-z])\\?\s*[.、)]\s*(.*)$")
_ANS_SINGLE_LETTER_RE = re.compile(r"^([A-Za-z])$")

TYPE_CHOICE = "choice"
TYPE_FILL = "fill"


class BuildError(Exception):
    """构建过程中发现的数据 / 结构错误。"""


# --------------------------------------------------------------------------
# 通用小工具
# --------------------------------------------------------------------------


def strip_markdown(text: str) -> str:
    """剥离常见行内 Markdown 语法，但保留全部可见文字。

    注意：**不**处理 ``_斜体_`` / ``__粗体__`` —— 填空题干里的 ``______``
    是题目内容本身，任何下划线强调规则都会把它吃掉。
    """
    out = text.strip()
    out = re.sub(r"!\[(.*?)\]\(.*?\)", r"\1", out)      # 图片
    out = re.sub(r"\[(.+?)\]\(.*?\)", r"\1", out)       # 链接只留文字
    out = re.sub(r"\*\*(.+?)\*\*", r"\1", out)          # 粗体
    out = re.sub(r"(?<!\*)\*(?!\*)(.+?)(?<!\*)\*(?!\*)", r"\1", out)  # 斜体
    out = re.sub(r"`(.+?)`", r"\1", out)                # 行内代码
    out = re.sub(r"<[^>]+>", "", out)                   # 裸 HTML 标签
    return out.strip()


def normalize_key(text: str) -> str:
    """把列名/章节名归一化，便于别名匹配。"""
    return re.sub(r"[\s_\-*/·]+", "", strip_markdown(text)).lower()


def normalize_answer(text: str) -> str:
    """填空题答案判定用的归一化：去首尾空白、压缩空白、去尾部标点、忽略大小写。

    ``assets/js/main.js`` 中的 ``normalizeAnswer`` 必须与本函数保持一致。
    """
    value = unicodedata.normalize("NFKC", text or "").strip()
    value = re.sub(r"\s+", " ", value)
    value = re.sub(r"[.!?。！？,，;；:：]+$", "", value)
    return value.strip().lower()


def display_number(number: int) -> str:
    """编号显示规则：四位以内补零，超过四位保留完整数字，不截断。"""
    return f"{number:04d}" if number < 10000 else str(number)


def display_title(number: int, title: str) -> str:
    """全站统一的标题生成逻辑。"""
    return f"{display_number(number)}. {title}"


def page_title(number: int, title: str) -> str:
    """浏览器标签标题。"""
    return f"{display_title(number, title)} | {BRAND}"


def chapter_bounds(number: int) -> tuple[int, int]:
    """返回编号所属 Chapter 的 (起始编号, 结束编号)，闭区间。"""
    if number < 1:
        raise BuildError(f"文章编号必须为正整数，收到：{number}")
    start = ((number - 1) // CHUNK) * CHUNK + 1
    return start, start + CHUNK - 1


def chapter_label(start: int, end: int) -> str:
    return f"Chapter {display_number(start)}{EN_DASH}{display_number(end)}"


def esc(text: str) -> str:
    return html.escape(text, quote=True)


def slug_to_title(slug: str) -> str:
    """文件名中的标题片段 → 可读标题。

    ``A_New_Hobby`` → ``A New Hobby``；已含空格则原样保留。
    """
    return slug.replace("_", " ").strip()


# --------------------------------------------------------------------------
# 数据模型
# --------------------------------------------------------------------------


@dataclass
class Word:
    word: str
    ipa: str = ""
    pos: str = ""
    meaning: str = ""
    example: str = ""


@dataclass
class Option:
    key: str
    text: str


@dataclass
class Question:
    qid: str
    index: int
    text: str
    qtype: str
    options: list[Option] = field(default_factory=list)
    blank: bool = False
    answer: str = ""
    acceptable: list[str] = field(default_factory=list)
    explanation: str = ""


@dataclass
class Article:
    number: int
    title: str
    slug: str
    source: Path
    audio_name: str
    paragraphs: list[str] = field(default_factory=list)
    words: list[Word] = field(default_factory=list)
    questions: list[Question] = field(default_factory=list)

    # 运行时填充
    html_name: str = ""
    has_audio: bool = False
    prev: "Article | None" = None
    next: "Article | None" = None

    @property
    def number_text(self) -> str:
        return display_number(self.number)

    @property
    def display_title(self) -> str:
        return display_title(self.number, self.title)

    @property
    def page_title(self) -> str:
        return page_title(self.number, self.title)


@dataclass
class Chapter:
    start: int
    end: int
    articles: list[Article] = field(default_factory=list)

    @property
    def label(self) -> str:
        return chapter_label(self.start, self.end)


@dataclass
class BuildResult:
    articles: list[Article]
    chapters: list[Chapter]
    warnings: list[str]
    index_path: Path
    article_paths: list[Path]


# --------------------------------------------------------------------------
# Markdown 解析
# --------------------------------------------------------------------------


def parse_front_matter(text: str) -> tuple[dict[str, str], str]:
    """解析可选的 YAML front matter（只支持 ``key: value`` 的简单形式）。"""
    if not text.startswith("---"):
        return {}, text
    lines = text.splitlines()
    if not lines or lines[0].strip() != "---":
        return {}, text
    meta: dict[str, str] = {}
    for i in range(1, len(lines)):
        raw = lines[i]
        if raw.strip() == "---":
            return meta, "\n".join(lines[i + 1:])
        if ":" not in raw:
            continue
        key, _, value = raw.partition(":")
        value = value.strip().strip('"').strip("'")
        if key.strip():
            meta[key.strip().lower()] = value
    return {}, text  # 未闭合的 front matter 视为普通正文


def split_sections(body: str) -> tuple[str, dict[str, list[str]]]:
    """把 Markdown 正文拆成 (主标题, {章节键: 行列表})。

    章节标题可以是任意级别的 Markdown 标题（``## Article`` 或 ``# Article``）。
    **不能识别为章节的标题行会原样保留在当前章节内** —— 例如 ``## Questions``
    下面的 ``## Q1`` 属于题目区的一部分，不得把题目区提前截断。
    """
    title = ""
    sections: dict[str, list[str]] = {}
    current: str | None = None
    for raw in body.splitlines():
        heading = _HEADING_RE.match(raw)
        if heading:
            level = len(heading.group(1))
            text = heading.group(2)
            if level == 1 and not title:
                title = strip_markdown(text)
                continue
            key = SECTION_ALIASES.get(normalize_key(text))
            if key:
                current = key
                sections.setdefault(key, [])
                continue
            # 无法识别的标题：保留在当前章节内（可能是题目 / 答案的子标题）
        if current is not None:
            sections[current].append(raw)
    return title, sections


def parse_words(lines: Sequence[str]) -> list[Word]:
    """解析单词表；表头列名按别名映射，兼容 3 列与 5 列两种写法。"""
    rows = [ln for ln in lines if ln.strip().startswith("|")]
    if not rows:
        return []

    def cells(row: str) -> list[str]:
        raw = row.strip()
        raw = raw[1:] if raw.startswith("|") else raw
        raw = raw[:-1] if raw.endswith("|") else raw
        return [c.strip() for c in raw.split("|")]

    header = cells(rows[0])
    columns: list[str | None] = [WORD_COLUMN_ALIASES.get(normalize_key(c)) for c in header]
    if "word" not in [c for c in columns if c]:
        # 表头不可识别时按位置兜底：第 1 列单词、第 2 列音标、最后 1 列释义
        count = len(header)
        fallback: list[str | None] = ["word", "ipa"] + [None] * max(count - 3, 0)
        if count >= 3:
            fallback.append("meaning")
        columns = (fallback + [None] * count)[:count]

    words: list[Word] = []
    for row in rows[1:]:
        values = cells(row)
        if all(re.fullmatch(r":?-{2,}:?", v or "-") for v in values):
            continue  # 分隔行
        record: dict[str, str] = {}
        for idx, value in enumerate(values):
            key = columns[idx] if idx < len(columns) else None
            if key:
                record[key] = strip_markdown(value)
        word = record.get("word", "").strip()
        if not word:
            continue
        words.append(
            Word(
                word=word,
                ipa=record.get("ipa", ""),
                pos=record.get("pos", ""),
                meaning=record.get("meaning", ""),
                example=record.get("example", ""),
            )
        )
    return words


def parse_questions(lines: Sequence[str]) -> list[Question]:
    """解析题目区，兼容 3 种常见写法。"""
    questions: list[Question] = []
    text_parts: list[str] = []
    explicit_type: str | None = None

    def flush() -> None:
        nonlocal text_parts, explicit_type
        if not text_parts and explicit_type is None:
            return
        text = " ".join(p for p in (s.strip() for s in text_parts) if p).strip()
        text = strip_markdown(text)
        if not text:
            text_parts, explicit_type = [], None
            return
        options = pending_options[:]
        qtype = explicit_type or (TYPE_CHOICE if options else TYPE_FILL)
        if qtype == TYPE_FILL:
            options = []
        questions.append(
            Question(
                qid="",
                index=0,
                text=text,
                qtype=qtype,
                options=options,
                blank=bool(_BLANK_RE.search(text)),
            )
        )
        text_parts, explicit_type = [], None
        pending_options.clear()

    pending_options: list[Option] = []

    for raw in lines:
        line = raw.strip()
        if not line:
            continue

        m = _Q_HEAD_RE.match(line)
        if m:
            flush()
            text_parts = [m.group(2)] if m.group(2).strip() else []
            pending_options = []
            continue

        m = _Q_LABEL_RE.match(line)
        if m:
            flush()
            text_parts = [m.group(2)] if m.group(2).strip() else []
            continue

        m = _TYPE_RE.match(line)
        if m:
            explicit_type = _normalize_type(m.group(1))
            continue

        m = _OPTION_RE.match(line)
        if m and text_parts:
            pending_options.append(Option(key=m.group(1).upper(), text=strip_markdown(m.group(2))))
            continue

        m = _Q_NUMBERED_RE.match(line)
        if m:
            flush()
            text_parts = [m.group(2)]
            continue

        m = _Q_BOLD_RE.match(line)
        if m:
            flush()
            text_parts = [m.group(1)]
            continue

        text_parts.append(line)

    flush()

    for i, q in enumerate(questions, start=1):
        q.index = i
        q.qid = f"Q{i}"
    return questions


def _normalize_type(value: str) -> str:
    key = normalize_key(value)
    if key in {"单选", "单项选择", "选择题", "choice", "singlechoice", "mc", "multiplechoice"}:
        return TYPE_CHOICE
    if key in {"填空", "填空题", "fill", "fillblank", "gap", "blank", "cloze"}:
        return TYPE_FILL
    raise BuildError(f"无法识别的题型：{value!r}（支持：单选 / 填空）")


def extract_choice_key(text: str) -> str | None:
    """从 ``B`` / ``B. To the library.`` 里取出选项字母；不是选项字母时返回 None。

    只在「编号答案列表」这条支路上使用，避免影响填空题答案（``cook`` 不该被当成 C）。
    判据必须严格：``cook`` 以 c 开头，但 c 后面不是 ``.``/``)``/``、``，且整串不是单字母，
    因此不会被误判成选项 C。
    """
    cleaned = strip_markdown(text).strip()
    m = _ANS_CHOICE_KEY_RE.match(cleaned) or _ANS_SINGLE_LETTER_RE.match(cleaned)
    return m.group(1).upper() if m else None


def apply_answers(questions: list[Question], lines: Sequence[str]) -> None:
    """把答案区数据绑定到题目上。

    支持四种写法：
      * 紧凑字母串     ``BAC``              → 按顺序赋给各题
      * 单题行         ``Question5: ...``   → 赋给第 5 题
      * 分块           ``## Q1`` + ``答案：B`` / ``可接受答案：…`` / ``解释：…``
      * 编号答案列表   ``1. **B. To the library.** 解释`` → 赋给第 1 题，
                       粗体里的选项字母作为答案，粗体后的文字作为解释；
                       序号点被转义成 ``1\\.`` 的写法同样识别
    """
    entries: dict[int, dict] = {}
    compact: str | None = None
    current: dict | None = None

    for raw in lines:
        line = raw.strip()
        if not line:
            continue

        m = _ANS_HEAD_RE.match(line)
        if m:
            idx = int(m.group(1))
            current = {"index": idx, "answer": None, "acceptable": [], "explanation": None}
            entries[idx] = current
            continue

        m = _ANS_LABEL_RE.match(line)
        if m:
            idx = int(m.group(1))
            text = strip_markdown(m.group(2))
            current = {"index": idx, "answer": text or None, "acceptable": [], "explanation": None}
            entries[idx] = current
            continue

        m = _ANS_NUMBERED_RE.match(line)
        if m:
            idx = int(m.group(1))
            body = m.group(2).strip()
            entry = {"index": idx, "answer": None, "acceptable": [], "explanation": None}
            entries[idx] = entry
            current = entry

            head, tail = body, ""
            bold = _ANS_BOLD_HEAD_RE.match(body)
            if bold:
                head, tail = bold.group(1).strip(), bold.group(2).strip()

            key = extract_choice_key(head)
            detail = strip_markdown(tail)
            if key:
                entry["answer"] = key
                # 粗体后没有解释时，用选项原文当解释，Answers 区不至于只剩一个字母
                entry["explanation"] = detail or strip_markdown(head)
            else:
                entry["answer"] = strip_markdown(head)
                if detail:
                    entry["explanation"] = detail
            continue

        m = _ANS_ACCEPT_RE.match(line)
        if m and current is not None:
            values = [strip_markdown(v) for v in _ACCEPT_SPLIT_RE.split(m.group(1)) if v.strip()]
            current["acceptable"].extend(values)
            continue

        m = _ANS_EXPLAIN_RE.match(line)
        if m and current is not None:
            current["explanation"] = strip_markdown(m.group(1))
            continue

        m = _ANS_KEY_RE.match(line)
        if m:
            value = strip_markdown(m.group(1))
            if current is None:
                current = {"index": None, "answer": None, "acceptable": [], "explanation": None}
            current["answer"] = value
            continue

        if _COMPACT_KEY_RE.match(line):
            if current is not None and current.get("index") is not None:
                current["answer"] = line.upper()
            else:
                compact = line.upper()
            continue

        if current is not None and not current.get("answer"):
            current["answer"] = strip_markdown(line)
            continue

    for q in questions:
        entry = entries.get(q.index)
        if entry:
            if entry.get("answer"):
                q.answer = entry["answer"].strip()
            q.explanation = entry.get("explanation") or ""
            q.acceptable = [v for v in entry.get("acceptable", []) if v]
        elif compact and q.index <= len(compact):
            q.answer = compact[q.index - 1]
        if not q.acceptable and q.answer:
            q.acceptable = [q.answer]


# --------------------------------------------------------------------------
# 单篇文章解析
# --------------------------------------------------------------------------


def parse_article_file(path: Path) -> Article:
    m = _ARTICLE_FILE_RE.match(path.name)
    if not m:
        raise BuildError(
            f"文件名不符合编号规则：{path.name}"
            "（期望 <编号>.<标题>.md，例如 0001.A_New_Hobby.md）"
        )
    number = int(m.group(1))
    if number < 1:
        raise BuildError(f"非法文章编号：{path.name}")

    try:
        text = path.read_text(encoding="utf-8")
    except UnicodeDecodeError as exc:
        raise BuildError(f"{path.name} 不是有效的 UTF-8 文件：{exc}") from exc

    meta, body = parse_front_matter(text)
    title, sections = split_sections(body)

    if "id" in meta and meta["id"].strip():
        meta_id = meta["id"].strip()
        if not meta_id.isdigit() or int(meta_id) != number:
            raise BuildError(
                f"{path.name} 的 front matter 编号 {meta_id!r} 与文件名编号 {m.group(1)!r} 不一致"
            )
    if meta.get("title", "").strip():
        title = strip_markdown(meta["title"])
    if not title:
        raise BuildError(f"{path.name} 缺少标题（需要一级标题 `# Title` 或 front matter 的 title）")

    slug = m.group(2)
    audio_name = meta.get("audio", "").strip() or f"{m.group(1)}.{slug}.wav"

    paragraphs: list[str] = []
    if "article" in sections:
        for block in re.split(r"\n\s*\n", "\n".join(sections["article"])):
            block = block.strip()
            if block and not block.startswith("```"):
                paragraphs.append(strip_markdown(block))
    if not paragraphs:
        raise BuildError(f"{path.name} 缺少 `## Article` 正文内容")

    article = Article(
        number=number,
        title=title,
        slug=slug,
        source=path,
        audio_name=audio_name,
        paragraphs=paragraphs,
        words=parse_words(sections.get("words", [])),
        questions=parse_questions(sections.get("questions", [])),
    )
    apply_answers(article.questions, sections.get("answers", []))
    article.html_name = f"{m.group(1)}.{slug}.html"
    return article


def validate_article(article: Article) -> list[str]:
    """单篇文章的数据校验，返回错误信息列表。"""
    errors: list[str] = []
    if not article.questions:
        errors.append(f"{article.source.name}: 没有解析到任何题目")
    for q in article.questions:
        if q.qtype == TYPE_CHOICE:
            if not q.options:
                errors.append(f"{article.source.name}: {q.qid} 判定为单选但没有选项")
                continue
            keys = {o.key for o in q.options}
            if not q.answer:
                errors.append(f"{article.source.name}: {q.qid} 缺少答案")
            elif q.answer.upper() not in keys:
                errors.append(
                    f"{article.source.name}: {q.qid} 答案 {q.answer!r} 不在选项 "
                    f"{'/'.join(sorted(keys))} 中"
                )
        else:
            if not q.answer:
                errors.append(f"{article.source.name}: {q.qid} 判定为填空但没有答案")
            elif not any(normalize_answer(a) for a in q.acceptable):
                errors.append(f"{article.source.name}: {q.qid} 的可接受答案全部为空白")
    return errors


# --------------------------------------------------------------------------
# Chapter 分组
# --------------------------------------------------------------------------


def group_chapters(articles: Iterable[Article]) -> list[Chapter]:
    """按编号的数值区间分组，只输出包含真实文章的分组，组内按编号升序。"""
    buckets: dict[tuple[int, int], list[Article]] = {}
    for article in articles:
        buckets.setdefault(chapter_bounds(article.number), []).append(article)
    chapters = [
        Chapter(start=start, end=end, articles=sorted(items, key=lambda a: a.number))
        for (start, end), items in buckets.items()
    ]
    chapters.sort(key=lambda c: c.start)
    return chapters


# --------------------------------------------------------------------------
# HTML 渲染
# --------------------------------------------------------------------------


def _render_icons(prefix: str) -> str:
    """站点图标声明。``prefix`` 为到仓库根目录的相对前缀（首页 ""，文章页 "../"）。"""
    return "\n".join(
        [
            f'  <link rel="icon" type="image/svg+xml" href="{prefix}{FAVICON_SVG}">',
            f'  <link rel="icon" type="image/png" sizes="32x32" href="{prefix}{FAVICON_PNG32}">',
            f'  <link rel="apple-touch-icon" sizes="180x180" href="{prefix}{FAVICON_PNG180}">',
            f'  <meta name="theme-color" content="{THEME_COLOR}">',
        ]
    )


# 完成状态图标对：未完成 = 灰色空心圆，完成 = 绿色勾。两个 SVG 始终都在 DOM 里，
# 由 CSS 按 `[aria-pressed]` 切换显隐 —— JS 只改状态属性，不重建节点，也不碰图标。
_TOGGLE_ICONS = (
    '<svg class="toggle-icon toggle-icon-todo" viewBox="0 0 24 24" aria-hidden="true" focusable="false">'
    '<circle cx="12" cy="12" r="9" fill="none" stroke="currentColor" stroke-width="2"/>'
    "</svg>"
    '<svg class="toggle-icon toggle-icon-done" viewBox="0 0 24 24" aria-hidden="true" focusable="false">'
    '<circle cx="12" cy="12" r="9" fill="none" stroke="currentColor" stroke-width="2"/>'
    '<path d="M7.6 12.4l3.1 3.1 5.9-6.4" fill="none" stroke="currentColor" stroke-width="2.2" '
    'stroke-linecap="round" stroke-linejoin="round"/>'
    "</svg>"
)

# 设置入口（首页左上角）
_SETTINGS_ICON = (
    '<svg class="settings-icon" viewBox="0 0 24 24" aria-hidden="true" focusable="false">'
    '<circle cx="12" cy="12" r="3.2" fill="none" stroke="currentColor" stroke-width="2"/>'
    '<path d="M12 3.4v2.4M12 18.2v2.4M3.4 12h2.4M18.2 12h2.4'
    'M6.1 6.1l1.7 1.7M16.2 16.2l1.7 1.7M17.9 6.1l-1.7 1.7M7.8 16.2l-1.7 1.7" '
    'fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round"/>'
    "</svg>"
)

_CLOSE_ICON = (
    '<svg class="close-icon" viewBox="0 0 24 24" aria-hidden="true" focusable="false">'
    '<path d="M6.5 6.5l11 11M17.5 6.5l-11 11" fill="none" stroke="currentColor" '
    'stroke-width="2" stroke-linecap="round"/>'
    "</svg>"
)


def render_index(chapters: Sequence[Chapter]) -> str:
    total = sum(len(chapter.articles) for chapter in chapters)
    parts: list[str] = []
    for i, chapter in enumerate(chapters):
        opened = " open" if i == 0 else ""
        chapter_total = len(chapter.articles)
        items = "\n".join(
            f'          <li class="article-item" data-article-id="{a.number_text}">\n'
            f'            <a class="article-link" href="src/{esc(a.html_name)}">'
            f"{esc(a.display_title)}</a>\n"
            f'            <button class="article-toggle" type="button" data-action="toggle-complete"'
            f' data-article-id="{a.number_text}" aria-pressed="false"'
            f' aria-label="标记「{esc(a.display_title)}」为已完成">{_TOGGLE_ICONS}</button>\n'
            f"          </li>"
            for a in chapter.articles
        )
        parts.append(
            f'      <details class="chapter"{opened}>\n'
            f'        <summary class="chapter-summary">\n'
            f'          <span class="chapter-arrow" aria-hidden="true"></span>\n'
            f'          <span class="chapter-label">{esc(chapter.label)}</span>\n'
            f'          <span class="chapter-status" data-chapter-status'
            f' data-chapter-total="{chapter_total}">\n'
            f'            <span class="chapter-count" data-chapter-count>0/{chapter_total}</span>\n'
            f'            <span class="chapter-mark" aria-hidden="true">{_TOGGLE_ICONS}</span>\n'
            f'            <span class="visually-hidden" data-chapter-state>未完成</span>\n'
            f"          </span>\n"
            f"        </summary>\n"
            f'        <ul class="article-list">\n{items}\n        </ul>\n'
            f"      </details>"
        )
    chapters_html = "\n".join(parts)
    return f"""<!DOCTYPE html>
<html lang="zh-CN">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>{esc(BRAND)}</title>
  <meta name="description" content="{esc(BRAND)} 每日英语学习：英文阅读、音频朗读、重点单词与阅读理解练习。">
{_render_icons("")}
  <link rel="stylesheet" href="{asset_url(STYLE_CSS)}">
</head>
<body class="page page-index">
  <main class="container">
    <header class="site-header">
      <div class="site-tools">
        <button class="settings-btn" type="button" data-action="open-settings"
                aria-haspopup="dialog" aria-controls="settings-dialog" aria-expanded="false"
                aria-label="设置：导入或导出学习进度">{_SETTINGS_ICON}</button>
      </div>
      <h1 class="brand">
        <img class="brand-icon" src="assets/images/favicon.svg" alt="" width="32" height="32" aria-hidden="true">
        <span class="brand-text">{esc(BRAND)}</span>
      </h1>
    </header>
    <section class="progress-card" aria-labelledby="progress-title">
      <div class="progress-head">
        <h2 class="progress-title" id="progress-title">学习进度</h2>
        <p class="progress-numbers" aria-live="polite"><strong data-progress-done>0</strong> / <span data-progress-total>{total}</span> 篇 · <span data-progress-percent>0%</span></p>
      </div>
      <div class="progress-track" role="progressbar" data-progress-bar
           aria-labelledby="progress-title" aria-valuemin="0" aria-valuemax="{total}"
           aria-valuenow="0" aria-valuetext="共 {total} 篇，已完成 0 篇">
        <span class="progress-fill" data-progress-fill></span>
      </div>
      <p class="progress-notice" data-progress-notice role="status" hidden></p>
    </section>
    <nav class="catalogue" aria-label="文章目录">
{chapters_html}
    </nav>
  </main>
  <dialog class="settings-dialog" id="settings-dialog" aria-labelledby="settings-title">
    <div class="settings-panel">
      <header class="settings-head">
        <h2 class="settings-title" id="settings-title">设置</h2>
        <button class="settings-close" type="button" data-action="close-settings" aria-label="关闭设置">{_CLOSE_ICON}</button>
      </header>
      <section class="settings-section" aria-labelledby="settings-progress-title">
        <h3 class="settings-subtitle" id="settings-progress-title">学习进度</h3>
        <p class="settings-desc">进度只保存在当前浏览器（localStorage），不上传、不跨设备同步。换设备或换浏览器时，用下面的导出 / 导入手动迁移。</p>
        <div class="settings-actions">
          <button class="btn" type="button" data-action="export-progress">导出学习进度</button>
          <button class="btn" type="button" data-action="pick-import">导入学习进度</button>
          <input class="visually-hidden" type="file" accept="application/json,.json" data-import-input tabindex="-1">
        </div>
        <p class="settings-message" data-settings-message role="status"></p>
      </section>
      <section class="import-preview" data-import-preview aria-labelledby="import-title" hidden>
        <h3 class="settings-subtitle" id="import-title">导入预览</h3>
        <dl class="import-stats">
          <div class="import-stat"><dt>文件中的有效记录</dt><dd data-import-file-count>0</dd></div>
          <div class="import-stat"><dt>当前已完成</dt><dd data-import-current-count>0</dd></div>
          <div class="import-stat"><dt>合并导入后</dt><dd data-import-merged-count>0</dd></div>
          <div class="import-stat"><dt>覆盖导入后</dt><dd data-import-overwrite-count>0</dd></div>
        </dl>
        <p class="settings-message" data-import-message role="status"></p>
        <fieldset class="import-modes">
          <legend>导入方式</legend>
          <label class="import-mode"><input type="radio" name="import-mode" value="merge" checked> 合并：保留现有记录，取两者并集</label>
          <label class="import-mode"><input type="radio" name="import-mode" value="overwrite"> 覆盖：以文件为准，替换现有记录</label>
        </fieldset>
        <div class="settings-actions">
          <button class="btn btn-primary" type="button" data-action="apply-import">应用导入</button>
          <button class="btn btn-ghost" type="button" data-action="cancel-import">取消</button>
        </div>
      </section>
      <section class="import-confirm" data-import-confirm aria-labelledby="import-confirm-title" hidden>
        <h3 class="settings-subtitle" id="import-confirm-title">确认覆盖</h3>
        <p class="settings-desc">覆盖会取消当前已完成、但文件中未标记为完成的文章。此操作不可撤销，确定继续？</p>
        <div class="settings-actions">
          <button class="btn btn-primary" type="button" data-action="confirm-overwrite">确认覆盖</button>
          <button class="btn btn-ghost" type="button" data-action="cancel-overwrite">返回</button>
        </div>
      </section>
    </div>
  </dialog>
  <script src="{asset_url(MAIN_JS)}" defer></script>
  <script src="{asset_url(PROGRESS_JS)}" defer></script>
</body>
</html>
"""


def _render_words(article: Article) -> str:
    if not article.words:
        return '        <p class="empty-note">这篇文章暂时没有重点单词。</p>'
    has_pos = any(w.pos for w in article.words)
    has_example = any(w.example for w in article.words)
    head = ["单词", "音标"]
    if has_pos:
        head.append("词性")
    head.append("中文释义")
    if has_example:
        head.append("例句")
    head_html = "".join(f"<th scope=\"col\">{esc(h)}</th>" for h in head)
    rows: list[str] = []
    for w in article.words:
        cells = [f'<td class="word-cell">{esc(w.word)}</td>', f'<td class="ipa-cell">{esc(w.ipa)}</td>']
        if has_pos:
            cells.append(f'<td class="pos-cell">{esc(w.pos)}</td>')
        cells.append(f'<td class="meaning-cell">{esc(w.meaning)}</td>')
        if has_example:
            cells.append(f'<td class="example-cell">{esc(w.example)}</td>')
        rows.append("            <tr>" + "".join(cells) + "</tr>")
    rows_html = "\n".join(rows)
    return (
        '        <div class="table-wrap">\n'
        '          <table class="words-table">\n'
        f"            <thead><tr>{head_html}</tr></thead>\n"
        f"            <tbody>\n{rows_html}\n            </tbody>\n"
        "          </table>\n"
        "        </div>"
    )


def _render_questions(article: Article) -> tuple[str, dict]:
    if not article.questions:
        return '        <p class="empty-note">这篇文章暂时没有练习题。</p>', {}

    quiz_data: dict[str, dict] = {}
    items: list[str] = []
    for q in article.questions:
        name = f"{article.number_text}-{q.qid}"
        if q.qtype == TYPE_CHOICE:
            options_html = "\n".join(
                f'              <label class="option">'
                f'<input type="radio" name="{esc(name)}" value="{esc(o.key)}">'
                f'<span class="option-key">{esc(o.key)}.</span>'
                f'<span class="option-text">{esc(o.text)}</span></label>'
                for o in q.options
            )
            body = f'            <div class="options" role="group">\n{options_html}\n            </div>'
            hint = "单项选择题"
        else:
            body = (
                '            <div class="fill-row">'
                f'<label class="fill-label" for="{esc(name)}">你的答案</label>'
                f'<input class="fill-input" id="{esc(name)}" type="text" '
                'autocomplete="off" autocapitalize="off" spellcheck="false" '
                'placeholder="请输入英文答案">'
                "</div>"
            )
            hint = "填空题"
        items.append(
            f'        <li class="question" data-qid="{esc(q.qid)}" data-type="{q.qtype}">\n'
            f'          <p class="question-head"><span class="question-id">{esc(q.qid)}</span>'
            f'<span class="question-text">{esc(q.text)}</span>'
            f'<span class="question-type">{esc(hint)}</span></p>\n'
            f"{body}\n"
            '          <div class="question-actions">\n'
            f'            <button type="button" class="btn btn-primary" data-action="check" '
            f'aria-controls="{esc(name)}-feedback">检查答案</button>\n'
            f'            <button type="button" class="btn btn-ghost" data-action="reset">重做</button>\n'
            "          </div>\n"
            f'          <p class="feedback" id="{esc(name)}-feedback" role="status" aria-live="polite"></p>\n'
            "        </li>"
        )
        quiz_data[q.qid] = {
            "type": q.qtype,
            "answer": q.answer,
            "acceptable": q.acceptable,
            "explanation": q.explanation,
        }

    html_block = (
        '        <ol class="question-list">\n' + "\n".join(items) + "\n        </ol>"
    )
    return html_block, quiz_data


def _render_answers(article: Article) -> str:
    if not article.questions:
        return '        <p class="empty-note">这篇文章暂时没有答案。</p>'

    def answer_text(q: Question) -> str:
        if q.qtype == TYPE_CHOICE:
            key = q.answer.upper()
            for o in q.options:
                if o.key == key:
                    return f"{key}. {o.text}"
        return q.answer

    items = "\n".join(
        "          <li>"
        f'<span class="answer-id">{esc(q.qid)}</span>'
        f'<span class="answer-value">{esc(answer_text(q))}</span>'
        + (
            f'<span class="answer-accept">可接受答案：{esc("，".join(q.acceptable))}</span>'
            if q.qtype == TYPE_FILL and len(q.acceptable) > 1
            else ""
        )
        + (
            f'<span class="answer-explanation">{esc(q.explanation)}</span>'
            if q.explanation
            else ""
        )
        + "</li>"
        for q in article.questions
    )
    return (
        '        <details class="answers-disclosure">\n'
        '          <summary>显示全部答案与解释</summary>\n'
        f'          <ol class="answer-list">\n{items}\n          </ol>\n'
        "        </details>"
    )


def _render_player(article: Article) -> str:
    if not article.has_audio:
        return (
            '        <div class="player player-unavailable">\n'
            f'          <p class="player-status" role="status">音频文件暂缺：'
            f"<code>sources/{esc(article.audio_name)}</code> 尚未生成，"
            "可使用 009.ai_voice 的 <code>eaudio.cmd</code> 生成后重新构建。</p>\n"
            "        </div>"
        )
    return f"""        <div class="player" data-player data-src="../sources/{esc(article.audio_name)}" data-title="{esc(article.display_title)}">
          <div class="player-main">
            <button type="button" class="player-toggle" data-action="toggle" aria-label="播放">
              <span class="player-toggle-text">播放</span>
            </button>
            <div class="player-body">
              <div class="player-track" data-action="seek" role="slider" tabindex="0"
                   aria-label="播放进度" aria-valuemin="0" aria-valuemax="0" aria-valuenow="0"
                   aria-valuetext="0:00">
                <div class="player-buffered" data-role="buffered"></div>
                <div class="player-progress" data-role="progress"></div>
                <div class="player-handle" data-role="handle"></div>
              </div>
              <div class="player-meta">
                <span class="player-time"><span data-role="current">0:00</span> / <span data-role="duration">--:--</span></span>
                <span class="player-state" data-role="state" role="status" aria-live="polite">正在加载音频…</span>
              </div>
            </div>
          </div>
          <div class="player-controls">
            <label class="player-volume">
              <span>音量</span>
              <input type="range" min="0" max="1" step="0.05" value="1" data-action="volume" aria-label="音量">
            </label>
            <div class="player-rates" role="group" aria-label="播放速度">
              <button type="button" class="rate" data-rate="0.75">0.75&times;</button>
              <button type="button" class="rate is-active" data-rate="1">1&times;</button>
              <button type="button" class="rate" data-rate="1.25">1.25&times;</button>
            </div>
          </div>
        </div>"""


def _render_continue(article: Article) -> str:
    def link(target: Article | None, label: str) -> str:
        if target is None:
            return f'          <span class="nav-disabled">{esc(label)}：无</span>'
        return (
            f'          <a class="nav-link" href="{esc(target.html_name)}">'
            f"{esc(label)}：{esc(target.display_title)}</a>"
        )

    return (
        '        <div class="continue-nav">\n'
        f"{link(article.prev, '上一篇')}\n"
        f"{link(article.next, '下一篇')}\n"
        '          <a class="nav-link nav-home" href="../index.html">返回目录</a>\n'
        "        </div>"
    )


def render_article_page(article: Article) -> str:
    words_html = _render_words(article)
    questions_html, quiz_data = _render_questions(article)
    answers_html = _render_answers(article)
    player_html = _render_player(article)
    continue_html = _render_continue(article)
    quiz_json = json.dumps(quiz_data, ensure_ascii=False, sort_keys=True, indent=2)
    paragraph_html = "\n".join(
        f"          <p>{esc(p)}</p>" for p in article.paragraphs
    )
    return f"""<!DOCTYPE html>
<html lang="zh-CN">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>{esc(article.page_title)}</title>
{_render_icons("../")}
  <link rel="stylesheet" href="../{asset_url(STYLE_CSS)}">
</head>
<body class="page page-article">
  <main class="container">
    <header class="article-header">
      <p class="article-number-large">{esc(article.number_text)}</p>
      <h1 class="article-title-main">{esc(article.title)}</h1>
    </header>

    <section class="section section-article" id="article">
      <h2 class="section-title">Article</h2>
{player_html}
        <hr class="player-divider">
{paragraph_html}
    </section>

    <section class="section section-words" id="words">
      <h2 class="section-title">Words</h2>
{words_html}
    </section>

    <section class="section section-questions" id="questions">
      <h2 class="section-title">Questions</h2>
{questions_html}
    </section>

    <section class="section section-answers" id="answers">
      <h2 class="section-title">Answers</h2>
{answers_html}
    </section>

    <section class="section section-continue" id="continue">
      <h2 class="section-title">Continue</h2>
{continue_html}
    </section>
  </main>

  <script type="application/json" id="quiz-data">
{quiz_json}
  </script>
  <script src="../{asset_url(PLAYER_JS)}" defer></script>
  <script src="../{asset_url(MAIN_JS)}" defer></script>
</body>
</html>
"""


# --------------------------------------------------------------------------
# 构建主流程
# --------------------------------------------------------------------------


def load_articles(content_dir: Path) -> tuple[list[Article], list[str]]:
    warnings: list[str] = []
    if not content_dir.is_dir():
        raise BuildError(f"内容目录不存在：{content_dir}")

    paths = sorted(p for p in content_dir.glob("*.md") if not p.name.startswith("."))
    articles = [parse_article_file(p) for p in paths]

    errors: list[str] = []
    seen: dict[int, Path] = {}
    for article in articles:
        if article.number in seen:
            errors.append(
                f"重复编号 {article.number_text}：{seen[article.number].name} 与 {article.source.name}"
            )
        else:
            seen[article.number] = article.source
        errors.extend(validate_article(article))
    if errors:
        raise BuildError("文章数据校验失败：\n  - " + "\n  - ".join(errors))
    if not articles:
        warnings.append(f"{content_dir} 下没有找到任何文章（*.md）")

    articles.sort(key=lambda a: a.number)

    for i, article in enumerate(articles):
        # 上一篇 / 下一篇按编号数值升序计算，与首页 Chapter 分组完全独立
        article.prev = articles[i - 1] if i > 0 else None
        article.next = articles[i + 1] if i + 1 < len(articles) else None

    return articles, warnings


def build_site(
    content_dir: Path | str = DEFAULT_CONTENT_DIR,
    out_dir: Path | str = DEFAULT_OUT_DIR,
    sources_dir: Path | str = DEFAULT_SOURCES_DIR,
    verbose: bool = False,
) -> BuildResult:
    content_dir = Path(content_dir)
    out_dir = Path(out_dir)
    sources_dir = Path(sources_dir)

    articles, warnings = load_articles(content_dir)
    chapters = group_chapters(articles)

    src_dir = out_dir / "src"
    src_dir.mkdir(parents=True, exist_ok=True)

    for article in articles:
        audio_path = sources_dir / article.audio_name
        article.has_audio = audio_path.is_file()
        if not article.has_audio:
            warnings.append(
                f"{article.source.name}: 缺少音频 sources/{article.audio_name}"
                "（页面其余部分仍会正常生成）"
            )

    index_path = out_dir / "index.html"
    index_path.write_text(render_index(chapters), encoding="utf-8", newline="\n")

    article_paths: list[Path] = []
    for article in articles:
        target = src_dir / article.html_name
        target.write_text(render_article_page(article), encoding="utf-8", newline="\n")
        article_paths.append(target)

    if verbose:
        for article in articles:
            print(
                f"  文章 {article.number_text}  {article.title}"
                f"  |  {len(article.words)} 词  {len(article.questions)} 题"
                f"  |  音频 {'有' if article.has_audio else '缺失'}"
            )

    return BuildResult(
        articles=articles,
        chapters=chapters,
        warnings=warnings,
        index_path=index_path,
        article_paths=article_paths,
    )


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="构建 DailyLingo 静态网站")
    parser.add_argument("--content", default=str(DEFAULT_CONTENT_DIR), help="Markdown 文章源目录")
    parser.add_argument("--out", default=str(DEFAULT_OUT_DIR), help="站点输出根目录")
    parser.add_argument("--sources", default=str(DEFAULT_SOURCES_DIR), help="WAV 音频目录")
    parser.add_argument("--verbose", "-v", action="store_true", help="逐篇打印解析结果")
    args = parser.parse_args(argv)

    try:
        result = build_site(args.content, args.out, args.sources, verbose=args.verbose)
    except BuildError as exc:
        print(f"[ERROR] 构建失败：{exc}", file=sys.stderr)
        return 1

    print(f"{BRAND} 构建完成")
    print(f"  文章总数：{len(result.articles)}")
    print(f"  Chapter 分组：{len(result.chapters)}")
    for chapter in result.chapters:
        state = "展开" if chapter is result.chapters[0] else "折叠"
        print(f"    {chapter.label}（默认{state}）：{len(chapter.articles)} 篇")
        if args.verbose:
            for a in chapter.articles:
                print(f"      - {a.display_title}")
    print(f"  首页：{result.index_path}")
    print(f"  文章页：{len(result.article_paths)} 个，位于 {Path(args.out) / 'src'}")
    if result.warnings:
        print(f"  警告 {len(result.warnings)} 条：")
        for w in result.warnings:
            print(f"    [WARN] {w}")
    else:
        print("  警告：0 条")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
