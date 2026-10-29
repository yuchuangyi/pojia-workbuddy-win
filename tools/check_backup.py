#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""核对封条：备份文件是否等于装载前原厂指纹，并汇总各层字节增量。"""
import hashlib
import json
import pathlib
import sys

from _locate import seal_path

seal = json.load(open(seal_path(), encoding="utf-8"))
bad = 0
per = {}
for key, rec in seal["files"].items():
    bak = pathlib.Path(rec["backup"])
    if rec.get("created"):
        print("NEW    ", rec["layer"], key)
        continue
    if not bak.exists():
        print("NOBAK  ", key)
        bad += 1
        continue
    ok = hashlib.sha256(bak.read_bytes()).hexdigest() == rec["before"]
    bad += 0 if ok else 1
    per[rec["layer"]] = per.get(rec["layer"], 0) + rec["delta"]
    print(("BAK-OK " if ok else "BAK-BAD"), rec["layer"], format(rec["delta"], "+d"), bak.name)

print()
print("备份完整性:", "ok" if bad == 0 else str(bad) + " 处异常")
print("各层字节增量:", json.dumps(per, ensure_ascii=False))
print("运行期基线:", json.dumps(seal.get("runtime_baseline"), ensure_ascii=False))
sys.exit(0 if bad == 0 else 2)
