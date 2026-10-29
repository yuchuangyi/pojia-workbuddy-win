# 审查意见：pojia.py v2 的缺陷与完善项

审查对象：`pojia.py` 21,602 字节（commit b3f1f4e），WorkBuddy 5.9.3 / Windows，Python 3.13.14。

方法两路：

1. **隔离环境**：`%TEMP%\pjlab` 下搭假安装目录 + 假人格目录，用 `WB_INSTALL` / `USERPROFILE` 隔离，完整跑了 apply → apply → 删 seal → apply → restore → 错路径 apply。
2. **真机核对**：在作者本机的部署（`D:\workbuddy-pojia`，全装载态）上，把磁盘文件、asar 的 unpacked 标志、trace 里的实际请求体三方对上。

结论：**主链路（首次装载、幂等重跑、封条校验、还原）是对的**，但验收链是断的——三条验收命令全绿，请求里的 policy 仍是原厂内容（P0-5）。根因最终定位到 **L8 打错文件**：welcomeMode 读的是插件缓存，安装目录那份是副本。

## 修复状态（v3 已落地）

| 编号 | 状态 | 说明 |
|---|---|---|
| P0-1 seal 缺失导致重复追加 | ✅ 已修 | `_in_place` 探针 + 封条缺失时拒绝执行（`--force` 可越过） |
| P0-2 装错目录静默降级 | ✅ 已修 | 安装目录自动探测 + `require_install()` + 靶点结构断言 |
| P0-3 restore 覆盖新版模板 | ✅ 已修 | 当前哈希既非 before 也非 after 时跳过，`--force` 可强行 |
| P0-4 trace 假阳性 | ✅ 已修 | 只解析 `generation` span 的 `toolInput`；新增 `inspect` 子命令 |
| P0-5 L1/L8 未进请求 | ✅ 已修 | L8 靶点改指插件缓存（本机 12 份）+ 安装目录副本，`inspect` 从 0/44 → 20/20 |
| P1-1 安装路径不探测 | ✅ 已修 | env → 常见路径 → 进程反查 |
| P1-3 缺 dry-run | ✅ 已修 | `apply --dry-run`，seal 与文件都不动 |
| P1-2 封条绑脚本目录 | ⚠️ 未改 | 改为"检测到已改装态就拒绝"，比加 `--state-dir` 更省事，先这样 |
| P1-4 长度对账误判 | ✅ 已修 | 模式不一致时直接标注"不可比，用 inspect" |
| P2 清单 | 部分 | 见文末 |

v3 的回归结果在文末「v3 回归记录」。

---

## P0-1 seal 缺失时把已改装文件当原厂，重复追加且永久失去还原能力

### 现象（实测）

```
第1次 apply → 12 个靶点写入
第2次 apply →  0 个靶点写入，12 个已是目标态     ← 幂等正常
删掉 seal.json
第3次 apply →  4 个靶点写入，8 个已是目标态
  → grep -c "环境与交付偏好" SOUL.md   = 2      ← 追加了两遍
  → grep -c "环境备忘"       MEMORY.md = 2      ← 前置了两遍
  → status：8 个明明已装载的文件报"未装载"
  → restore：只还原 4 个文件，SKILL.md 残留
```

### 根因（两处，叠加放大）

`cmd_apply`，`pojia.py:350-353`：

```python
bpath = Path(rec["backup"]) if rec and Path(rec["backup"]).exists() else None
pristine = bpath.read_bytes() if bpath else (p.read_bytes() if p.exists() else b"")
```

无封条时 `pristine` 退化成"当前文件"——而当前文件已经是改装过的。接着 `render_append` 无条件追加，于是第二遍。

`cmd_apply`，`pojia.py:378-380`：

```python
if p.exists() and sha256(p.read_bytes()) == sha256(after):
    skipped += 1
    continue          # ← 跳过了 files[str(p)] = rec_of(...)
```

这 8 个"内容已是目标态"的靶点既不备份也不写封条，于是它们在 `seal.json` 里不存在：`status` 报"未装载"（说谎），`restore` 遍历 `files` 时碰不到它们（漏还原），`created` 的 L7 永远删不掉。

### 触发条件（三条都常见）

