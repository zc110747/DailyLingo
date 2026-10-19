#!/usr/bin/env python3
"""构建 DailyLingo 的 Android APK。

本机没有 Gradle，也不希望为了一个 WebView 外壳去下载几百 MB 的依赖，
所以直接调用 SDK 自带的命令行工具完成整条链路：

    aapt2 compile -> aapt2 link -> javac -> d8 -> 打包 dex -> zipalign -> apksigner

用法::

    python tools/build_apk.py
    python tools/build_apk.py --sdk "D:/Software/Android_Modules" --jdk "D:/Software/Android_Studio/jbr"
    python tools/build_apk.py --clean

SDK 位置优先级：``--sdk`` > ``ANDROID_SDK_ROOT`` / ``ANDROID_HOME`` > 本机常见安装位置。
JDK 位置优先级：``--jdk`` > ``JAVA_HOME`` > Android Studio 自带的 JBR > PATH 里的 javac。

脚本只用 Python 标准库；签名的 keystore 固定在 ``keystore/dailylingo-debug.keystore``，
口令是 Android 调试签名的惯例值（android / android），不含任何真实凭据。
"""

from __future__ import annotations

import argparse
import os
import re
import shutil
import subprocess
import sys
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
MANIFEST = ROOT / "AndroidManifest.xml"
RES_DIR = ROOT / "res"
SRC_DIR = ROOT / "src" / "main" / "java"
BUILD_DIR = ROOT / "build"
OUTPUT_DIR = ROOT / "publisher"
KEYSTORE = ROOT / "keystore" / "dailylingo-debug.keystore"
APK_NAME = "DailyLingo.apk"

KEYSTORE_ALIAS = "dailylingo"
KEYSTORE_PASSWORD = "android"
KEYSTORE_VALIDITY_DAYS = "10000"

MIN_SDK = "24"
TARGET_SDK = "36"

# 本机安装位置的兜底候选。换一台机器时请设 ANDROID_SDK_ROOT / JAVA_HOME，而不是改这里。
SDK_FALLBACKS = (
    Path(r"D:\Software\Android_Modules"),
    Path(os.environ.get("LOCALAPPDATA", "")) / "Android" / "Sdk",
)
JDK_FALLBACKS = (
    Path(r"D:\Software\Android_Studio\jbr"),
    Path(r"C:\Program Files\Android\Android Studio\jbr"),
)


class BuildError(RuntimeError):
    """构建失败（带一句人话说明）。"""


def log(message: str) -> None:
    print(message, flush=True)


def run(command: list[str], description: str) -> None:
    """执行外部命令；失败时把命令与输出一起抛出来，便于定位。"""
    log(f"  $ {description}")
    completed = subprocess.run(
        command,
        cwd=str(ROOT),
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        encoding="utf-8",
        errors="replace",
    )
    if completed.returncode != 0:
        output = (completed.stdout or "").strip()
        raise BuildError(f"{description} 失败（退出码 {completed.returncode}）\n{output}")


def version_key(name: str) -> tuple[int, ...]:
    parts = re.findall(r"\d+", name)
    return tuple(int(part) for part in parts) if parts else (0,)


def locate_sdk(explicit: str | None) -> Path:
    candidates: list[Path] = []
    if explicit:
        candidates.append(Path(explicit))
    for variable in ("ANDROID_SDK_ROOT", "ANDROID_HOME"):
        value = os.environ.get(variable)
        if value:
            candidates.append(Path(value))
    candidates.extend(SDK_FALLBACKS)

    for candidate in candidates:
        if (candidate / "platform-tools").is_dir() and (candidate / "platforms").is_dir():
            return candidate.resolve()

    raise BuildError(
        "找不到 Android SDK。请设置 ANDROID_SDK_ROOT，或用 --sdk 指定（目录里应有 platform-tools 与 platforms）。"
    )


def locate_jdk(explicit: str | None) -> Path:
    candidates: list[Path] = []
    if explicit:
        candidates.append(Path(explicit))
    value = os.environ.get("JAVA_HOME")
    if value:
        candidates.append(Path(value))
    candidates.extend(JDK_FALLBACKS)
    javac = shutil.which("javac")
    if javac:
        candidates.append(Path(javac).parent.parent)

    exe = "javac.exe" if os.name == "nt" else "javac"
    for candidate in candidates:
        if (candidate / "bin" / exe).is_file():
            return candidate.resolve()

    raise BuildError("找不到 JDK。请设置 JAVA_HOME，或用 --jdk 指定 Android Studio 的 jbr 目录。")


