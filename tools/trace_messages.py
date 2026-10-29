#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""从 trace jsonl 里抽出对话消息（role/content），看模型实际看到了什么、回了什么。"""
import json
import pathlib
import sys

path = pathlib.Path(sys.argv[1])
seen = set()
for i, line in enumerate(path.read_text("utf-8", errors="ignore").splitlines(), 1):
    if '"role"' not in line:
        continue
    try:
        obj = json.loads(line)
    except Exception:
        continue
    span = obj.get("span")
    if not isinstance(span, dict):
        continue
    blob = json.dumps(span, ensure_ascii=False)
    # span 里通常嵌了 request/response 的 JSON 字符串
    for key in ("attributes", "data", "payload"):
        v = span.get(key)
        if isinstance(v, str) and '"role"' in v:
            try:
                parsed = json.loads(v)
            except Exception:
                continue
            for msg in _walk(parsed):
                role = msg.get("role")
                content = msg.get("content")
                if isinstance(content, list):
                    content = " ".join(
                        c.get("text", "") for c in content if isinstance(c, dict)
                    )
                if not isinstance(content, str) or not content.strip():
                    continue
                sig = (role, content[:80])
                if sig in seen:
                    continue
                seen.add(sig)
                print(f"===== [{i}] {role} =====")
                print(content[:1200].replace("\\n", "\n"))
                print()


def _walk(node, out=None):
    out = [] if out is None else out
    if isinstance(node, dict):
        if "role" in node and "content" in node:
            out.append(node)
        for v in node.values():
            _walk(v, out)
    elif isinstance(node, list):
        for v in node:
            _walk(v, out)
    return out