1. `git clone` 到新目录再跑 —— `.gitignore` 同时忽略了 `seal.json` 和 `backup/`，克隆出来的副本**必然**没有封条。
2. `git clean -xfd` / 手工删 `seal.json`。
3. `apply` 中途抛 `PermissionError`：`save_seal(seal)` 在 `pojia.py:389` 只在全部成功后调用一次，第 19 个靶点写失败时前 18 个已落盘但封条一条都没存 —— 直接退化成场景 1。

### 修法（三处，都不引入标记）

**(a) append / prepend 自愈**，`pojia.py:295-305`：

```python
def _in_place(text: str, nl: str, block: str) -> bool:
    """载荷首 80 字符已在文中 —— 用它判断是否已装载，不带任何标记。"""
    probe = crlf(block.strip("\n")[:80], nl)
    return probe and probe in text


def render_append(text: str, nl: str, block: str) -> str:
    if _in_place(text, nl, block):
        return text
    return text.rstrip() + nl + nl + crlf(block.strip("\n"), nl) + nl


def render_prepend(text: str, nl: str, block: str) -> str:
    if _in_place(text, nl, block):
        return text
    body = crlf(block.strip("\n"), nl) + nl
    m = re.match(r"(?s)^(---\r?\n.*?\r?\n---\r?\n)", text)
    if m:
        return m.group(1) + nl + body + text[m.end():]
    return body + text
```

探针用的是载荷正文前 80 字（本来就该在文件里），不新增任何可疑字符串，v1 的教训不受影响。

**(b) skip 分支补写封条**，`pojia.py:378-381`：

```python
if p.exists() and sha256(p.read_bytes()) == sha256(after):
    if rec is None:                      # 内容已是目标态但无封条
        cur = p.read_bytes()
        files[str(p)] = rec_of(layer, p, cur, cur, None,
                               created=False, adopted=True)
        print(f"  [{layer:<2}] {tgt['name']:<38} 认领（无原厂备份，不可还原）")
    skipped += 1
    continue
```

`adopted=True` 的记录 `before == after`，`restore` 里要显式跳过并汇总提示，不能静默。

**(c) 前置拦截**，`cmd_apply` 开头：seal 为空但检测到任一靶点已是目标态 → 打印清单 + `return 3`，不执行。宁可让人手工收拾，也不要静默叠加。

**(d) `save_seal` 放进 `try/finally`**，`pojia.py:389`：

```python
try:
    for tgt in targets():
        ...
finally:
    save_seal(seal)          # 半途失败也要把已写入的靶点落进封条
```

---

## P0-2 安装目录不对时不报错，静默只装 4 层

### 现象（实测）

```bash
$ WB_INSTALL="D:\nonexist-workbuddy" python pojia.py apply
  [L4] IDENTITY.md   +423 字节
  [L5] USER.md       +648 字节
  [L6] MEMORY.md     +493 字节
装载完成：4 个靶点写入，2 个已是目标态。
生效：新开一个对话即读新提示词（welcomeMode 走 L8，其它模式走 L1）
```

22 个靶点只找到 6 个（L0 + L3–L7），L1/L2/L8 全丢，**退出码仍是 0**，末尾还照样打印"welcomeMode 走 L8"。用户会以为装好了，然后发现模型行为没变，再去查半天。

根因：`plugin_prompts()` 在目录不存在时 `return []`（`pojia.py:247`），`tpl_files()` 对空目录 glob 返回 `[]`，`identity_tpls()` 有 `exists()` 过滤。三处都选择静默降级，`apply` 也没校验靶点总数。

### 修法

```python
def check_install() -> bool:
    probe = RES / "app.asar.unpacked"
    if not probe.exists():
        print(f"安装目录无效：{INSTALL}")
        print(f"  缺少：{probe}")
        print("  WB_INSTALL 要指向含 resources\\app.asar.unpacked 的那一层，")
        print("  不是 %APPDATA%\\WorkBuddy 这类数据目录。")
        return False
    return True


def cmd_apply(a) -> int:
    if not check_install():
        return 2
    ...
    expect = 22
    got = len(targets())
    if got != expect:
        print(f"靶点数量异常：{got}（预期 {expect}）。版本结构可能变了，先跑 status 核对。")
        return 2
```

---

## P0-3 restore 会拿旧原厂覆盖新版本的模板

