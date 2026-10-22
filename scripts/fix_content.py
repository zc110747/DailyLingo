r"""把 ``content/`` 里的文章文件名与 ``## Continue`` 链接整理到规范状态。

为什么需要它：新文章通常是先粘正文、文件名随手给个占位（``0041..md``、``0043.md``），
而文件名同时是 **URL 片段** 和 **音频名**，错了会连带 URL、WAV、相邻导航三处。
手工改名容易漏掉「改相邻文章的 previous / next」，所以收在一个幂等脚本里。

规则（与 ``README`` 的硬约定一致）：

* 文件名 = ``NNNN.<Slug>.md``；``Slug`` 由 ``# 标题`` 生成 —— 去掉撇号 / 引号 / 标点，
  空格换成下划线，只保留 ASCII 字母与数字（``Grandma’s`` → ``Grandmas``）。
* ``## Continue`` 段按**编号相邻**重写为相对路径（跨子目录也正确），
  首篇 previous 与末篇 next 指回仓库根的 ``index.html``。
* 只动文件名和 ``## Continue`` 段，正文一字不改。

用法::

    python scripts/fix_content.py --check    # 只报告，有需修项时退出码 1
    python scripts/fix_content.py --apply    # 真的改名并重写链接
"""

from __future__ import annotations

import argparse
import os
import re
import sys
from dataclasses import dataclass, field
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DEFAULT_CONTENT_DIR = ROOT / "content"

# 撇号、引号、常见标点：直接删掉而不是换成下划线（照 0016 / 0021 / 0039 的先例）
_DROP = "’'\"“”‘’.,:;!?()[]{}<>/\\|*`~@#$%^&=+–—、，。！？（）《》【】·"
_CONTINUE = re.compile(r"^## Continues?\s*$", re.M)
_TITLE = re.compile(r"^#\s+(.+?)\s*$", re.M)
_LINK = re.compile(r"\]\(([^)\s]+)\)")


def slugify(title: str) -> str:
    """「Grandma’s Secret Recipe」→「Grandmas_Secret_Recipe」。"""
    text = title
    for ch in _DROP:
        text = text.replace(ch, "")
    words = re.findall(r"[A-Za-z0-9]+", text)
    return "_".join(words)


@dataclass
class Entry:
    path: Path
    number: int
    title: str
    slug: str

    @property
    def expected_name(self) -> str:
        return f"{self.number:04d}.{self.slug}.md"

    @property
    def name_ok(self) -> bool:
        return self.path.name == self.expected_name


@dataclass
class Report:
    renames: list[tuple[Path, str]] = field(default_factory=list)
    relinks: list[Path] = field(default_factory=list)
    errors: list[str] = field(default_factory=list)

    @property
    def ok(self) -> bool:
        return not (self.renames or self.relinks or self.errors)


def scan(content_dir: Path) -> list[Entry]:
    entries: list[Entry] = []
    for path in sorted(content_dir.rglob("*.md")):
        rel = path.relative_to(content_dir)
        if any(part.startswith(".") for part in rel.parts):
            continue
        match = re.match(r"^(\d+)\.", path.name)
        if not match:
            raise SystemExit(f"文件名不以编号开头：{rel.as_posix()}")
        text = path.read_text(encoding="utf-8")
        title_match = _TITLE.search(text)
        if not title_match:
            raise SystemExit(f"缺少 `# 标题`：{rel.as_posix()}")
        entries.append(
            Entry(
                path=path,
                number=int(match.group(1)),
                title=title_match.group(1),
                slug=slugify(title_match.group(1)),
            )
        )
    entries.sort(key=lambda e: e.number)
    duplicates = {e.number for e in entries if [x.number for x in entries].count(e.number) > 1}
    if duplicates:
        raise SystemExit("重复编号：" + ", ".join(f"{n:04d}" for n in sorted(duplicates)))
    return entries


