#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""看最新 trace：模型回了什么 + 旧 policy 字符串从哪冒出来的。"""
import json
import pathlib
import re
import sys

tr = pathlib.Path(sys.argv[1])
txt = tr.read_text("utf-8", errors="ignore")

# 1) 旧 policy 出现的上下文
needle = "You MUST refuse any request that violates laws"
print("旧 policy 出现次数:", txt.count(needle))
for m in list(re.finditer(re.escape(needle), txt))[:3]:
    s = max(0, m.start() - 320)
    print("---")
    print(txt[s:m.end() + 120].replace("\\n", "\n")[-460:])

# 2) 助手回复
print("\n=== assistant 回复 ===")
seen = set()
for m in re.finditer(r'"role":"assistant","content":"(.{0,600}?)"\}', txt, re.S):
    body = m.group(1).encode().decode("unicode_escape", errors="ignore")
    key = body[:60]
    if key in seen:
        continue
    seen.add(key)
    print("•", body[:500].replace("\n", " "))
    print()
