# pojia-workbuddy-win

**双击 `install.bat` 就装完。** 不用敲命令，不用配环境变量。

装之前只有一件事：WorkBuddy **桌面版至少启动过一次**（脚本要读它启动时生成的插件缓存）。

## 三步

| # | 做什么 | 看到什么算成功 |
|---|---|---|
| 1 | 双击 **`install.bat`** | 最后一行 `装完了。接下来三步…` |
| 2 | 完全退出 WorkBuddy，再打开，随便发一句话 | — |
| 3 | 双击 **`check.bat`** | `[OK] Installed and effective.` |

第 2 步不能跳：模板是**启动时**读进内存的，只新开对话读不到。

`install.bat` 自己会干完这些，中途不需要回答任何问题：

```
找 WorkBuddy 装在哪   注册表 → 运行中进程 → 标准安装位 → 扫本地盘
记住路径              pojia.config.json，下次不用再找
关掉正在运行的程序     3 秒倒计时，Ctrl+C 可取消
体检靶点              L8/L1/L2 数量对不上就直接停，不乱写
预演 → 写入           改哪个文件、增删多少字节，逐个打印
```

## 没装 Python 3.9+

双击后会提示。照这行装完，**关掉窗口重新双击**：

```
winget install -e --id Python.Python.3.12
```

离线机器：装 [python.org](https://www.python.org/downloads/windows/) 的安装包，勾上 *Add python.exe to PATH*。

## 装不上

双击 **`doctor.bat`**，把输出贴出来。绝大多数是这三种：

| 现象 | 处理 |
|---|---|
| `[!] Python 3.9+ not found` | 装 Python，关窗口重开再双击 |
| `安装未完成，退出码 4` | 装在 `C:\Program Files` 下：右键 `install.bat` → 以管理员身份运行 |
| `退出码 3` | 这台机器以前装过，但目录里缺 `seal.json`：找回它放进来重跑；找不到就 `install.bat --force`（之后还原不回原厂） |

其余报错按 `DETAILS.md` 第 1 节逐条查。

## 想还原

双击 **`restore.bat`**，然后退出并重启 WorkBuddy。

## 想自己来

```
install.bat --dry-run     只体检，一个文件都不改
python pojia.py setup     交互式向导（会逐个问你）
python pojia.py status    看每层状态 + 靶点合计
python pojia.py doctor    环境自检，15 项
python pojia.py restore   还原
```

`WB_INSTALL` 环境变量仍然有效（优先级最高），装在哪就填哪：`D:\你的\WorkBuddy`。贴 exe 路径、`...\resources` 也行，脚本会往上找。

目录结构、八层靶点表、排查手册 → `DETAILS.md`；代码审查与实测记录 → `REVIEW.md` / `VERIFY.md`。

## License

MIT