场景：WorkBuddy 升到 5.9.4，模板内容变了，用户想"先还原干净再重装"，跑 `restore` → `shutil.copy2` 把 5.9.3 的原厂模板写进 5.9.4 的安装目录。

`cmd_restore`，`pojia.py:475-484` 只检查 `src.exists()`，不检查目标文件当前状态。修法：拷贝前先看当前哈希是不是 `before` 或 `after`，都不是就跳过。

```python
cur = sha256(p.read_bytes()) if p.exists() else ""
if cur not in (rec["before"], rec["after"]):
    print(f"  跳过（内容已变，可能是新版本）：{p}")
    skipped += 1
    continue
```

`restore` 末尾把 `skipped` 一起报出来，别只说"已还原 N 个文件"。

---

## P0-4 cmd_trace 的判定会被工具结果污染，产生假阳性

### 现象（实测）

在 `D:\workbuddy-pojia` 里跑 `python pojia.py trace`，22 个靶点全"封条一致"、装载态完整，输出是：

```
=== trace_5a7707a0872e4f4495b9cc174a479be2.jsonl  10-29 20:18:27
    L8/L1 policy     命中
    L2 identity      命中
    L3 SOUL          命中
    L5 USER          命中
    L6 MEMORY        命中
    L0 custom        命中
    旧 policy(未清)     命中        ← 新旧同时"命中"，逻辑上不可能
```

用 `tools/trace_probe.py` 定位那句旧 policy 出现在哪：

```
[426] type=span_end path=.span.toolInput    ← 我自己刚写的一段 Python 脚本
[72]  type=span_end path=.span.toolOutput   ← 读 pojia.py 的输出（带行号 442→）
```

`cmd_trace`，`pojia.py:450-456`：

```python
for tr in traces:
    txt = tr.read_text("utf-8", errors="ignore")     # 整个 jsonl 当纯文本
    for label, needle in probes.items():
        print(f"    {label:<16} {'命中' if needle in txt else '-'}")
```

不区分 `systemPrompt` / 用户消息 / `toolInput` / `toolOutput`。只要对话里读过 `pojia.py`（里面的 `POLICY` 常量和探针字符串本身就带这两个特征串），必然双命中。

### 后果

`trace` 是 README 里"唯一能确认改动进了请求"的手段。它一旦有假阳性，整条验收链就是空的——**磁盘对了、trace 说命中、模型行为没变**，然后所有时间都花在错误的方向上。本机就是这个状态。

### 修法

只扫承载请求体的 span，且只搜 `systemPrompt` 字段：

```python
def cmd_trace(_a) -> int:
    traces = sorted((UD / "traces").rglob("*.jsonl"),
                    key=lambda p: p.stat().st_mtime, reverse=True)[:6]
    for tr in traces:
        new = old = 0
        for line in tr.read_text("utf-8", errors="ignore").splitlines():
            if '"generation"' not in line:
                continue
            try:
                span = json.loads(line).get("span") or {}
            except Exception:
                continue
            ti = span.get("toolInput") or ""
            if "systemPrompt" not in ti:
                continue
            new += "single-operator workstation" in ti
            old += "You MUST refuse any request that violates laws" in ti
        if new or old:
            print(f"=== {tr.name}  新policy={new} 旧policy={old}")
```

探针也不要硬编码，从 `seal.json` 里各层的 `before`/`after` 差异段自动取前 40 字符（见 P2-5）。

---

## P0-5 L1/L8 改了，请求里仍是原厂 policy

### 现象（实测）

同一台机器、同一时刻：

| 检查 | 结果 |
|---|---|
| 磁盘上 `workbuddy-craft-code-prompt.tpl` 的 `<content_policy>` | 已换成 pojia 版（`single-operator workstation`） |
| 磁盘上 `user-context-identity.tpl` 的 `<product_identity>` | 已换成 pojia 版 |
| 请求体里的 `<product_identity>`（L2） | pojia 版 ✅（会话里可见新措辞） |
| 请求体里的 `<content_policy>`（L1/L8） | **44 份样本，44 份原厂版，0 份新版** ❌ |

时间线：19:34 首次 apply → 19:39 主进程启动 → 19:44 二次 apply → 20:12 新开会话 → 20:18 抽请求体。

