#!/usr/bin/env python3
r"""DailyLingo 增量同步：content/ 或 sources/ 一变，站点 HTML 立刻重建。

用途：手工维护 Markdown 时不必反复敲 `python scripts/build.py`，
      保存 md（或放入新的 wav）后 1 秒内自动重新生成 index.html 与 src/*.html。

只用标准库；不联网、不生成音频（除非显式加 --audio）。

用法：
    python scripts/watch.py                 监听 content/**/*.md 与 sources/*.wav
    python scripts/watch.py --audio         新增 md 缺音频时，自动调用 EnglishAudio 生成
    python scripts/watch.py --audio --audio-tool "D:\...\eaudio.cmd"
    python scripts/watch.py --once          只检查并重建一次，然后退出
    python scripts/watch.py --interval 0.5  轮询间隔（秒，默认 1.0）

EnglishAudio（本地离线 TTS）查找顺序：
    --audio-tool 参数 > 环境变量 DAILYLINGO_AUDIO_TOOL > 系统 PATH 里的
    eaudio.cmd / EnglishAudio.exe / EnglishAudio > <仓库>/tools/eaudio.cmd
    都找不到时只重建网页并给出提示，不会中断监听。
    **刻意不写任何绝对路径**：工具已加入系统环境，各台电脑安装位置不同，写死会在换机后失效。

行为约定：
    * 重建是**全量**的（冷启动约 1.2 秒，之后通常 < 0.2 秒 —— 句子时间轴按 WAV 的
      大小/mtime 缓存，只有音频本身变了才重新分析）。原因：新增/删除一篇文章会改变相邻文章的
      上一篇/下一篇导航，只重写「变化的那一页」会留下一致的假象。
    * md 写坏时只打印错误并继续监听，不会退出——修好再存一次就会重建成功。
    * 被删除文章遗留的 src/*.html 只提示、**不自动删除**（避免误删生成物之外的改动）。
"""

from __future__ import annotations

import argparse
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import build  # noqa: E402  （同目录，复用唯一的构建逻辑）
import tts  # noqa: E402  （音频工具查找 / 合成的唯一实现）

ROOT = Path(__file__).resolve().parent.parent

# 兼容旧用法：仍可按 ``watch.AUDIO_TOOL_ENV`` 取环境变量名
AUDIO_TOOL_ENV = tts.AUDIO_TOOL_ENV


def resolve_audio_tool(explicit: str | None) -> Path | None:
    """工具查找的唯一实现在 ``scripts/tts.py``（监听与手动生成必须同一套判据）。"""
    return tts.resolve_audio_tool(explicit)


def snapshot(content_dir: Path, sources_dir: Path) -> dict[str, tuple[int, int]]:
    """{相对项目根的路径: (mtime_ns, size)}，只覆盖会触发重建的文件。"""
    state: dict[str, tuple[int, int]] = {}
    for folder, pattern, recursive in (
        (content_dir, "*.md", True),
        (sources_dir, "*.wav", False),
    ):
        if not folder.is_dir():
            continue
        paths = folder.rglob(pattern) if recursive else folder.glob(pattern)
        for path in sorted(paths):
            if any(part.startswith(".") for part in path.relative_to(folder).parts):
                continue
            try:
                st = path.stat()
            except OSError:
                continue
            state[relative(path)] = (st.st_mtime_ns, st.st_size)
    return state


def relative(path: Path) -> str:
    try:
        return path.relative_to(ROOT).as_posix()
    except ValueError:
        return path.as_posix()


def describe_changes(
    old: dict[str, tuple[int, int]], new: dict[str, tuple[int, int]]
) -> list[str]:
    changes: list[str] = []
    for name in sorted(new.keys() - old.keys()):
        changes.append(f"新增 {name}")
    for name in sorted(old.keys() - new.keys()):
        changes.append(f"删除 {name}")
    for name in sorted(old.keys() & new.keys()):
        if old[name] != new[name]:
            changes.append(f"修改 {name}")
    return changes


def missing_audio(content_dir: Path, sources_dir: Path) -> list[Path]:
    """content/**/*.md 里还没有同名 wav 的文章（支持按 Chapter 分子目录）。"""
    pending: list[Path] = []
    for md in build.iter_content_files(content_dir):
        if not (sources_dir / f"{md.stem}.wav").exists():
            pending.append(md)
    return pending


def make_audio(md: Path, sources_dir: Path, tool: Path) -> bool:
    """为单个 md 生成同名 wav。成功返回 True。

    实际调用在 ``scripts/tts.py``：对话体文章的 ``**Anna:**`` 会先被去掉再合成，
    页面上仍然看得到说话人 —— 详见该文件顶部的说明。
    """
    print(f"  [audio] {relative(md)} -> {relative(sources_dir / (md.stem + '.wav'))}", flush=True)
    ok, detail = tts.synthesize(md, sources_dir, tool)
    if ok:
        print(f"  [audio] ok: {detail}", flush=True)
    else:
        print(f"  [audio] 失败：{detail}", flush=True)
    return ok


