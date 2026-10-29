#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""在 trace jsonl 里定位注入标记，并判断它出现在哪一类事件（系统提示 / 工具结果 / 用户消息）。"""
import json
import pathlib
import sys

path = pathlib.Path(sys.argv[1])
needle = sys.argv[2] if len(sys.argv) > 2 else "POJIA:L3"

for i, line in enumerate(path.read_text("utf-8", errors="ignore").splitlines(), 1):
    if needle not in line:
        continue
    try:
        obj = json.loads(line)
    except Exception:
        print(f"[{i}] 非 JSON 行，前 300 字: {line[:300]}")
        continue
    kind = obj.get("type") or obj.get("name") or "?"
    name = obj.get("name") or ""
    # 找出承载 needle 的顶层键
    holders = []
    for k, v in obj.items():
        s = json.dumps(v, ensure_ascii=False) if not isinstance(v, str) else v
        if needle in s:
            holders.append(k)
    print(f"[{i}] type={kind} name={name} 命中键={holders}")
    for k in holders:
        s = obj[k] if isinstance(obj[k], str) else json.dumps(obj[k], ensure_ascii=False)
        idx = s.find(needle)
        print(f"    {k} 片段: ...{s[max(0, idx-160):idx+160]}...")
    print()
