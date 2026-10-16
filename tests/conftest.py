# -*- coding: utf-8 -*-
"""pytest 公共配置：把 ``scripts/`` 加入 import 路径，使测试可以直接 ``import build``。"""

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SCRIPTS = ROOT / "scripts"

if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))