复核脚本（`generation` span 的 `toolInput`，按 `<content_policy>` 过滤后统计）：

```
trace_5a7707a0....jsonl: 请求体 43 份  新 policy 0 / 旧 policy 43
```

跨多轮对话、44 份样本全为原厂版，排除"装配延迟"。

### 根因（已确认）

不是进程缓存，也不是"policy 由模板外代码拼装"——是 **L8 打错了文件**。

`welcomeMode`（work / code / design）的提示词实际加载路径是**版本化插件缓存**：

```
~\.workbuddy\plugins\cache\workbuddy-builtin\welcomemode-<mode>\<版本>\prompt.tpl
```

本机 3 模式 × 4 版本 = 12 份。v2 改的是安装目录里的 `resources\...\plugins\workbuddy-builtin\welcomemode\*\prompt.tpl`——那只是解压副本，从不参与装配。

排除其他假设的证据：

| 假设 | 反证 |
|---|---|
| 读了 asar 内部的原版 | `tools/asar_ls.py` 显示 templates 条目全部 `UNPACKED` |
| 整个 templates 目录没生效 | 同目录的 `user-context-identity.tpl`（L2）改动生效 |
| 装配慢半拍 | 44 份样本、跨多轮对话、跨 40 分钟，全是原厂 |
| 主模板被进程缓存 | 改对缓存文件后，新 trace 立刻 20/20 命中，无需重启也能看到新会话生效 |

### 为什么这条是 P0

README 把 `verify` 全绿当作装载成功的判据。但"文件改对了"和"模型看到了"是两件事，而工具链里没有任何一步能区分这两者：`verify` 只看哈希，`verify --runtime` 只看长度且不可比，`trace` 有假阳性（P0-4）。三条验收全绿而实际零效果，这个组合会让人误判好几天。

### 修法（已落地）

**L8 靶点改指真源**：

```python
def plugin_prompts() -> list[Path]:
    out: list[Path] = []
    if PLUGIN_CACHE.exists():                      # 真源：版本化缓存
        out += sorted(p for p in PLUGIN_CACHE.glob("welcomemode-*/**/prompt.tpl") if p.is_file())
    if PLUGIN_TPL.exists():                        # 副本：安装目录解压出来的
        out += sorted(p for p in PLUGIN_TPL.glob("*/prompt.tpl") if p.is_file())
    uniq, seen = [], set()
    for p in out:                                  # 同一文件只算一次
        key = str(p.resolve()).lower()
        if key not in seen:
            seen.add(key)
            uniq.append(p)
    return uniq
```

两处都改：缓存那份决定当前行为，副本那份保证升级/清缓存后不会立刻回到原厂。

**验收改成 `inspect`**：只解析最新 trace 的 `generation` span，输出 `新 policy / 旧 policy` 的分数，退出码 0/3/2/1 分别表示已生效/未生效/混杂/没抓到。

```python
def cmd_inspect(_a) -> int:
    """从最新 trace 的 generation span 里抽请求体，核对载荷是否真的进去了。"""
    traces = sorted((UD / "traces").rglob("*.jsonl"),
                    key=lambda p: p.stat().st_mtime, reverse=True)[:5]
    for tr in traces:
        new = old = seen = 0
        for line in tr.read_text("utf-8", errors="ignore").splitlines():
            try:
                span = json.loads(line).get("span") or {}
            except Exception:
                continue
            if span.get("name") != "generation":       # 只有它承载请求体
                continue
            ti = span.get("toolInput") or ""
            if "<content_policy>" not in ti:           # 没带系统提示的跳过
                continue
            seen += 1
            new += "single-operator workstation" in ti
            old += "You MUST refuse any request that violates laws" in ti
        if seen:
            print(f"{tr.name}: 请求体 {seen} 份  新policy {new}  旧policy {old}")
            return 0 if (new and not old) else 3
    print("最近 5 个 trace 里没有含 policy 的请求体。")
    return 1
```

注意判空：`ti` 为空、或者含 `<content_policy>` 但不是请求体的，都要跳过，否则会得到"0/0 → 未进入请求"的假阴性。

**文档侧**：README 的「生效方式」已改成「完全退出进程再启动」，§9.7 从"两个候选根因"改写成确认后的实测记录。

---