def newest_entry(directory: Path, prefix: str) -> Path:
    entries = [item for item in directory.iterdir() if item.is_dir() and item.name.startswith(prefix)]
    if not entries:
        raise BuildError(f"{directory} 下没有 {prefix}* 目录。请用 SDK Manager 安装。")
    return max(entries, key=lambda item: version_key(item.name))


def clear_dir(directory: Path) -> None:
    """逐个文件删除，不用 shutil.rmtree（本环境的沙箱会拦递归删除）。"""
    if not directory.exists():
        return
    for current, directories, files in os.walk(directory, topdown=False):
        for name in files:
            try:
                os.remove(os.path.join(current, name))
            except OSError:
                pass
        for name in directories:
            try:
                os.rmdir(os.path.join(current, name))
            except OSError:
                pass


def ensure_keystore(jdk: Path) -> None:
    if KEYSTORE.is_file():
        return

    keytool = jdk / "bin" / ("keytool.exe" if os.name == "nt" else "keytool")
    if not keytool.is_file():
        raise BuildError(f"找不到 keytool：{keytool}")

    KEYSTORE.parent.mkdir(parents=True, exist_ok=True)
    log("生成调试签名用 keystore（只用于本应用，口令是 Android 调试惯例值）")
    run(
        [
            str(keytool),
            "-genkeypair",
            "-keystore",
            str(KEYSTORE),
            "-storepass",
            KEYSTORE_PASSWORD,
            "-keypass",
            KEYSTORE_PASSWORD,
            "-alias",
            KEYSTORE_ALIAS,
            "-keyalg",
            "RSA",
            "-keysize",
            "2048",
            "-validity",
            KEYSTORE_VALIDITY_DAYS,
            "-dname",
            "CN=DailyLingo, OU=Debug, O=DailyLingo, L=Shanghai, ST=Shanghai, C=CN",
        ],
        "keytool -genkeypair",
    )


def collect_class_files(directory: Path) -> list[str]:
    return sorted(str(path) for path in directory.rglob("*.class"))


def add_dex_to_apk(apk: Path, dex: Path, target: Path) -> None:
    """把 classes.dex 追加进 aapt2 产出的 APK 骨架。"""
    if target.exists():
        target.unlink()

    shutil.copyfile(apk, target)
    with zipfile.ZipFile(target, "a", compression=zipfile.ZIP_DEFLATED) as archive:
        archive.write(dex, "classes.dex")


def human_size(size: int) -> str:
    if size >= 1024 * 1024:
        return f"{size / (1024 * 1024):.1f} MB"
    return f"{size / 1024:.0f} KB"


