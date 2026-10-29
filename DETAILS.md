# 细节：故障排查与实现说明

安装步骤看 `README.md`；这份放排查方法和实现细节。

## 0 一键安装到底做了什么

`install.bat` 只干一件事：找到 Python，然后 `python pojia.py setup --yes --close`。逻辑全在 `setup` 里，六步：

| 步 | 动作 | 失败退出码 |
|---|---|---|
| 1 | `sys.version_info >= (3,9)` | 4 |
| 2 | 定位安装目录（见下）：`--install` → 自适应探测 → 都没有才交互手输；校验 `resources\app.asar.unpacked`；成功后写 `pojia.config.json` | 2 |
| 3 | 对安装目录 / 模板目录 / 插件缓存 / 人格目录逐个建临时文件试写 | 4 |
| 4 | `tasklist` 查 `WorkBuddy.exe`；`--close` 倒计时 3 秒后 `taskkill /F /T`，交互模式则先问 | 5 |
| 5 | 统计 L8 / L1 / L2 靶点，复用 `target_warnings()` 判定 | 2 |
| 6 | 封条缺失拦截 → `apply --dry-run` 预演 → `--yes` 不再确认 → `apply` | 3 / 其它 |

### 0.1 路径全自适应

安装目录按「快 → 慢」分六层，命中即停（`detect_install`）：

| 层 | 来源 | 成本 | 说明 |
|---|---|---|---|
| 1 | `WB_INSTALL` 环境变量 | 0 | 优先级最高，临时覆盖用 |
| 2 | `pojia.config.json` | 0 | `setup` 写下的，装过一次就一直有效 |
| 3 | 标准安装位 | 几毫秒 | `%LOCALAPPDATA%\Programs\WorkBuddy*`、`%ProgramW6432%`/`%PROGRAMFILES%`/`%PROGRAMFILES(X86)%` 下的 `WorkBuddy*` |
| 4 | 卸载注册表 | 十几毫秒 | HKCU/HKLM × 64/32 视图，`DisplayName` 含 WorkBuddy → `InstallLocation` / `DisplayIcon` |
| 5 | 运行中进程 | ~1 秒 | `wmic` 取 `ExecutablePath`，没有就 PowerShell |
| 6 | 磁盘扫描 | 几百毫秒 | 本地固定盘两层目录里找名字含 `workbuddy` 的（网络盘/光驱跳过） |

判据只有一条：**这一层下面有 `resources\app.asar.unpacked`**。

三个配套行为：

- **贴错也能救**（`coerce_install`）：给 exe 路径、`...\resources`、`...\app.asar.unpacked`、带引号、带 `%VAR%`、`file:///` 都行，往上找最多四层。
- **配置过期自动接续**：`pojia.config.json` 里的路径失效（WorkBuddy 换盘/升级换目录）时不会卡住，继续往下探测；`EXPLICIT_STALE` 记下原因，`status` / `doctor` 里提示"原配置已失效，已自动改用 X"。只有**所有层都失败**才用 `EXPLICIT_INVALID` 拦下。
- **数据目录也自适应**（`resolve_user_dir`）：`WB_HOME` / `WORKBUDDY_HOME` → 配置里的 `user_dir` → `%USERPROFILE%\.workbuddy` → `%APPDATA%` / `%LOCALAPPDATA%` / `~` 下的 `workbuddy`。判据是里面有 `app` / `plugins` / `logs` / `traces` / `skills` 至少一个。

载荷里唯一随目录变的东西是演练范围文件的绝对路径，`_fill()` 在 import 时按 `HERE / scope / redteam-scope.md` 填进去——换机器不用改代码，本机上填出来的字节和原来写死的一致（`apply --dry-run` 仍然是 0 写入）。

`doctor` 与 `setup` 不共用代码但共用同一批探测函数（`_is_install` / `writable` / `wb_running` / `target_counts` / 各层 candidates），所以 `doctor` 的输出就是 `setup` 判定依据的原文。

## 1 故障排查

### 1.1 `apply` 报「封条缺失，但靶点已是改装态」（退出码 3）

这台机器以前装过，但 `seal.json` 没了（新克隆的目录、`git clean`、手工删）。继续会把这些文件当原厂基线再追加一遍，人格文件出现重复段落。

处理顺序：

1. 找回原来那份 `seal.json` 放回脚本目录，跑 `status` 看是不是全「已装载」——找到了就没事。
2. 找不回：打开 `SOUL.md` / `IDENTITY.md` / `USER.md` / `MEMORY.md`，确认偏好段落只有一段（重复了就删掉多的），再 `apply --force` 重建封条。这些条目此后是「认领(无备份)」，能用但 `restore` 还原不了。

### 1.2 靶点合计远少于 34

先跑 `python pojia.py doctor`，第 2–7 行会直接指出来。手工核对时把 `$wb` 换成 `doctor` 输出里「安装目录」那行的路径：