## P1-1 安装路径不自动探测（这是别人装不上的第一道坎）

`pojia.py:35`：

```python
INSTALL = Path(os.environ.get("WB_INSTALL") or r"D:\AppStoreSoftstore\WorkBuddy")
```

默认值是作者自己机器的路径。别人的机器 90% 在 `%LOCALAPPDATA%\Programs\WorkBuddy`，不改环境变量就跑，直接命中 P0-2 的静默降级。

```python
CANDIDATES = [
    Path(os.environ.get("LOCALAPPDATA", "")) / "Programs" / "WorkBuddy",
    Path(os.environ.get("PROGRAMFILES", "")) / "WorkBuddy",
    Path(r"D:\AppStoreSoftstore\WorkBuddy"),
    Path(r"D:\Program Files\WorkBuddy"),
]


def detect_install() -> Path | None:
    env = os.environ.get("WB_INSTALL")
    if env:
        p = Path(env)
        if (p / "resources" / "app.asar.unpacked").exists():
            return p
        print(f"警告：WB_INSTALL={env} 下没有 resources\\app.asar.unpacked，继续探测")
    for c in CANDIDATES:
        if c and (c / "resources" / "app.asar.unpacked").exists():
            return c
    try:                                   # 从运行中的进程反查，最可靠
        import subprocess
        out = subprocess.run(
            ["powershell", "-NoProfile", "-Command",
             "(Get-Process WorkBuddy -EA SilentlyContinue | Select-Object -First 1).Path"],
            capture_output=True, text=True, timeout=10).stdout.strip()
        if out and Path(out).exists():
            return Path(out).parent
    except Exception:
        pass
    return None
```

进程反查要放在注册表/快捷方式探测之前 —— 它给的是真值，不必猜。

---

## P1-2 封条和备份绑在脚本目录，同机多副本各说各话

实测：`D:\workbuddy-pojia`（真机部署）里 22 个靶点全"已装载"；同一时刻在新克隆的 `_pojia_ref` 里跑 `status`，22 个全报"未装载"。两份脚本看的是同一批文件，结论完全相反。

这个设计便携，但和 P0-1 撞在一起就成了事故。两条改法选一条：

- **加 `--state-dir`**，默认 `%USERPROFILE%\.workbuddy\pojia\`，封条跨副本共享 → 多副本无害。
- **或者保留现设计，但 `apply` 前强制检测**：`seal.json` 不存在且任一靶点已是目标态 → 拒绝执行（即 P0-1(c)）。

建议两条都做：宁可多一道闸。

---

## P1-3 没有 dry-run

改 22 个文件（含安装目录、含人格文件）之前没法预览改什么。加 `--dry-run` 成本极低：

```python
sub.add_parser("apply").add_argument("--dry-run", action="store_true")
cmd_apply 里 p.write_bytes(after) 附近：
    if a.dry_run:
        print(f"  [dry] {layer:<2} {tgt['name']:<38} {len(after)-len(before):+6d} 字节")
        continue
```

---

## P1-4 verify --runtime 的长度对账会误判

`pojia.py:420-431` 用 `systemPrompt` 长度差判定是否生效。实测本机（完整装载态）：

```
基线 : systemPrompt=43827 vars=21093 @ 19:41:24  (craft)
当前 : systemPrompt=42284 vars=18997 @ 20:15:30  (craft)
人格/vars 增量 -2096 字；systemPrompt 增量 -1543 字
```

完整装载却显示负增量。因为 `systemPrompt` 长度同时受模式、挂载 MCP 数、技能数、工具表影响，两个会话环境不完全相同就不可比。现在的输出会让人误判成"装失败"。

改法：对账时把两边 `mode` 一起打出来，`mode` 不同或 `hasDeclaredMcp` 不同就明确标注"不可比，请看 trace"。

```python
if base.get("mode") != now.get("mode"):
    print(f"  判定 : 模式不一致（{base.get('mode')} → {now.get('mode')}），长度差不可比，请用 trace 验收")
    return ...
