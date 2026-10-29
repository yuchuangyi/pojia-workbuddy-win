#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""粗读 trace：把 user / assistant 的文本片段按出现顺序打出来（不依赖具体 schema）。"""
import pathlib
import re
import sys

tr = pathlib.Path(sys.argv[1])
txt = tr.read_text("utf-8", errors="ignore")

for role in ("user", "assistant"):
    print(f"===== {role} 片段 =====")
    seen = set()
    for m in re.finditer(r'role\\?":\\?"' + role + r'\\?",\\?"(?:(?:content)\\?":\\?")(.{80,1200}?)(?<!\\)\\?"', txt):
        seg = m.group(1).replace("\\n", "\n").replace('\\"', '"')
        key = seg[:50]
        if key in seen:
            continue
        seen.add(key)
        print("---")
        print(seg[:700])
        if len(seen) >= 3:
            break
    if not seen:
        # 退一步：找 role 后面最近的 content 字段
        for m in list(re.finditer(r'"role":"' + role + '"', txt))[:2]:
            print("--- (raw)", txt[m.start():m.start() + 600].replace("\\n", "\n"))
    print()
