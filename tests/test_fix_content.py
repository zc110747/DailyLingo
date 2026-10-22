"""``scripts/fix_content.py``：文件名规范化 + Continue 链接重写。

这个脚本的价值全在「幂等」和「跨目录也对」这两点上，所以测试重点就是：
跑之前 --check 必须报、跑之后 --check 必须静默、再跑一次不能有变化。
"""

from __future__ import annotations

import fix_content

import pytest

ARTICLE = """# {title}

## Article

A short story. It has two sentences.

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

## Continue

- [catalogue](./catalogue.md)
- [previous chapter](./nope.md)
- [next chapter](./nope.md)
"""


def make_content(tmp_path, files: dict[str, str]):
    content = tmp_path / "content"
    for rel, title in files.items():
        path = content / rel
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(ARTICLE.format(title=title), encoding="utf-8", newline="\n")
    content.mkdir(parents=True, exist_ok=True)
    (tmp_path / "index.html").write_text("<html></html>", encoding="utf-8")
    return content


# --------------------------------------------------------------------------
# 文件名规则
# --------------------------------------------------------------------------


@pytest.mark.parametrize(
    "title,slug",
    [
        ("The Missing Recipe", "The_Missing_Recipe"),
        ("Grandma’s Secret Recipe", "Grandmas_Secret_Recipe"),
        ("The Town's New Recycling Center", "The_Towns_New_Recycling_Center"),
        ("The Little Bee’s Busy Day", "The_Little_Bees_Busy_Day"),
        ("A Day at the Post Office", "A_Day_at_the_Post_Office"),
        ("Ready… Set… Go!", "Ready_Set_Go"),
        ("Tea & Coffee", "Tea_Coffee"),
        ("   Spaced   Out   ", "Spaced_Out"),
    ],
)
def test_slugify(title, slug):
    assert fix_content.slugify(title) == slug


def test_existing_articles_are_already_canonical():
    """仓库里 45 篇的文件名必须已经是 slugify(标题) —— 这条同时验证规则没写歪。"""
    entries = fix_content.scan(fix_content.DEFAULT_CONTENT_DIR)
    bad = [(e.path.name, e.expected_name) for e in entries if not e.name_ok]
    assert bad == []


# --------------------------------------------------------------------------
# 改名 + 重写链接
# --------------------------------------------------------------------------


def test_placeholders_are_renamed(tmp_path):
    content = make_content(
        tmp_path,
        {"0041..md": "First Story", "0042.md": "Second Story"},
    )
    report = fix_content.apply(content)
    assert [new for _, new in report.renames] == [
        "0041.First_Story.md",
        "0042.Second_Story.md",
    ]
    assert sorted(p.name for p in content.iterdir()) == [
        "0041.First_Story.md",
        "0042.Second_Story.md",
    ]


def test_links_follow_numbers_across_folders(tmp_path):
    content = make_content(
        tmp_path,
        {"0001-0025/0001..md": "One", "0026-0050/0026..md": "Twenty Six"},
    )
    fix_content.apply(content)
    first = (content / "0001-0025" / "0001.One.md").read_text(encoding="utf-8")
    second = (content / "0026-0050" / "0026.Twenty_Six.md").read_text(encoding="utf-8")
    assert "- [catalogue](../../index.html)" in first
    assert "- [next chapter](../0026-0050/0026.Twenty_Six.md)" in first
    assert "- [previous chapter](../0001-0025/0001.One.md)" in second
    assert "- [next chapter](../../index.html)" in second


def test_apply_is_idempotent(tmp_path):
    content = make_content(tmp_path, {"0041..md": "First"})
    fix_content.apply(content)
    snapshot = {p.name: p.read_text(encoding="utf-8") for p in content.iterdir()}

    report = fix_content.apply(content)
    assert report.renames == [] and report.relinks == []
    assert {p.name: p.read_text(encoding="utf-8") for p in content.iterdir()} == snapshot


def test_check_reports_without_touching(tmp_path):
    content = make_content(tmp_path, {"0041..md": "First"})
    assert fix_content.main(["--content", str(content), "--check"]) == 1
    assert [p.name for p in content.iterdir()] == ["0041..md"]
    # 修完再 check 就应该静默通过
    fix_content.apply(content)
    assert fix_content.main(["--content", str(content), "--check"]) == 0


def test_duplicate_numbers_are_rejected(tmp_path):
    content = make_content(
        tmp_path,
        {"0001-0025/0001.A.md": "A", "0026-0050/0001.B.md": "B"},
    )
    with pytest.raises(SystemExit) as exc:
        fix_content.scan(content)
    assert "0001" in str(exc.value)


def test_missing_title_is_rejected(tmp_path):
    content = tmp_path / "content"
    content.mkdir()
    (content / "0001.No_Title.md").write_text("## Article\n\nHello.\n", encoding="utf-8")
    with pytest.raises(SystemExit) as exc:
        fix_content.scan(content)
    assert "0001.No_Title.md" in str(exc.value)