```

---

## P2 清单

| # | 位置 | 问题 | 修法 |
|---|---|---|---|
| 1 | `pojia.py:193-194` | `persona_dir()` 多账号时取 `sorted(glob)[0]`，可能选错人 | 改按 mtime 倒序取最新，并用 `app-config.json` 里的 userId 交叉校验目录名 |
| 2 | `pojia.py:362` | seal 里存 `prev_value`（用户原来的自定义指令全文） | 只存 `sha256` + 长度。封条可能被同步/上传，不必留明文 |
| 3 | `pojia.py:389` | `save_seal` 只在成功路径调用 | 见 P0-1(d) |
| 4 | `tools/check_backup.py:9` 等 5 个 | `open("seal.json")` 依赖 cwd，`cd tools` 再跑就崩 | 改成 `Path(__file__).resolve().parents[1]/"seal.json"`，与 README 里"必须在根目录跑"的免责说明一起删掉 |
| 5 | `pojia.py:437-445` | trace 探针是硬编码中文串（`"环境与交付偏好"`），改载荷措辞就永远命中不了 | 探针从 `seal.json` 里各层备份与当前文件的差异段自动提取前 40 字符（假阳性见 P0-4） |
| 6 | `pojia.py:212-216` | `runtime_ref()` 只在最近 60 个日志文件里找，日志轮转后拿不到基线 | 放宽到"按日期目录倒序，最多 5 天" |
| 7 | whole | 无 `--version`，seal 里也没记脚本版本 | `seal["tool_version"]`，`apply` 时与当前不一致就提示"载荷可能已变，建议 restore 后重装" |
| 8 | whole | `structure_check.py` 是独立脚本，`verify` 不查模板结构 | 并成 `verify --struct`，检查 `{% %}` / `{{ }}` 成对 + 占位符未丢失。这是**唯一能在装载后立刻发现"模板改坏了"的检查**，应当默认跑 |
| 9 | `pojia.py:59` | `{{ productName }}` 在 `PRODUCT_IDENTITY` 里保留模板变量，但没有测试证明渲染后不残留 | 加一条 `verify --struct` 断言：改装后的 tpl 里 `{{`/`}}` 计数必须与原厂一致 |
| 10 | `.gitignore` | 忽略 `seal.json` 是对的（含原厂指纹），但没给用户"如何导出/迁移封条"的路子 | 加 `export-seal` 子命令，把 `seal.json` 里的路径/哈希导出（不含备份内容），便于换机诊断 |
| 11 | README | 称 L7 是"新建"，实测 `created=False, delta=-193`（机器上本来就有同名技能，走的是覆盖） | 文档已改（附录 A 已注明两种情形） |
| 12 | whole | 没有失败注入测试 | 建议加 `tests/test_render.py`：把 `render_append` 连调两次断言幂等、`_in_place` 探针在 CRLF/LF 下都命中、`render(policy)` 对无 `<content_policy>` 的模板走追加分支 |

---

## 只修四处的话，修这四个

1. **P0-5**：L8 改指插件缓存。不修这条，前面 33 个靶点全绿也是零效果——本机就是这么白跑了一轮。
2. **P0-4**：`cmd_trace` 只解析 `generation` span，另加 `inspect`。假的验收比没有验收更坏。
3. **P0-1**：`_in_place` 探针 + 封条缺失拒绝 apply。掐死「重复追加 + 永久失去还原」。
4. **P0-2 + P1-1**：安装目录探测 + 结构断言。别人能不能装上的分水岭。

以上四条已在 v3 落地，见下面回归记录。

---

## v3 回归记录

改动文件：`D:\workbuddy-pojia\pojia.py`（21,602 → 36,984 字节），备份在 `pojia.py.bak-20261029-202527`。

### 隔离环境（`%TEMP%\pjlab3`：假安装目录 + 假插件缓存 3 模式 × 2 版本 + 假人格目录）

| 场景 | 命令 | 结果 |
|---|---|---|
| 首次装载 | `apply` | 28 个靶点写入（fake 环境的 L8 是 3+6=9，故 28 而非 34） |
| 幂等重跑 | `apply` | 0 个写入，28 个已是目标态 |
| 预览不落盘 | `apply --dry-run` | 0 个写入，文件与 seal 均未变 |
| 封条丢失后重装 | 删 seal → `apply` | **拒绝执行，退出码 3**，人格段落仍只有 1 段 |
| 强行重建 | `apply --force` | 0 写入 28 认领，**未重复追加**（`_in_place` 生效） |
| 安装目录指错 | `WB_INSTALL=D:\nonexist` → `apply` | **退出码 2**，不再静默回退 |
| 还原 | `restore` | 28 个还原，偏好块计数归 0，`SKILL.md` 被删除，缓存文件回原厂 |
| 无封条校验 | 删 seal → `verify` | 退出码 1 |

### 真机（`D:\workbuddy-pojia`，34 靶点全装载）

```
$ python pojia.py apply --dry-run
[dry-run] 将写入 0 个靶点，34 个已是目标态，0 个备份缺失。未改动任何文件。
seal.json 未被改动 ✅

