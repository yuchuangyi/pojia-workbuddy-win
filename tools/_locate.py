#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""从脚本自身位置往上找工作副本根目录 —— 不依赖 cwd，`cd tools` 里也能跑。"""
import pathlib


def root(start=None) -> pathlib.Path:
    here = pathlib.Path(start or __file__).resolve()
    here = here if here.is_dir() else here.parent
    for d in (here, here.parent, here.parent.parent):
        if (d / "seal.json").exists() or (d / "pojia.py").exists():
            return d
    return here.parent


def seal_path() -> pathlib.Path:
    p = root() / "seal.json"
    if not p.exists():
        raise SystemExit(f"没找到 {p} —— 还没装过，或工作副本不完整（seal.json 在 .gitignore 里）")
    return p
