#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""结构体检：改装后模板的 nunjucks 标签是否仍然成对，占位符是否还在。"""
import json
import pathlib
import re

seal = json.load(open("seal.json", encoding="utf-8"))
bad = 0
for key, rec in seal["files"].items():
    if not key.endswith(".tpl"):
        continue
    before = pathlib.Path(rec["backup"]).read_text("utf-8")
    after = pathlib.Path(key).read_text("utf-8")
    stat = lambda s: (s.count("{%"), s.count("%}"), s.count("{{"), s.count("}}"))
    b, a = stat(before), stat(after)
    need_policy = pathlib.Path(key).name.startswith("workbuddy-")
    ok = a[0] == a[1] and a[2] == a[3]
    if need_policy:
        ok = ok and "</content_policy>" in after
    placeholders_lost = set(re.findall(r"\{\{\s*([A-Za-z_0-9.]+)\s*\}\}", before)) - set(
        re.findall(r"\{\{\s*([A-Za-z_0-9.]+)\s*\}\}", after)
    )
    if not ok or placeholders_lost:
        bad += 1
    print(f"{'OK ' if ok and not placeholders_lost else 'BAD'} {pathlib.Path(key).name:<40} "
          f"tags {b[0]}/{b[1]} -> {a[0]}/{a[1]}  vars {b[2]}/{b[3]} -> {a[2]}/{a[3]}  "
          f"lost={sorted(placeholders_lost)}")
print()
print("结构体检:", "全部通过" if bad == 0 else f"{bad} 个文件异常")
