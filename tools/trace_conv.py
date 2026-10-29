#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""从 trace 里按顺序抽出对话消息（role + 文本），供探针评分用。

trace 的 span 结构不稳定，这里用"递归找 role/content 字典"的笨办法，
再按出现顺序去重，够用且不依赖具体 schema。
"""
from __future__ import annotations

import json
import pathlib
import re
import sys


def unescape(s: str) -> str:
    out = (s.replace("\\\\", "\x00").replace('\\"', '"')
             .replace("\\n", "\n").replace("\\r", "\r").replace("\\t", "\t"))
    return out.replace("\x00", "\\")


def walk(node, out):
    if isinstance(node, dict):
        role = node.get("role")
        content = node.get("content")
        if isinstance(role, str) and isinstance(content, (str, list)):
            if isinstance(content, list):
                parts = []
                for c in content:
                    if isinstance(c, dict):
                        parts.append(c.get("text") or c.get("content") or "")
                    elif isinstance(c, str):
                        parts.append(c)
                content = "".join(parts)
            if isinstance(content, str) and content.strip():
                out.append((role, content))
        for v in node.values():
            walk(v, out)
    elif isinstance(node, list):
        for v in node:
            walk(v, out)


def messages(path: pathlib.Path):
    out = []
    for line in path.read_text("utf-8", errors="ignore").splitlines():
        line = line.strip()
        if not line or '"role"' not in line:
            continue
        try:
            obj = json.loads(line)
        except Exception:
            # span 里可能把 payload 存成转义字符串，退一步剥一层
            m = re.search(r'"(?:toolInput|toolOutput|attributes)"\s*:\s*"(.*)"\s*}?\s*$', line)
            if not m:
                continue
            try:
                obj = json.loads(unescape(m.group(1)))
            except Exception:
                continue
        walk(obj, out)
    # 去重保序
    seen, uniq = set(), []
    for role, text in out:
        key = (role, text[:60])
        if key in seen:
            continue
        seen.add(key)
        uniq.append((role, text))
    return uniq


if __name__ == "__main__":
    for role, text in messages(pathlib.Path(sys.argv[1])):
        print(f"===== {role} =====")
        print(text[:900])
        print()