def continue_block(entry: Entry, previous: Entry | None, following: Entry | None, index: Path) -> str:
    """按**编号升序里的相邻**生成导航（缺号不跳空，与 build.py 完全一致）。"""

    def link(target: Path) -> str:
        rel = os.path.relpath(target, entry.path.parent).replace("\\", "/")
        return rel if rel.startswith("..") else "./" + rel

    lines = [
        "## Continue",
        "",
        f"- [catalogue]({link(index)})",
        f"- [previous chapter]({link(previous.path if previous else index)})",
        f"- [next chapter]({link(following.path if following else index)})",
    ]
    return "\n".join(lines) + "\n"


def _neighbours(position: int, entries: list[Entry]) -> tuple[Entry | None, Entry | None]:
    previous = entries[position - 1] if position > 0 else None
    following = entries[position + 1] if position + 1 < len(entries) else None
    return previous, following


def inspect(content_dir: Path) -> tuple[Report, list[Entry]]:
    report = Report()
    entries = scan(content_dir)
    index = content_dir.parent / "index.html"

    for entry in entries:
        if not entry.name_ok:
            report.renames.append((entry.path, entry.expected_name))

    # 改名后路径会变，链接按「改名后的目录」计算
    for position, entry in enumerate(entries):
        final = entry.path.with_name(entry.expected_name)
        text = entry.path.read_text(encoding="utf-8")
        match = _CONTINUE.search(text)
        if not match:
            report.errors.append(f"{entry.path.name}: 缺少 ## Continue 段")
            continue
        previous, following = _neighbours(position, entries)
        rewritten = Entry(final, entry.number, entry.title, entry.slug)
        expected = continue_block(rewritten, previous, following, index)
        if text[match.start():] != expected:
            report.relinks.append(entry.path)
    return report, entries


def apply(content_dir: Path) -> Report:
    report, _ = inspect(content_dir)
    if report.errors:
        return report

    # 先把所有不合规的文件名改掉（同一目录内不会撞名：编号唯一）
    for path, new_name in report.renames:
        path.rename(path.with_name(new_name))

    entries = scan(content_dir)
    index = content_dir.parent / "index.html"
    for position, entry in enumerate(entries):
        text = entry.path.read_text(encoding="utf-8")
        match = _CONTINUE.search(text)
        if not match:
            continue
        previous, following = _neighbours(position, entries)
        block = continue_block(entry, previous, following, index)
        if text[match.start():] != block:
            entry.path.write_text(text[: match.start()] + block, encoding="utf-8", newline="\n")
    return report


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="整理文章文件名与 Continue 链接")
    parser.add_argument("--content", default=str(DEFAULT_CONTENT_DIR), help="Markdown 文章源目录")
    parser.add_argument("--check", action="store_true", help="只报告，不改文件（默认行为）")
    parser.add_argument("--apply", action="store_true", help="真的改名并重写链接")
    args = parser.parse_args(argv)

    content_dir = Path(args.content).resolve()
    if not content_dir.is_dir():
        print(f"内容目录不存在：{content_dir}", file=sys.stderr)
        return 2

    if args.apply:
        report = apply(content_dir)
        if report.errors:
            for error in report.errors:
                print(f"[错误] {error}", file=sys.stderr)
            return 1
        print(f"已改名 {len(report.renames)} 个，重写链接 {len(report.relinks)} 篇")
        for old, new in report.renames:
            print(f"  改名 {old.name} → {new}")
        return 0

    report, _ = inspect(content_dir)
    for old, new in report.renames:
        print(f"[需改名] {old.relative_to(content_dir).as_posix()} → {new}")
    for path in report.relinks:
        print(f"[需改链接] {path.relative_to(content_dir).as_posix()}")
    for error in report.errors:
        print(f"[错误] {error}", file=sys.stderr)
    if report.ok:
        print("文件名与 Continue 链接都已规范，无需改动")
        return 0
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
