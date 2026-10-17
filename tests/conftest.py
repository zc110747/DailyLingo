# -*- coding: utf-8 -*-
"""pytest 公共配置：把 ``scripts/`` 加入 import 路径，使测试可以直接 ``import build``。

另外提供两个可选的「开发期工具链」探测器：``find_node()`` 与 ``find_jsdom()``。
站点本身零依赖 —— 只有这些测试会用到它们，找不到时相关用例自动 skip。
"""

import glob
import os
import shutil
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SCRIPTS = ROOT / "scripts"

if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))


def find_node() -> str | None:
    """定位 node 可执行文件：PATH > 托管目录 > 常见安装位置。"""
    found = shutil.which("node")
    if found:
        return found
    patterns = [
        os.path.expanduser("~/.workbuddy/binaries/node/versions/*/node.exe"),
        os.path.expanduser("~/.workbuddy/binaries/node/versions/*/bin/node"),
        r"C:\Program Files\nodejs\node.exe",
    ]
    for pattern in patterns:
        matches = sorted(glob.glob(pattern))
        if matches:
            return matches[-1]
    return None


def find_jsdom() -> str | None:
    """返回可直接喂给 ``NODE_PATH`` 的 node_modules 目录（内含 jsdom）。

    jsdom 只是本机开发期的临时依赖，**不属于**站点或测试套件的硬依赖；
    找不到就跳过 DOM 交互测试，``pytest -q`` 依然全绿。
    """
    node = find_node()
    if node is None:
        return None
    bases = [
        os.path.join(os.path.dirname(node), "..", "workspace", "node_modules"),
        os.path.expanduser("~/.workbuddy/binaries/node/workspace/node_modules"),
        os.path.expanduser("~/node_modules"),
        str(ROOT / "node_modules"),
    ]
    for base in bases:
        candidate = Path(base)
        if (candidate / "jsdom" / "package.json").is_file():
            return str(candidate.resolve())
    return None
