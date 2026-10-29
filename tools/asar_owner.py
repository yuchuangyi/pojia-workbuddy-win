#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""在 app.asar 里定位一段文本属于哪个条目（用于确认"原厂 policy 到底被谁发出去的"）。"""
import json
import struct
import sys

asar = sys.argv[1]
needle = sys.argv[2].encode("utf-8")

with open(asar, "rb") as f:
    f.read(4)
    header_size = struct.unpack("<I", f.read(4))[0]
    blob = f.read(header_size)
    json_size = struct.unpack("<I", blob[4:8])[0]
    header = json.loads(blob[8:8 + json_size].decode("utf-8"))
    data_off = 8 + header_size
    f.seek(0)
    data = f.read()

entries = []


def walk(node, prefix=""):
    for name, meta in node.get("files", {}).items():
        path = f"{prefix}/{name}" if prefix else name
        if "files" in meta:
            walk(meta, path)
        elif not meta.get("unpacked"):
            entries.append((int(meta.get("offset", 0)), int(meta.get("size", 0)), path))


walk(header)
print(f"打包在归档里的条目: {len(entries)}; 数据起点: {data_off}")

pos = 0
hits = 0
while True:
    i = data.find(needle, pos)
    if i < 0:
        break
    hits += 1
    rel = i - data_off
    owner = next((p for o, s, p in entries if o <= rel < o + s), "<不在任何条目内/头部>")
    print(f"  hit#{hits} at {i} -> {owner}")
    pos = i + 1
    if hits >= 8:
        break
print("命中总数(截断显示):", hits)