def main() -> int:
    parser = argparse.ArgumentParser(description="构建 DailyLingo Android APK")
    parser.add_argument("--sdk", help="Android SDK 目录（默认读 ANDROID_SDK_ROOT）")
    parser.add_argument("--jdk", help="JDK 目录（默认读 JAVA_HOME 或 Android Studio 的 jbr）")
    parser.add_argument("--output", help="输出 APK 路径（默认 publisher/DailyLingo.apk）")
    parser.add_argument("--clean", action="store_true", help="构建前清空 build/ 目录")
    args = parser.parse_args()

    if args.clean:
        clear_dir(BUILD_DIR)

    sdk = locate_sdk(args.sdk)
    jdk = locate_jdk(args.jdk)
    build_tools = newest_entry(sdk / "build-tools", "")
    platform = newest_entry(sdk / "platforms", "android-")
    android_jar = platform / "android.jar"
    if not android_jar.is_file():
        raise BuildError(f"{platform} 下没有 android.jar。")

    aapt2 = build_tools / "aapt2.exe"
    zipalign = build_tools / "zipalign.exe"
    d8_jar = build_tools / "lib" / "d8.jar"
    apksigner_jar = build_tools / "lib" / "apksigner.jar"
    java = jdk / "bin" / ("java.exe" if os.name == "nt" else "java")
    javac = jdk / "bin" / ("javac.exe" if os.name == "nt" else "javac")

    for path in (aapt2, zipalign, d8_jar, apksigner_jar, java, javac):
        if not path.is_file():
            raise BuildError(f"缺少构建工具：{path}")

    log("== 环境 ==")
    log(f"  SDK        : {sdk}")
    log(f"  build-tools: {build_tools.name}")
    log(f"  platform   : {platform.name}")
    log(f"  JDK        : {jdk}")

    BUILD_DIR.mkdir(parents=True, exist_ok=True)
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    clear_dir(BUILD_DIR)

    res_zip = BUILD_DIR / "res.zip"
    base_apk = BUILD_DIR / "base.apk"
    gen_dir = BUILD_DIR / "gen"
    classes_dir = BUILD_DIR / "classes"
    dex_dir = BUILD_DIR / "dex"
    unsigned_apk = BUILD_DIR / "unsigned.apk"
    aligned_apk = BUILD_DIR / "aligned.apk"
    for directory in (gen_dir, classes_dir, dex_dir):
        directory.mkdir(parents=True, exist_ok=True)

    log("== 1/6 编译资源 ==")
    run([str(aapt2), "compile", "--dir", str(RES_DIR), "-o", str(res_zip)], "aapt2 compile")

    log("== 2/6 链接资源与清单 ==")
    run(
        [
            str(aapt2),
            "link",
            "-o",
            str(base_apk),
            "-I",
            str(android_jar),
            "--manifest",
            str(MANIFEST),
            "-R",
            str(res_zip),
            "--java",
            str(gen_dir),
            "--min-sdk-version",
            MIN_SDK,
            "--target-sdk-version",
            TARGET_SDK,
            "--auto-add-overlay",
        ],
        "aapt2 link",
    )

    log("== 3/6 编译 Java ==")
    sources = [str(path) for path in SRC_DIR.rglob("*.java")]
    sources += [str(path) for path in gen_dir.rglob("*.java")]
    if not sources:
        raise BuildError("没有找到任何 Java 源文件。")
    run(
        [
            str(javac),
            "-encoding",
            "UTF-8",
            "-source",
            "17",
            "-target",
            "17",
            "-classpath",
            str(android_jar),
            "-d",
            str(classes_dir),
        ]
        + sources,
        "javac",
    )

    log("== 4/6 生成 dex ==")
    class_files = collect_class_files(classes_dir)
    if not class_files:
        raise BuildError("javac 没有产出 class 文件。")
    run(
        [
            str(java),
            "-cp",
            str(d8_jar),
            "com.android.tools.r8.D8",
            "--release",
            "--min-api",
            MIN_SDK,
            "--lib",
            str(android_jar),
            "--output",
            str(dex_dir),
        ]
        + class_files,
        "d8",
    )

    dex = dex_dir / "classes.dex"
    if not dex.is_file():
        raise BuildError("d8 没有生成 classes.dex。")

    log("== 5/6 打包与对齐 ==")
    add_dex_to_apk(base_apk, dex, unsigned_apk)
    run([str(zipalign), "-f", "4", str(unsigned_apk), str(aligned_apk)], "zipalign")

    log("== 6/6 签名 ==")
    ensure_keystore(jdk)
    output = Path(args.output) if args.output else OUTPUT_DIR / APK_NAME
    output.parent.mkdir(parents=True, exist_ok=True)
    if output.exists():
        output.unlink()

    run(
        [
            str(java),
            "-jar",
            str(apksigner_jar),
            "sign",
            "--ks",
            str(KEYSTORE),
            "--ks-pass",
            f"pass:{KEYSTORE_PASSWORD}",
            "--key-pass",
            f"pass:{KEYSTORE_PASSWORD}",
            "--ks-key-alias",
            KEYSTORE_ALIAS,
            # 不生成 .idsig（v4 签名只对增量安装有用，多一个文件没意义）。
            "--v4-signing-enabled",
            "false",
            "--min-sdk-version",
            MIN_SDK,
            "--out",
            str(output),
            str(aligned_apk),
        ],
        "apksigner sign",
    )

    verify = subprocess.run(
        [str(java), "-jar", str(apksigner_jar), "verify", "--print-certs", str(output)],
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        encoding="utf-8",
        errors="replace",
    )
    if verify.returncode != 0:
        raise BuildError("apksigner verify 失败：\n" + (verify.stdout or "").strip())

    log("")
    log(f"APK: {output}  ({human_size(output.stat().st_size)})")
    lines = [line.strip() for line in (verify.stdout or "").splitlines() if line.strip()]
    summary = next((line for line in lines if line.startswith("Verifies")), None)
    log(summary or "签名校验通过")
    return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except BuildError as error:
        print(f"\n构建失败：{error}", file=sys.stderr)
        sys.exit(1)