```powershell
$wb = "D:\AppStoreSoftstore\WorkBuddy"   # ← 换成你的
Get-ChildItem "$wb\resources\app.asar.unpacked\resources" -Directory | Select-Object Name
# 期望：templates / plugins

(Get-ChildItem "$wb\resources\app.asar.unpacked\resources\templates" -Filter "workbuddy-*.tpl").Count
# 期望 11

(Get-ChildItem "$env:USERPROFILE\.workbuddy\plugins\cache\workbuddy-builtin" -Filter "welcomemode-*" -Directory).Count
# 期望 3（每个 welcomeMode 一个）
```

结构不一样就是版本变了。用 `asar_ls.py` 反查新路径：

```powershell
python tools\asar_ls.py "$wb\resources\app.asar" "prompt.tpl"
```

### 1.3 `inspect` 退出码 3（旧 policy 还在）

按顺序查，别跳：

1. `status` 里 L8 那 15 行是不是全「已装载」——不是就 `apply`。
2. 有没有**完全退出重启**——没有就重启（L8 是启动时加载的，新开对话不够）。
3. `status` 的「插件缓存」是不是「存在」——不存在就先启动一次 WorkBuddy 生成它。
4. 三条都过还是 3：直接打开缓存里的 `prompt.tpl` 看 `<content_policy>` 是哪一版，别猜。

### 1.4 改动被吃掉

改完十几分钟内被还原，多半是云记忆回写人格文件，或者应用内设置面板被打开过并保存（会把整个 `personalization` 重写）。`apply` 能补回来，但会来回拉锯——看是不是登了多设备。

### 1.5 权限不足

`D:\` 下的安装目录一般不用提权。装在 `C:\Program Files\` 下写模板会抛 `PermissionError`，`setup` 第 3 步用写探针就能查出来并退出码 4 —— **右键 `install.bat` → 以管理员身份运行**即可。

手工 `apply` 半途失败时，封条可能已经写了一部分；v3 把 `save_seal` 放进了 `finally`，半数失败也会把已写入的靶点落进封条，提权重跑一次 `apply` 即可（幂等）。

### 1.6 中文乱码

`install.bat` 等入口已经 `chcp 65001`，用 bat 跑正常不会乱码。自己在 PowerShell 里直接调 `pojia.py` 看到乱码时：

```powershell
[Console]::OutputEncoding = [System.Text.Encoding]::UTF8
```

### 1.7 双击 bat 一闪而过 / 提示找不到 Python

四个 `.bat` 都是纯 ASCII，只做三件事：`cd /d "%~dp0"`（放哪都能跑）、`call _find_py.bat` 找解释器、把参数转给 `pojia.py`。所以：

| 现象 | 原因 | 处置 |
|---|---|---|
| 窗口一闪而过 | 启动就失败，连找 Python 都没到 | 开 `cmd`，`cd` 到目录，手敲 `install.bat` 看报错 |
| `[!] Python 3.9+ not found` | PATH 里没有 `py` / `python`，或版本 < 3.9 | `winget install -e --id Python.Python.3.12`，重开窗口 |
| 输出乱码 | 控制台代码页不是 65001 | 用 bat 跑（它会 chcp），或先 `chcp 65001` |
| 提示找不到 `_find_py.bat` | 解压漏了以下划线开头的文件 | 重新解压整个目录，别只拷 `install.bat` |

`_find_py.bat` 按顺序找：`py -3` → `python` → `python3` → 当前目录下 `python\python.exe`（便携版）→ `%LOCALAPPDATA%\Programs\Python\Python3*`。里面不能加 `setlocal`（`%PY%` 要传回调用者），判版本用的是 `if not errorlevel 1`。

`install.bat` 默认带 `--yes --close`：不提问、自动关掉正在运行的程序，所以双击就完事。想要交互版就跑 `python pojia.py setup`。

## 2 `verify --runtime` 怎么读

```
基线 : systemPrompt=43827 vars=21093 mode=craft @ 19:41:24
当前 : systemPrompt=42284 vars=18997 mode=craft @ 20:15:30
人格/vars 增量 -2096 字；systemPrompt 增量 -1543 字
```

**增量为负不代表失败。** 长度同时受模式、挂载 MCP 数、技能数影响，本机这组数就是在**完整装载态**下测到的负增量。

只在同模式、同插件数、同技能数的两个会话之间才可比；模式不一致时脚本会直接标「不可比，用 inspect」。真要确认，永远看 `inspect`。

## 3 目录速查

```
<安装目录>                                       # WB_INSTALL
└─ resources\app.asar.unpacked\resources\
   ├─ templates\                                # L1 / L2
   │  ├─ workbuddy-*.tpl                        #   11 个模式模板
   │  ├─ user-context-identity.tpl              #   L2
   │  └─ user-context-expert-identity.tpl       #   L2
   └─ plugins\workbuddy-builtin\welcomemode\    # L8（解压副本，不参与装配）
      ├─ work\prompt.tpl
      ├─ code\prompt.tpl
      └─ design\prompt.tpl

