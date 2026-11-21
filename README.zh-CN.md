[English](README.md) | **简体中文**

# 🔓 HashWizard

[![Python](https://img.shields.io/badge/Python-3.8%2B-3fb950?logo=python&logoColor=white)](https://python.org) [![License: MIT](https://img.shields.io/badge/License-MIT-yellow)](LICENSE) [![Security](https://img.shields.io/badge/Category-Security-8b5cf6)](https://github.com/Leechuihui/HashWizard)

纯 Python 编写的交互式密码哈希破解工具——粘贴哈希，自动识别类型，用 hashcat 或内置零依赖引擎破解。跨平台。

直接把哈希粘贴到命令行——**再也不用手动创建 `hash.txt` 文件**。

- **交互式向导**：粘贴哈希 → 自动识别类型 → 选择后端 → 挑选字典 → 开始破解
- **hashcat 后端**：检测到本地 hashcat 时自动调用（GPU/CPU 加速）
- **纯 Python 后端**：内置 sha512crypt / sha256crypt / md5crypt 实现，多进程并行并实时显示进度——没有 hashcat 也能用
- **智能 potfile**：破解前先查已有结果——已破解的哈希立即返回，无需重复运行
- **跨平台**：Linux / Windows / macOS（Python 3.8+）

---

## 环境要求

- Python 3.8+（无需任何第三方包）
- 可选：[hashcat](https://hashcat.net/hashcat/)，用于 GPU/CPU 加速破解
- 可选：`bcrypt` 包（`pip install bcrypt`），用于纯 Python 后端支持 bcrypt 哈希

---

## 快速开始

### 1. 交互模式（推荐）

```bash
python3 hashcrack.py
```

你会被一步步引导操作：

```
========================================================
  HashWizard interactive cracking tool v2.0.0
  Paste hashes directly - no hash.txt needed
========================================================
Paste the hash(es) to crack (one per line, press Enter twice to finish, or Ctrl+D/Ctrl+Z):
> $6$PYikyu28$gaZOe5FUDn62MDPkhAwj8KnYdu4S1MZoT44AuehXiFtwGIToYRutVTVKnr66j0298FTWd55YIpEpIPOQMh.tB.
> 
Received 1 hash(es):
  [1] $6$PYikyu28$... (sha512crypt ($6$), hashcat mode 1800)

Auto-detected: sha512crypt ($6$) (hashcat mode 1800)
Use this mode? [y]> y
Backend: [1] hashcat (found: /usr/bin/hashcat)
Choose backend (1=hashcat recommended, 2=pure Python) [1]> 1
Wordlist: /usr/share/wordlists/rockyou.txt
...
[+] Cracked:
    $6$PYikyu28$... : s3cret
```

### 2. 单行命令模式

```bash
# 自动识别哈希类型，自动查找字典和后端
python3 hashcrack.py -h '$6$salt$hash...'

# 显式指定所有参数
python3 hashcrack.py -h '$6$salt$hash...' -m 1800 -w rockyou.txt -d 1

# 一次破解多个哈希
python3 hashcrack.py -h '$6$a$...' -h '$6$b$...' -w rockyou.txt
```

### 3. 查询以往破解结果

```bash
python3 hashcrack.py --show -h '$6$salt$hash...'
```

---

## 命令行选项

| 选项 | 说明 |
|---|---|
| `-h, --hash HASH` | 要破解的哈希（可重复传入）。省略时进入交互粘贴模式 |
| `-m, --mode MODE` | hashcat 模式编号（如 `1800` = sha512crypt）。省略时自动识别 |
| `-w, --wordlist FILE` | 字典路径（支持 `.gz`）。省略时自动搜索 rockyou.txt |
| `-d, --device N` | hashcat 设备编号（透传给 `hashcat -d`） |
| `--hashcat-path PATH` | 显式指定 hashcat 可执行文件路径 |
| `--pure` | 强制使用纯 Python 后端（跳过 hashcat） |
| `--threads N` | 纯 Python 后端的工作进程数（默认：CPU 核心数） |
| `--potfile PATH` | potfile 路径（默认：与工具同目录） |
| `--import-potfile PATH` | 将已有的 potfile（如 hashcat 的 `hashcat.potfile`）导入本工具的 potfile |
| `--show` | 仅查询 potfile 中的已破解结果，不执行破解 |
| `--quiet` | 关闭纯 Python 后端的进度输出 |
| `--selftest` | 运行内置算法自测后退出 |
| `--version` | 显示版本 |
| `--help` | 显示帮助 |

---

## 支持的哈希类型

| hashcat 模式 | 类型 | 自动识别前缀 |
|---|---|---|
| 1800 | sha512crypt (`$6$`) | `$6$` |
| 7400 | sha256crypt (`$5$`) | `$5$` |
| 500 | md5crypt (`$1$`) | `$1$` |
| 3200 | bcrypt (`$2a$/$2b$/$2y$`) | `$2a$`/`$2b$`/`$2y$`（纯 Python 后端需要 `pip install bcrypt`） |
| 0 | MD5 | 32 位十六进制字符 |
| 100 | SHA1 | 40 位十六进制字符 |
| 1000 | NTLM | 32 位十六进制字符（与 MD5 有歧义——交互模式下会要求确认） |

> 注意：32 位十六进制哈希存在歧义（MD5 还是 NTLM）。交互模式下会要求你确认；单行命令模式下默认按 MD5 (0) 处理——如需 NTLM 请使用 `-m 1000`。

只要安装了 hashcat，其他任何 hashcat 模式也都可以用（工具直接透传模式编号）。

---

## 后端

### hashcat 后端（快速，默认）

工具按以下顺序自动定位 hashcat：

1. `--hashcat-path` 参数
2. `HASHCAT_PATH` 环境变量
3. `PATH`（`hashcat` / `hashcat.exe`）
4. 当前目录和脚本所在目录

哈希会自动写入临时文件并在运行结束后删除——**你完全不必自己创建哈希文件**。工具还管理着自己的 potfile（`--potfile-path`），破解结果跨运行可查。

### 纯 Python 后端（回退方案，零依赖）

找不到 hashcat 时自动启用，也可用 `--pure` 强制使用。

- 在 Linux/macOS 上，sha512crypt/sha256crypt/md5crypt 使用系统 `crypt` 模块（glibc）——比纯 Python 实现快约 10 倍。
- 在 Windows 上（无 `crypt` 模块），使用依照官方 glibc/SHA-crypt 规范编写的内置实现。
- 多进程并行破解，实时显示进度。
- **警告**：sha512crypt 每个候选口令约需 5000 轮哈希运算。纯 Python 吞吐量只有每秒几千个候选——请用小字典，或安装 hashcat 进行高强度破解。

---

## Potfile

- 默认位置：与工具本身同目录（即 `hashcrack.py` 所在目录，就像 hashcat 把 potfile 放在可执行文件旁边一样）
- 格式：每行一条 `hash:password`（与 hashcat 的 potfile 格式兼容）
- 破解结果自动保存；`--show` 可直接查询而无需重新破解
- **智能预检**：破解前工具会先查 potfile——已破解的哈希立即返回，不再重复攻击
- 使用 `--import-potfile` 可从现有 hashcat potfile 迁移结果：

## 配置

工具将设置保存在 `hashcrack.ini` 中（与工具同目录）：

```
hashcat_path=D:\cybersec\hash 工具\Hashcat\hashcat.exe
```

- 首次输入（或通过 `--hashcat-path` 传入）hashcat 路径后会**自动记住**，之后每次运行无需额外参数即可找到 GPU 后端
- hashcat 查找顺序：`--hashcat-path` 参数 → `hashcrack.ini` → `HASHCAT_PATH` 环境变量 → `PATH` → 当前/脚本目录

```bash
python3 hashcrack.py --import-potfile /path/to/hashcat.potfile --show
```

---

## 示例

```bash
# 用 rockyou.txt 破解 sha512crypt 哈希（Linux，全自动查找）
python3 hashcrack.py -h '$6$salt$hash...'

# 同上，但强制使用 GPU 设备 1 并显示完整的 hashcat 命令
python3 hashcrack.py -h '$6$salt$hash...' -w rockyou.txt -d 1

# Windows：hashcat 不在 PATH 中
python hashcrack.py -h '$6$salt$hash...' -w rockyou.txt --hashcat-path "D:\cybersec\hash 工具\Hashcat\hashcat.exe"

# 没装 hashcat？纯 Python 多进程破解
python3 hashcrack.py --pure -h '$6$salt$hash...' -w small_dict.txt

# 破解 MD5 哈希（32 位十六进制字符）
python3 hashcrack.py -h '5f4dcc3b5aa765d61d8327deb882cf99' -w rockyou.txt

# 查看某哈希是否已破解过
python3 hashcrack.py --show -h '$6$salt$hash...'

# 验证内置算法实现
python3 hashcrack.py --selftest
```

---

## 自测

运行 `python3 hashcrack.py --selftest`，使用官方测试向量（来自 SHA-crypt 规范、glibc md5-crypt 以及一个真实 sha512crypt 样本）验证内置算法实现：

```
[*] Running algorithm self-tests ...
  sha512crypt Hello world!     OK
  sha512crypt rounds=10000     OK
  ...
  sha512crypt real-world (s3cret) OK
  MD5('123456')                OK
  SHA1('123456')               OK
[PASS] self-test all tests OK
```

---

## 故障排查

| 问题 | 解决办法 |
|---|---|
| `hashcat: No such file or directory` / 回退到纯 Python | 传 `--hashcat-path <路径>` 或设置 `HASHCAT_PATH` |
| hashcat 报错 `./OpenCL/: No such file or directory` | 工具会自动从 hashcat 自身目录运行它；如果手动调用 hashcat，请先 `cd` 到其所在目录 |
| hashcat 在 stdin 模式报 `Token length exception` | 已知的 hashcat 6.2.6 Windows stdin（`-`）bug；工具通过自动管理的临时文件规避 |
| `bcrypt` 模式失败 | `pip install bcrypt` |
| 纯 Python 破解太慢 | 属预期现象——安装 hashcat，或用 `--threads` 调整进程数 |
| Windows 控制台下中文/Unicode 路径乱码 | 在终端执行 `chcp 65001`，或设置 `PYTHONIOENCODING=utf-8` |

---

## 工作原理

- **哈希输入**：`-h` 参数或交互式粘贴（多行，空行 / Ctrl+D 结束）
- **类型识别**：基于前缀（`$6$` → 1800，`$5$` → 7400，`$1$` → 500，`$2x$` → 3200，十六进制长度 → MD5/SHA1/NTLM）
- **hashcat 后端**：子进程运行 `-m <mode> -a 0`，临时哈希文件，独立 potfile，然后用 `--show` 确认结果
- **纯 Python 后端**：`multiprocessing.Pool` 配合分块 `imap_unordered`，实时进度，Linux/macOS 上优先使用系统 `crypt` 模块

## 许可证

可自由用于教育和获授权的安全测试。只破解你拥有或明确获准测试的哈希。
