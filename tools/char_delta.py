#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""按"字符数"（JS 字符串长度口径）核算各层增量，并与日志里的装配长度对账。"""
import json
import pathlib

seal = json.load(open("seal.json", encoding="utf-8"))
char_delta = {}
for key, rec in seal["files"].items():
    bak = pathlib.Path(rec["backup"])
    if rec.get("created") or not bak.exists():
        continue
    before = bak.read_text("utf-8")
    after = pathlib.Path(key).read_text("utf-8")
    d = len(after) - len(before)
    char_delta[pathlib.Path(key).name] = d
    print(f"{rec['layer']:<3}{d:+6d} 字符   {pathlib.Path(key).name}")

print()
tpl = char_delta.get("workbuddy-prompt.tpl", 0)
idt = char_delta.get("user-context-identity.tpl", 0)
idt_x = char_delta.get("user-context-expert-identity.tpl", 0)
ask = char_delta.get("workbuddy-ask-prompt.tpl", 0)
print(f"craft  场景 systemPrompt 预期增量 = {tpl:+d} (主提示) {idt:+d} (身份模板) = {tpl + idt:+d}")
print(f"expert 场景 systemPrompt 预期增量 = {tpl + idt_x:+d}")
print(f"ask    场景 systemPrompt 预期增量 = {ask + idt:+d}")
persona = sum(char_delta.get(n, 0) for n in ("SOUL.md", "IDENTITY.md", "USER.md", "MEMORY.md"))
print(f"人格文件 vars 预期增量 = {persona:+d}")
cfg = [k for k in seal["files"] if k.endswith("app-config.json")]
if cfg:
    cur = json.loads(pathlib.Path(cfg[0]).read_text("utf-8"))
    payload = cur.get("personalization", {}).get("customPrompt", "")
    print(f"customPrompt 载荷长度 = {len(payload)} 字符（重启后进 UserCustomPrompt 槽，再加到 systemPrompt 上）")