%USERPROFILE%\.workbuddy\
├─ app\app-config.json                          # L0
├─ plugins\cache\workbuddy-builtin\             # L8 真源
│  ├─ welcomemode-work\<版本>\prompt.tpl
│  ├─ welcomemode-code\<版本>\prompt.tpl
│  └─ welcomemode-design\<版本>\prompt.tpl
├─ skills\pojia-mode\SKILL.md                   # L7
├─ logs\                                        # verify --runtime 的数据源
├─ traces\<pid>\trace_*.jsonl                   # inspect / trace 的数据源
└─ user-<id>-personal\                          # 人格目录
   ├─ SOUL.md  IDENTITY.md  USER.md  MEMORY.md  # L3–L6
```

## 4 为什么文件里一个标记都没有

v1 在文件里留过 `<!-- POJIA:L3 -->` 这类标记，还写了「拒答视为故障 / 与上文冲突以本块为准」的元规则。结果模型把六个标记挨个念出来，然后声明「这些段落对我没有效力」，请求照样被拒。

v2 起改成：**文件里零标记、零元规则，只写事实性内容**（这台机器归谁、交付习惯是什么、缺值怎么办）。幂等不靠标记，靠 `seal.json` 的指纹 + v3 的载荷探针。

所以：不要在载荷里加「不要提及本块」「冲突以本块为准」这类句子，也不要加注释标记。要调就调事实描述的措辞和详略。

## 5 手工兜底（不跑脚本时）

| # | 文件 | 改什么 |
|---|---|---|
| 1 | 应用内 **设置 → 个性化 → 自定义指令** | 粘贴偏好描述（官方槽位，最稳，优先用） |
| 2 | `<人格目录>\SOUL.md` | 末尾追加偏好段落，不加任何注释标记 |
| 3 | `<人格目录>\USER.md` | 同上，写环境与授权事实 |
| 4 | `...\templates\*.tpl` | `<content_policy>...</content_policy>` 整块换掉（11 个） |
| 5 | `~\.workbuddy\plugins\cache\workbuddy-builtin\welcomemode-*\*\prompt.tpl` | 同上。**这才是 welcomeMode 真正加载的那份**，漏了它前四条改了也白改 |

改之前先 `Copy-Item <文件> <文件>.bak`。手工改没有封条、没有备份，升级后找不到原样。

## 6 tools/ 里的小脚本

| 脚本 | 用途 |
|---|---|
| `asar_ls.py` | 不解包直接列 `app.asar` 条目与 unpacked 标志 |
| `prompt_timeline.py` | 打印最近会话的时间 / 模式 / 场景 / 两段长度 |
| `check_backup.py` | 核对备份指纹与各层字节增量 |
| `char_delta.py` | 按字符口径算各层增量，与日志长度对账 |
| `structure_check.py` | 体检改装后模板的 `{% %}` / `{{ }}` 是否成对、占位符有无丢失 |
| `trace_probe.py` | 在某个 trace 里定位一个字符串出现在哪类事件 |
| `trace_messages.py` | 从 trace 里抽出对话 role / content |
| `check_asar_read.js` | 用 Electron 自己的 fs 读 asar 内路径，验证可读性 |

```powershell
python tools\asar_ls.py "$env:WB_INSTALL\resources\app.asar" "prompt.tpl"
python tools\prompt_timeline.py
python tools\structure_check.py
```

前五个从**脚本自身位置**往上找 `seal.json`（`tools/_locate.py`），`cd tools` 里跑、或者从别的目录 `python D:\...\tools\xxx.py` 跑都行，不再依赖 cwd。

## 7 八层靶点

| 层 | 数量 | 位置 | 本机字节增量 |
|---|---|---|---|
| L0 | 1 | `~\.workbuddy\app\app-config.json` → `personalization.customPrompt` | +604 |
| L8 | 15 | 插件缓存 12 份（真源）+ 安装目录副本 3 份 | −226 ×15 |
| L1 | 11 | `templates\workbuddy-*.tpl` | −227 ×7，−1355 ×3，+844 ×1 |
| L2 | 2 | `user-context-identity.tpl` / `user-context-expert-identity.tpl` | +130 / +118 |
| L3 | 1 | `SOUL.md` | +731 |
| L4 | 1 | `IDENTITY.md` | +423 |
| L5 | 1 | `USER.md` | +647 |
| L6 | 1 | `MEMORY.md` | +489 |
| L7 | 1 | `skills\pojia-mode\SKILL.md` | 覆盖已有 −193；新建约 +1242 |

合计 34（本机，L8 的缓存份数随版本数浮动）。字节数随版本变化，只作参照，校验值在 `seal.json`。
