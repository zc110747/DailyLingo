"""Markdown 源文件自身的链接自洽性。

``## Continue`` 段构建时会被忽略（页面导航按编号重新生成），但源文件仍必须自洽 ——
改编号、改文件名、把文章挪进 Chapter 子目录，都会让这里悄悄断掉，而这种断裂
在构建输出里完全看不出来。所以单独守一层：

* 每个相对链接都要能在磁盘上解析到真实文件；
* previous / next 必须等于**编号相邻**的上一篇 / 下一篇（跨子目录也算）；
* 首篇的 previous 与末篇的 next 都指回首页。
"""

from __future__ import annotations

import re
from pathlib import Path

import pytest

import build

ROOT = Path(__file__).resolve().parent.parent
CONTENT = ROOT / "content"

LINK = re.compile(r"\]\(([^)\s]+)\)")
CONTINUE = re.compile(r"^## Continues?\s*$", re.M)


def _articles() -> list[tuple[Path, int]]:
    """[(md 路径, 编号)]，按编号升序。"""
    items = []
    for path in build.iter_content_files(CONTENT):
        items.append((path, int(path.name[:4])))
    items.sort(key=lambda item: item[1])
    return items


ARTICLES = _articles()
IDS = [p.name for p, _ in ARTICLES]


def _continue_links(path: Path) -> list[str]:
    text = path.read_text(encoding="utf-8")
    match = CONTINUE.search(text)
    assert match, f"{path.name} 缺少 ## Continue 段"
    return LINK.findall(text[match.end():])


def test_content_has_articles():
    assert len(ARTICLES) == 40


@pytest.mark.parametrize("path,number", ARTICLES, ids=IDS)
def test_continue_links_resolve(path: Path, number: int):
    links = _continue_links(path)
    assert len(links) == 3, f"{path.name}: 期望 catalogue / previous / next 三条链接"
    for href in links:
        if href.startswith(("http://", "https://", "#")):
            continue
        target = (path.parent / href).resolve()
        assert target.exists(), f"{path.name}: {href} 解析不到 {target}"


@pytest.mark.parametrize("path,number", ARTICLES, ids=IDS)
def test_continue_order_matches_numbers(path: Path, number: int):
    numbers = [n for _, n in ARTICLES]
    position = numbers.index(number)
    previous = ARTICLES[position - 1][0] if position > 0 else ROOT / "index.html"
    following = ARTICLES[position + 1][0] if position + 1 < len(ARTICLES) else ROOT / "index.html"

    catalogue, prev_link, next_link = _continue_links(path)
    assert (path.parent / catalogue).resolve() == (ROOT / "index.html").resolve()
    assert (path.parent / prev_link).resolve() == previous.resolve()
    assert (path.parent / next_link).resolve() == following.resolve()


def test_navigation_crosses_chapter_folders():
    """0025 在 0001-0025/、0026 在 0026-0050/，这一对是最容易写错的地方。"""
    by_number = {n: p for p, n in ARTICLES}
    assert by_number[25].parent != by_number[26].parent
    _, _, next_of_25 = _continue_links(by_number[25])
    _, prev_of_26, _ = _continue_links(by_number[26])
    assert (by_number[25].parent / next_of_25).resolve() == by_number[26].resolve()
    assert (by_number[26].parent / prev_of_26).resolve() == by_number[25].resolve()
