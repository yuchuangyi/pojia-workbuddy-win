# pojia-workbuddy-win · 安装

Windows 桌面版 WorkBuddy 的提示词层装载器。三步：`status` 看 → `apply` 装 → `inspect` 验。

## 1 前置

- WorkBuddy **桌面版**（不是网页版），确认安装目录：

  ```powershell
  (Get-Process WorkBuddy -EA SilentlyContinue | Select-Object -First 1).Path
  ```

  返回 `D:\AppStoreSoftstore\WorkBuddy\WorkBuddy.exe` 这类路径，**父目录**就是安装目录。安装目录里必须有 `resources\app.asar.unpacked`，不是 `%APPDATA%\WorkBuddy` 那种数据目录。

- Python 3.9+。纯标准库，**不用 pip install**。

  ```powershell
  python --version
  ```

- **完全退出 WorkBuddy**（任务管理器确认进程没了）。程序开着改，`customPrompt` 那一层会被它退出时重写掉。

## 2 选一个目录放脚本，之后别换

```powershell
cd D:\
git clone https://github.com/yuchuangyi/pojia-workbuddy-win.git workbuddy-pojia
cd D:\workbuddy-pojia
```

脚本把 `seal.json`（封条）和 `backup\`（原厂备份）存在自己所在目录。这两个在 `.gitignore` 里，`git clone` 不带过来——**一台机器只留一份工作副本，别另克隆第二份再跑 `apply`**（会被拒绝执行，见第 7 步）。

## 3 指定安装目录

脚本默认 `D:\AppStoreSoftstore\WorkBuddy`，其他机器要显式指定：

```powershell
$env:WB_INSTALL = "C:\Users\<你>\AppData\Local\Programs\WorkBuddy"
```

只在当前窗口有效。要长期生效就写进用户环境变量（写完重开窗口）：

```powershell
[Environment]::SetEnvironmentVariable("WB_INSTALL", "C:\Users\<你>\AppData\Local\Programs\WorkBuddy", "User")
```

Git Bash 里用 `export WB_INSTALL="..."`。

## 4 先看

```powershell
python pojia.py status
```

要确认三件事：

```
安装目录   : D:\AppStoreSoftstore\WorkBuddy          ← 是不是你的
插件缓存   : C:\Users\<你>\.workbuddy\plugins\cache\workbuddy-builtin  (存在)   ← 必须是"存在"
人格目录   : C:\Users\<你>\.workbuddy\user-<id>-personal          ← 必须带长串 id
...
靶点合计 34 个（L0×1 + L8×15 + L1×11 + L2×2 + 人格×4 + L7×1）
```

**「靶点合计」本机是 34**。数字比这个小很多 → 安装目录指错了，或者 WorkBuddy 从没启动过（插件缓存是启动后才生成的），先启动一次再跑。

## 5 装

```powershell
python pojia.py apply --dry-run    # 先看会改什么，不写任何文件
python pojia.py apply              # 确认没问题再真装
```

每个靶点一行 `[Lx] 名字 ±字节`，末尾：

```
装载完成：34 个靶点写入，0 个已是目标态。
```

重复跑一次会是 `0 个靶点写入，34 个已是目标态`，这是正常的（幂等）。

## 6 生效 + 验收

```powershell
# 完全退出再启动 —— L0 和 L8 都是启动时加载，只新开对话不够
Get-Process WorkBuddy -EA SilentlyContinue | Stop-Process -Force
```

启动 WorkBuddy，新开一个对话说句话，然后：

```powershell
python pojia.py inspect
```

```
样本：20 份请求体（trace_xxx.jsonl，10-29 20:28:50）
L8/L1 新policy     20 / 20
L8/L1 旧policy      0 / 20
判定：L1/L8 已进入请求（新 policy 在，旧 policy 不在）。
```

退出码 `0` 才算装好。`3` = 请求里还是原厂 policy，回去查第 4 步那个插件缓存路径。

## 7 日常

| 情况 | 处理 |
|---|---|
| WorkBuddy 升级后 | `apply`（在新版本基础上重算） |
| 应用内改过设置 | 退出程序 → `apply` → 启动 |
| 想还原 | `python pojia.py restore`，然后退出重启用 |
| `apply` 报「封条缺失，但靶点已是改装态」 | 找回原来那份 `seal.json` 复用；确认要重来就加 `--force`（拿不到原厂基线，以后还原不了） |

## 命令一览

```powershell
python pojia.py status              # 每层状态 + 靶点合计
python pojia.py apply [--dry-run]   # 装载（--dry-run 只预览）
python pojia.py verify [--runtime]  # 封条校验
python pojia.py inspect             # 载荷有没有真的进请求（唯一可信验收）
python pojia.py trace               # 各 trace 的命中表
python pojia.py restore [--force]   # 还原到原厂
```

故障排查、目录速查、八层靶点表、为什么文件里不能加标记，见 `DETAILS.md`；代码审查与回归记录见 `REVIEW.md`。

## License

MIT
