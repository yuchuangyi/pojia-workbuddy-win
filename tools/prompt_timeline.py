#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""打印最近的会话装配记录：时间 / 模式 / 场景 / 系统提示长度 / 变量总长。"""
import re
import pathlib
import sys

HOME = pathlib.Path.home()
logs = HOME / ".workbuddy" / "logs"
LINE = re.compile(r"\[(\d{4}/\d{2}/\d{2} \d{2}:\d{2}:\d{2})\.\d+\].*?resolveConfig output (.*)")
SP = re.compile(r'"systemPrompt":\{"length":(\d+)')
VS = re.compile(r'"promptContextVariables":\{"keys":\[[^\]]*\],"totalLength":(\d+)')
MODE = re.compile(r'"mode":"([A-Za-z-]+)"')
WELCOME = re.compile(r'"welcomeMode":"([A-Za-z-]+)"')
MCPS = re.compile(r'"hasDeclaredMcp":(true|false)')

rows = []
files = sorted(logs.rglob("*.log"), key=lambda p: p.stat().st_mtime, reverse=True)
main = [p for p in files if p.name.startswith("workbuddyMainThread")]
for p in (main + files)[:8]:
    for stamp, payload in LINE.findall(p.read_text("utf-8", errors="ignore")):
        sp, vs = SP.search(payload), VS.search(payload)
        if not sp:
            continue
        rows.append((stamp, MODE.search(payload).group(1) if MODE.search(payload) else "-",
                     WELCOME.search(payload).group(1) if WELCOME.search(payload) else "-",
                     int(sp.group(1)), int(vs.group(1)) if vs else -1))
rows = sorted(set(rows))
print(f"{'时间':<22}{'模式':<10}{'场景':<12}{'systemPrompt':>13}{'vars':>9}")
for r in rows[-14:]:
    print(f"{r[0]:<22}{r[1]:<10}{r[2]:<12}{r[3]:>13}{r[4]:>9}")