def orphan_pages(content_dir: Path, out_dir: Path) -> list[str]:
    """src/ 里已经没有对应 md 的遗留页面。"""
    expected = {f"{md.stem}.html" for md in build.iter_content_files(content_dir)}
    src_dir = out_dir / "src"
    if not src_dir.is_dir():
        return []
    return sorted(p.name for p in src_dir.glob("*.html") if p.name not in expected)


def rebuild(content_dir: Path, out_dir: Path, sources_dir: Path) -> bool:
    started = time.perf_counter()
    try:
        result = build.build_site(content_dir, out_dir, sources_dir)
    except build.BuildError as exc:
        print(f"[{now()}] 构建失败：{exc}", flush=True)
        print("            修好 Markdown 再保存一次即可自动重建。", flush=True)
        return False
    except Exception as exc:  # 解析期的意外异常也不该让监听退出
        print(f"[{now()}] 构建异常：{type(exc).__name__}: {exc}", flush=True)
        return False

    elapsed = (time.perf_counter() - started) * 1000
    titles = " / ".join(a.display_title for a in result.articles)
    print(
        f"[{now()}] 已重建 {len(result.articles)} 篇（{len(result.chapters)} 个 Chapter）"
        f"，{elapsed:.0f} ms",
        flush=True,
    )
    print(f"            {titles}", flush=True)
    print(f"            index.html + src/*.html 共 {len(result.article_paths)} 页", flush=True)

    for warning in result.warnings:
        print(f"            [WARN] {warning}", flush=True)

    stale = orphan_pages(content_dir, out_dir)
    if stale:
        print(f"            提示：src/ 下有 {len(stale)} 个已无对应 md 的遗留页面，需人工删除：", flush=True)
        for name in stale:
            print(f"              - src/{name}", flush=True)
    return True


def now() -> str:
    return time.strftime("%H:%M:%S")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="监听 content/ 与 sources/ 并自动重建站点")
    parser.add_argument("--content", default=str(build.DEFAULT_CONTENT_DIR), help="Markdown 文章源目录")
    parser.add_argument("--out", default=str(build.DEFAULT_OUT_DIR), help="站点输出根目录")
    parser.add_argument("--sources", default=str(build.DEFAULT_SOURCES_DIR), help="WAV 音频目录")
    parser.add_argument("--interval", type=float, default=1.0, help="轮询间隔秒数（默认 1.0）")
    parser.add_argument("--audio", action="store_true", help="缺音频时自动调用 EnglishAudio 生成")
    parser.add_argument(
        "--audio-tool",
        default=None,
        help=f"eaudio.cmd 路径；也可用环境变量 {AUDIO_TOOL_ENV} 指定",
    )
    parser.add_argument("--once", action="store_true", help="只重建一次后退出")
    args = parser.parse_args(argv)

    content_dir = Path(args.content).resolve()
    out_dir = Path(args.out).resolve()
    sources_dir = Path(args.sources).resolve()

    audio_tool: Path | None = None
    if args.audio:
        audio_tool = resolve_audio_tool(args.audio_tool)
        if audio_tool is None:
            print("[WARN] 未找到 EnglishAudio（PATH 里既没有 eaudio.cmd 也没有 EnglishAudio.exe），"
                  "本次不生成音频，只重建网页。")
            print(f"       把工具加入系统 PATH，或用 --audio-tool <路径> / 环境变量 {AUDIO_TOOL_ENV} 指定，例如：")
            print("         python scripts/watch.py --audio --audio-tool "
                  r'"<安装目录>\eaudio.cmd"')
            print()

    print(f"DailyLingo 同步监听")
    print(f"  content : {content_dir}")
    print(f"  sources : {sources_dir}")
    print(f"  输出     : {out_dir}")
    print(f"  自动生成音频：{'开' if args.audio else '关（加 --audio 开启）'}")
    if audio_tool is not None:
        print(f"  EnglishAudio : {audio_tool}")
    print(f"  间隔     : {args.interval}s")
    print()

    if audio_tool is not None:
        for md in missing_audio(content_dir, sources_dir):
            make_audio(md, sources_dir, audio_tool)

    if not rebuild(content_dir, out_dir, sources_dir):
        if args.once:
            return 1

    if args.once:
        return 0

    state = snapshot(content_dir, sources_dir)
    print()
    print(f"[{now()}] 开始监听，Ctrl+C 退出。", flush=True)

    try:
        while True:
            time.sleep(args.interval)
            new_state = snapshot(content_dir, sources_dir)
            changes = describe_changes(state, new_state)
            if not changes:
                continue

            print()
            for change in changes:
                print(f"[{now()}] {change}", flush=True)

            if audio_tool is not None and any(c.startswith(("新增", "修改")) for c in changes):
                for md in missing_audio(content_dir, sources_dir):
                    make_audio(md, sources_dir, audio_tool)
                new_state = snapshot(content_dir, sources_dir)

            state = new_state
            rebuild(content_dir, out_dir, sources_dir)
    except KeyboardInterrupt:
        print()
        print(f"[{now()}] 已停止监听。", flush=True)
        return 0


if __name__ == "__main__":
    raise SystemExit(main())