$ python pojia.py inspect
样本：20 份请求体（trace_eb423180....jsonl，10-29 20:28:50）
L8/L1 新policy     20 / 20
L8/L1 旧policy      0 / 20
判定：L1/L8 已进入请求（新 policy 在，旧 policy 不在）。
退出码 0
```

改缓存文件之前 `inspect` 的对应输出是 `新 0 / 44`——这就是 P0-5 的原始症状，现在闭环了。

### 仍未做

- `--state-dir`（P1-2）：用「检测到已改装态就拒绝」代替，够用。
- `structure_check.py` 并入 `verify --struct`（P2-8）：模板结构体检还得单独跑。
- `tools/*.py` 的 cwd 依赖（P2-4）：没改，README 里注明「必须在根目录跑」。
- 单元测试（P2-12）：本次验证靠 shell 脚本 + 真机 dry-run，没有落成 `tests/`。要长期维护的话建议补上 `_in_place` 的 CRLF/LF 双分支和 `render(policy)` 的无标签分支。

---

## v3.1 · 2026-10-29 · 安装体验（不改载荷，只改"别人能不能装上"）

v3 的装载逻辑没动，改的是入口与自检。目标：把「读 README 敲六条命令 + 自己设环境变量」压成「双击一个 bat」。

### 改了什么

| 位置 | 改动 | 解决的问题 |
|---|---|---|
| `pojia.py` | 新增 `setup`：六步向导（版本 → 目录 → 权限 → 进程 → 靶点 → 预演+装载） | 首次安装零参数，装错目录当场停 |
| `pojia.py` | 新增 `doctor`：15 项自检，关键项失败退出码 2 | 远程求助时贴一段输出即可定位 |
| `pojia.py` | 新增 `pojia.config.json`，解析顺序 `WB_INSTALL → config → 常见路径 → 进程反查` | 不再要求用户配环境变量 |
| `pojia.py` | `EXPLICIT_INVALID` 取代 `ENV_INVALID`：env 与 config 两个显式来源都记录原因 | 显式指错时给出更准的话术 |
| `pojia.py` | `apply` 前查 `WorkBuddy.exe`，在跑就告警（`--allow-running` / `--yes` 可越过，dry-run 不拦） | 消除"装了没生效"的第一大来源 |
| `pojia.py` | `dw()` / `pad()`：按东亚字符宽度对齐表格 | 中文表格列错位 |
| `install.bat` `doctor.bat` `check.bat` `restore.bat` `_find_py.bat` | 纯 ASCII + CRLF；`chcp 65001`；`_find_py.bat` 找 3.9+ 并回传 `PY` | 双击即装，不用记命令；无 Python 时给 winget 命令 |
| `README.md` | 重写成「三步装完 + 退出码对照 + 装不上怎么查 + 哪些文件不能删」 | 原版按命令讲，非开发用户读不下去 |
| `DETAILS.md` | 新增 §0（setup 六步与解析优先级）、§1.7（bat 闪退 / 找不到 Python 对照表）；§1.2 §1.5 §1.6 改用 doctor 与 config | 排查路径与实现一致 |
| `.gitignore` | 忽略 `pojia.config.json` | 每台机器路径不同，不该进仓库 |

### 回归记录（真机 + 临时副本）

| # | 场景 | 命令 | 结果 |
|---|---|---|---|
| 1 | 真机全装载态 | `setup --dry-run --yes` | 退出码 0，`将写入 0 个靶点 / 34 已是目标态`，未生成 `pojia.config.json` |
| 2 | 真机全装载态 | `setup --yes` | 退出码 0，0 写入；生成 config `{"install": "D:\\AppStoreSoftstore\\WorkBuddy"}` |
| 3 | 新克隆（无 seal） | `setup --dry-run --yes` | 退出码 3，命中"已是改装态但无封条"拦截，未写任何文件 |
| 4 | 新克隆 + 上级目录有 seal | `setup --yes` | 输出 `已复用 D:\tmp\seal.json`，随后 0 写入，退出码 0 |
| 5 | 显式目录不存在 | `WB_INSTALL=C:\nonexistent\WorkBuddy status` | 显示"显式配置无效（WB_INSTALL=…），这是自动探测结果"，回落到正确目录 |
| 6 | `--install` 指错 | `setup --install C:\nope --yes` | 退出码 2，指出缺 `resources\app.asar.unpacked` |
| 7 | 程序在跑时 dry-run | `apply --dry-run` | 只告警不阻塞，退出码 0 |
| 8 | 四个 bat 实跑 | `install.bat --dry-run`、`doctor.bat`、`check.bat` | 中文输出正常，退出码 0；`check.bat` 打出 `34 一致 / 0 异常` 与 `[OK]` |
| 9 | bat 传参链路 | `restore.bat --bogus` | argparse 先拒（退出码 2），未触碰任何文件 |
| 10 | Python 3.9 语法 | `D:\conda\python.exe -m py_compile pojia.py` | 通过（3.9.13） |

`restore` 未做真实还原测试（会动真机全装载态），只验了传参链路——需要时在隔离目录用假靶点补。

### 补丁：路径自适应 + 双击即装（同日）

| 改动 | 说明 |
|---|---|
| `detect_install` 六层探测 | `WB_INSTALL` → `pojia.config.json` → 标准安装位 → 卸载注册表（HKCU/HKLM × 64/32，`DisplayIcon` / `InstallLocation`）→ 运行中进程（`wmic`，退 PowerShell）→ 本地盘两层扫描。删除写死的 `D:\AppStoreSoftstore\WorkBuddy` 默认值 |
| `coerce_install` | exe / `...\resources` / `...\app.asar.unpacked` / 引号 / `%VAR%` / `file:///` 都往上找，最多四层 |
| `EXPLICIT_STALE` | 配置里的路径失效时**继续往下探测**并提示"已自动改用 X"，只有全部失败才用 `EXPLICIT_INVALID` 拦 |
| `resolve_user_dir` | 数据目录自适应：`WB_HOME` / `WORKBUDDY_HOME` → 配置 `user_dir` → `~/.workbuddy` → `%APPDATA%` / `%LOCALAPPDATA%` / `~` 下的 `workbuddy` |
| `_fill` + `{SCOPE}` | 载荷里唯一的绝对路径改为按 `HERE/scope/redteam-scope.md` 填充；本机渲染结果与原写死字节一致（`apply --dry-run` 仍 0 写入） |
| `backup_path` | 跨盘 / UNC 也不撞名，取不到相对路径时退化为哈希目录 |
| `install.bat` | 改为 `setup --yes --close`：零提问、自动关程序（3 秒倒计时），双击即装完 |
| `_find_py.bat` | 追加便携版 `.\python\python.exe` 与 `%LOCALAPPDATA%\Programs\Python\Python3*` |
| `tools/_locate.py` | `check_backup` / `char_delta` / `structure_check` 改为从脚本位置上找 `seal.json`，不再依赖 cwd |
| `README.md` | 压到一屏：三步表 + 三个常见错误 + 还原 |

新增回归：

| 场景 | 结果 |
|---|---|
| 无 `pojia.config.json` 时的探测 | 走注册表命中 `注册表：WorkBuddy 5.9.3` → `D:\AppStoreSoftstore\WorkBuddy` |
| 配置指向失效路径 | `status` 显示「原配置已失效 … 已自动改用上面这个」，实际走注册表命中（探测链路同下一条） |
| `--install` 贴 exe 路径 | 接受并归一到安装目录 |
| 三支 tools 从 `/tmp` 与 `tools/` 运行 | 均正常（`备份完整性: ok` / `结构体检: 全部通过`） |
| 载荷字节 | `apply --dry-run` 仍 `0 个靶点写入，34 个已是目标态` |
| `install.bat --dry-run` | 中文正常、零提问、退出码 0（未触发关闭程序） |
