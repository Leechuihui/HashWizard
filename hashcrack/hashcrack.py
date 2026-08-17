#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
hashcrack v2.0 —— 交互式哈希破解工具
=====================================
哈希直接命令行/交互输入，无需手动创建 hash.txt。

特性:
  * 交互向导: 粘贴哈希 -> 自动识别类型 -> 选后端 -> 选字典 -> 破解
  * hashcat 后端: 优先调用本机 hashcat (GPU/CPU 加速)，临时文件自动管理
  * 纯 Python 后端: 无 hashcat 时自动降级，内置 sha512crypt/sha256crypt/md5crypt
    (Linux/macOS 自动用系统 crypt 模块加速)，多进程并行 + 实时进度
  * 自带 potfile (hash:password，兼容 hashcat 格式)，破解前自动查重
  * 跨平台: Linux / Windows / macOS (Python 3.8+，零第三方依赖)

用法:
  hashcrack                              # 交互模式
  hashcrack -h '<哈希>' -w rockyou.txt    # 一行命令
  hashcrack --pure -h '<哈希>' -w dict    # 强制纯 Python
  hashcrack --show -h '<哈希>'            # 查询已破解结果
  hashcrack --selftest                    # 算法自检
"""

import argparse
import gzip
import hashlib
import multiprocessing
import os
import re
import shutil
import subprocess
import sys
import tempfile
import time
from pathlib import Path

__version__ = "2.0.0"

# 当前语言设置
LANGUAGE = None

# 其他常量
B64T = "./0123456789ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz"

# 支持的语言列表
LANGUAGES = {
    "zh": "简体中文",
    "en": "English",
}

# 当前语言设置
LANGUAGE = None

# 翻译表（zh / en），缺失键回退到中文
TRANSLATIONS = {
    "zh": {
        "banner_title": "HashCrack 交互式破解工具 v{version}",
        "banner_lines": "哈希直接粘贴输入，无需 hash.txt\n完成一个任务后停留在本页，等待下一条指令",
        "welcome": "欢迎使用 HashCrack 交互式破解工具 v{version}",
        "continue_prompt": "继续下一个任务? (y/n): ",
        "exit_msg": "再见，感谢使用!",
        "exited": "已退出。",
        "input_empty": "[!] 输入不能为空",
        "paste_hint": "请粘贴要破解的哈希（每行一个，粘贴后按回车再按回车结束，或 Ctrl+D/Ctrl+Z 结束）：",
        "q_hint": "输入 q 直接退出",
        "hashes_received": "已收到 %d 个哈希：",
        "hash_list_item": "  [%d] %s  (%s, 模式 %s)",
        "unknown_mode": "未知",
        "auto_detect_fail": "[!] 无法自动识别哈希类型（请检查哈希格式是否正确），需要手动指定模式",
        "ask_mode": "请输入 hashcat 模式号",
        "invalid_mode": "[!] 模式无效，退出",
        "auto_detected": "自动识别: %s (hashcat 模式 %d)",
        "mode_num": "模式 %d",
        "md5_ntlm_choice": "32 位十六进制，可能是 MD5(0) 或 NTLM(1000)，选择模式",
        "confirm_mode": "确认使用该模式?",
        "multi_mode": "[!] 检测到多种哈希类型，需要手动指定模式",
        "no_hashcat_ask": "未找到 hashcat，请输入 hashcat 可执行文件路径（回车跳过，用纯 Python）",
        "hashcat_saved": "[*] 已记住 hashcat 路径: %s（下次自动使用，无需再输入）",
        "backend_choice": "后端: [1] hashcat (%s)  [2] 纯 Python，选择",
        "backend_hashcat_only": "后端: hashcat（模式 %d 仅 hashcat 支持）",
        "no_backend": "[!] 未找到 hashcat，且模式 %d 不被纯 Python 支持，退出。",
        "backend_pure": "后端: 纯 Python 多进程（未找到 hashcat）",
        "dict_found": "自动找到字典: %s，使用?",
        "ask_dict": "请输入字典路径",
        "ask_dict2": "未自动找到字典，请输入字典文件路径（如 rockyou.txt）",
        "dict_missing": "[!] 字典不存在: %s",
        "results_header": "破解结果：",
        "potfile_saved": "结果已保存到 potfile: %s",
        "no_result": "未破解出结果（字典已跑完或未命中）。",
        "no_result_tip": "可尝试：换更大的字典 / 加规则 / 用 hashcat 掩码攻击。",
    },
    "en": {
        "banner_title": "HashCrack Interactive Cracking Tool v{version}",
        "banner_lines": "Paste hashes directly, no hash.txt needed\nStays on this page after each task, waiting for the next command",
        "welcome": "Welcome to HashCrack interactive cracking tool v{version}",
        "continue_prompt": "Continue to next task? (y/n): ",
        "exit_msg": "Goodbye, thanks for using!",
        "exited": "Exited.",
        "input_empty": "[!] Input cannot be empty",
        "paste_hint": "Paste the hashes to crack (one per line; press Enter twice to finish, or Ctrl+D/Ctrl+Z):",
        "q_hint": "Type q to quit",
        "hashes_received": "Received %d hash(es):",
        "hash_list_item": "  [%d] %s  (%s, mode %s)",
        "unknown_mode": "unknown",
        "auto_detect_fail": "[!] Cannot auto-detect hash type (check the hash format), you must specify a mode manually",
        "ask_mode": "Enter hashcat mode number",
        "invalid_mode": "[!] Invalid mode, exiting",
        "auto_detected": "Auto-detected: %s (hashcat mode %d)",
        "mode_num": "mode %d",
        "md5_ntlm_choice": "32 hex chars: could be MD5(0) or NTLM(1000), choose a mode",
        "confirm_mode": "Use this mode?",
        "multi_mode": "[!] Detected multiple hash types, you must specify a mode manually",
        "no_hashcat_ask": "hashcat not found. Enter hashcat executable path (Enter to skip, use pure Python)",
        "hashcat_saved": "[*] Saved hashcat path: %s (will be used automatically next time)",
        "backend_choice": "Backend: [1] hashcat (%s)  [2] pure Python, choose",
        "backend_hashcat_only": "Backend: hashcat (mode %d is only supported by hashcat)",
        "no_backend": "[!] hashcat not found and mode %d is not supported by pure Python, exiting.",
        "backend_pure": "Backend: pure Python multiprocessing (hashcat not found)",
        "dict_found": "Wordlist found: %s, use it?",
        "ask_dict": "Enter wordlist path",
        "ask_dict2": "No wordlist found automatically. Enter wordlist file path (e.g. rockyou.txt)",
        "dict_missing": "[!] Wordlist does not exist: %s",
        "results_header": "Cracked results:",
        "potfile_saved": "Results saved to potfile: %s",
        "no_result": "No results (wordlist exhausted or no match).",
        "no_result_tip": "Try: a larger wordlist / rules / hashcat mask attack.",
    },
}


def _(key):
    """按当前 LANGUAGE 返回翻译文本；缺失键回退到中文。"""
    table = TRANSLATIONS.get(LANGUAGE) or TRANSLATIONS["zh"]
    return table.get(key, key)


def select_language():
    """询问用户选择语言并返回语言代码。"""
    while True:
        print("=" * 56)
        print("  HashCrack 语言选择")
        print("=" * 56)
        print("  请选择语言/语言：")
        print("  [1] 简体中文")
        print("  [2] English")
        print("=" * 56)
        choice = input("> ").strip().lower()
        if choice in ("1", "zh", "中文"):
            return "zh"
        elif choice in ("2", "en", "english"):
            return "en"
        print("  [!] 无效选择，请输入 1(中文) 或 2(English)。")

# 其他常量
MODE_NAMES = {
    0: "MD5", 100: "SHA1", 500: "md5crypt ($1$)", 1000: "NTLM",
    1600: "Apache $apr1$", 1800: "sha512crypt ($6$)",
    3200: "bcrypt ($2a/$2b/$2y$)", 7400: "sha256crypt ($5$)",
}
PURE_SUPPORTED = {0, 100, 500, 1000, 1800, 3200, 7400}

# crypt base64 分组顺序（None = 字面量 0，glibc 行为）
SHA512_B64 = [
    (0, 21, 42, 4), (22, 43, 1, 4), (44, 2, 23, 4), (3, 24, 45, 4),
    (25, 46, 4, 4), (47, 5, 26, 4), (6, 27, 48, 4), (28, 49, 7, 4),
    (50, 8, 29, 4), (9, 30, 51, 4), (31, 52, 10, 4), (53, 11, 32, 4),
    (12, 33, 54, 4), (34, 55, 13, 4), (56, 14, 35, 4), (15, 36, 57, 4),
    (37, 58, 16, 4), (59, 17, 38, 4), (18, 39, 60, 4), (40, 61, 19, 4),
    (62, 20, 41, 4), (None, None, 63, 2),
]
SHA256_B64 = [
    (0, 10, 20, 4), (21, 1, 11, 4), (12, 22, 2, 4), (3, 13, 23, 4),
    (24, 4, 14, 4), (15, 25, 5, 4), (6, 16, 26, 4), (27, 7, 17, 4),
    (18, 28, 8, 4), (9, 19, 29, 4), (None, 31, 30, 3),
]
MD5_B64 = [
    (0, 6, 12, 4), (1, 7, 13, 4), (2, 8, 14, 4), (3, 9, 15, 4),
    (4, 10, 5, 4), (None, None, 11, 2),
]


# ---------------------------------------------------------------------------
# 纯 Python 的 Unix crypt 实现（零依赖，按 glibc / SHA-crypt 规范）
# ---------------------------------------------------------------------------

def _b64_group(digest, spec):
    w = 0
    for i, shift in ((spec[0], 16), (spec[1], 8), (spec[2], 0)):
        if i is not None:
            w |= digest[i] << shift
    out = []
    for _ in range(spec[3]):
        out.append(B64T[w & 0x3F])
        w >>= 6
    return "".join(out)


def _sha_crypt(secret, salt, rounds, digestmod, digest_len, b64_spec):
    """SHA-256/SHA-512 crypt 通用实现（SHA-crypt 规范 / glibc sha*crypt.c）。"""
    B = digestmod(secret + salt + secret).digest()
    add = (B * ((len(secret) + digest_len - 1) // digest_len))[:len(secret)]
    bits = []
    cnt = len(secret)
    while cnt > 0:
        bits.append(B if (cnt & 1) else secret)
        cnt >>= 1
    A = digestmod(secret + salt + add + b"".join(bits)).digest()

    DP = digestmod(secret * len(secret)).digest()
    P = (DP * ((len(secret) + digest_len - 1) // digest_len))[:len(secret)]
    DS = digestmod(salt * (16 + A[0])).digest()
    S = (DS * ((len(salt) + digest_len - 1) // digest_len))[:len(salt)]

    for i in range(rounds):
        parts = [P if (i & 1) else A]
        if i % 3 != 0:
            parts.append(S)
        if i % 7 != 0:
            parts.append(P)
        parts.append(A if (i & 1) else P)
        A = digestmod(b"".join(parts)).digest()

    return "".join(_b64_group(A, s) for s in b64_spec)


def sha512_crypt(secret, salt, rounds=5000):
    return _sha_crypt(secret, salt, rounds, hashlib.sha512, 64, SHA512_B64)


def sha256_crypt(secret, salt, rounds=5000):
    return _sha_crypt(secret, salt, rounds, hashlib.sha256, 32, SHA256_B64)


def md5_crypt(secret, salt):
    """md5crypt：magic "$1$" 参与初始摘要；位循环每比特 1 字节（1 位=NUL，0 位=密码首字节）；固定 1000 轮。"""
    magic = b"$1$"
    B = hashlib.md5(secret + salt + secret).digest()
    add = (B * ((len(secret) + 15) // 16))[:len(secret)]
    bits = []
    cnt = len(secret)
    while cnt > 0:
        bits.append(b"\x00" if (cnt & 1) else secret[:1])
        cnt >>= 1
    A = hashlib.md5(secret + magic + salt + add + b"".join(bits)).digest()
    for i in range(1000):
        parts = [secret if (i & 1) else A]
        if i % 3 != 0:
            parts.append(salt)
        if i % 7 != 0:
            parts.append(secret)
        parts.append(A if (i & 1) else secret)
        A = hashlib.md5(b"".join(parts)).digest()
    return "".join(_b64_group(A, s) for s in MD5_B64)


# ---------------------------------------------------------------------------
# 哈希解析与校验
# ---------------------------------------------------------------------------

def detect_mode(h):
    """根据哈希内容猜测 hashcat 模式号；无法识别返回 None。"""
    h = h.strip()
    if h.startswith("$6$"):
        return 1800
    if h.startswith("$5$"):
        return 7400
    if h.startswith("$1$"):
        return 500
    if re.match(r"^\$2[aby]\$", h):
        return 3200
    if re.fullmatch(r"[0-9a-fA-F]{40}", h):
        return 100
    if re.fullmatch(r"[0-9a-fA-F]{32}", h):
        return 0  # MD5/NTLM 歧义，交互模式再确认
    return None


class HashTarget:
    """一个待破解哈希的解析结果与校验器。"""

    def __init__(self, hash_str, mode=None):
        self.hash_str = hash_str.strip()
        self.mode = mode if mode is not None else detect_mode(self.hash_str)
        if self.mode is None:
            raise ValueError("无法自动识别哈希类型，请用 -m 手动指定 hashcat 模式")
        self._prepare()

    def _prepare(self):
        h, m = self.hash_str, self.mode
        if m in (1800, 7400, 500):
            prefix = {"1800": "$6$", "7400": "$5$", "500": "$1$"}[str(m)]
            if not h.startswith(prefix):
                raise ValueError("模式 %d 要求哈希以 %s 开头" % (m, prefix))
            parts = h.split("$")
            salt_part = parts[2]
            expected = parts[3] if len(parts) >= 4 else ""
            rounds, salt_str = self._parse_rounds(salt_part)
            self.salt = salt_str.encode("utf-8", "replace")
            self.salt = self.salt[:8] if m == 500 else self.salt[:16]
            self.rounds = rounds
            self.expected = expected.encode("ascii", "replace")
        elif m == 3200:
            if not re.match(r"^\$2[aby]\$", h):
                raise ValueError("模式 3200 (bcrypt) 要求哈希以 $2a$/$2b$/$2y$ 开头")
            try:
                import bcrypt  # noqa: F401
            except ImportError:
                raise ValueError("bcrypt 模式需要: pip install bcrypt")
            self.salt = h.encode("utf-8", "replace")
        elif m in (0, 100, 1000):
            pat = {0: r"[0-9a-fA-F]{32}", 100: r"[0-9a-fA-F]{40}",
                   1000: r"[0-9a-fA-F]{32}"}[m]
            if not re.fullmatch(pat, h):
                raise ValueError("模式 %d 的哈希格式不正确" % m)
            self.expected = h.lower().encode("ascii")
        else:
            raise ValueError("模式 %d 不支持（纯 Python 支持: %s）"
                             % (m, ", ".join(str(x) for x in sorted(PURE_SUPPORTED))))

    @staticmethod
    def _parse_rounds(salt_part):
        m = re.match(r"^rounds=(\d+)\$(.*)$", salt_part, re.S)
        if m:
            return max(1000, min(int(m.group(1)), 999999999)), m.group(2)
        return 5000, salt_part

    def check(self, pw):
        """pw: bytes -> bool"""
        m = self.mode
        try:
            if m == 1800:
                got = sha512_crypt(pw, self.salt, self.rounds)
            elif m == 7400:
                got = sha256_crypt(pw, self.salt, self.rounds)
            elif m == 500:
                got = md5_crypt(pw, self.salt)
            elif m == 3200:
                import bcrypt
                return bcrypt.checkpw(pw, self.salt)
            elif m == 0:
                return hashlib.md5(pw).hexdigest().encode() == self.expected
            elif m == 100:
                return hashlib.sha1(pw).hexdigest().encode() == self.expected
            elif m == 1000:
                return hashlib.new("md4", pw).hexdigest().encode() == self.expected
            else:
                return False
        except Exception:
            return False
        return got.encode("ascii", "replace") == self.expected


# ---------------------------------------------------------------------------
# potfile 管理（hash:password，与 hashcat 兼容）
# ---------------------------------------------------------------------------

def default_potfile():
    """potfile 默认放在工具所在目录（与 hashcat 的配置方式一致：potfile 与程序同目录）。"""
    return Path(__file__).resolve().parent / "potfile"


def default_config():
    """配置文件（记录 hashcat 路径等），与工具同目录。"""
    return Path(__file__).resolve().parent / "hashcrack.ini"


def load_config():
    """读取配置文件 -> dict（键=值，每行一个）"""
    cfg = {}
    p = default_config()
    if p.exists():
        try:
            with open(p, "r", encoding="utf-8") as f:
                for line in f:
                    line = line.strip()
                    if line and "=" in line:
                        k, v = line.split("=", 1)
                        cfg[k.strip()] = v.strip()
        except OSError:
            pass
    return cfg


def save_config(**kw):
    """合并保存配置到 hashcrack.ini"""
    cfg = load_config()
    cfg.update(kw)
    p = default_config()
    try:
        p.parent.mkdir(parents=True, exist_ok=True)
        with open(p, "w", encoding="utf-8") as f:
            for k, v in cfg.items():
                f.write("%s=%s\n" % (k, v))
    except OSError:
        pass


def load_potfile(path):
    store = {}
    if path and os.path.exists(path):
        try:
            with open(path, "r", encoding="utf-8", errors="replace") as f:
                for line in f:
                    line = line.rstrip("\r\n")
                    if ":" in line:
                        h, p = line.split(":", 1)
                        store[h] = p
        except OSError:
            pass
    return store


def save_potfile(path, entries):
    if not entries:
        return
    existing = load_potfile(path)
    Path(path).parent.mkdir(parents=True, exist_ok=True)
    with open(path, "a", encoding="utf-8", errors="replace") as f:
        for h, p in entries.items():
            if h not in existing:
                f.write("%s:%s\n" % (h, p))


def query_potfile(path, hashes):
    store = load_potfile(path)
    return {h: store[h] for h in hashes if h in store}


# ---------------------------------------------------------------------------
# hashcat 后端
# ---------------------------------------------------------------------------

def find_hashcat(explicit=None):
    """查找 hashcat：--hashcat-path > 配置文件 hashcrack.ini > HASHCAT_PATH > PATH > 常见目录。"""
    cfg = load_config()
    for cand in (explicit, cfg.get("hashcat_path"),
                 os.environ.get("HASHCAT_PATH")):
        if cand and os.path.exists(cand):
            return cand
    exe = shutil.which("hashcat") or shutil.which("hashcat.exe")
    if exe:
        return exe
    for cand in (Path.cwd(), Path(__file__).resolve().parent):
        for name in ("hashcat.exe", "hashcat"):
            p = cand / name
            if p.exists():
                return str(p)
    return None


def _hashcat_cmd(exe, mode, potfile, device, extra):
    cmd = [exe, "-m", str(mode), "-a", "0"]
    if device:
        cmd += ["-d", str(device)]
    if potfile:
        cmd += ["--potfile-path", str(potfile)]
    cmd += list(extra)
    return cmd


def run_hashcat(hash_strs, mode, wordlist, device=None, potfile=None,
                extra=(), hashcat_path=None):
    """用 hashcat 破解。哈希写入自动管理的临时文件（用完删除）。
    返回 (退出码, {hash: password})。"""
    exe = find_hashcat(hashcat_path)
    if not exe:
        raise RuntimeError("未找到 hashcat")
    cmd = _hashcat_cmd(exe, mode, potfile, device, extra)
    tmp_hash = None
    try:
        fd, tmp_hash = tempfile.mkstemp(prefix="hashcrack_", suffix=".hash")
        with os.fdopen(fd, "w", encoding="utf-8") as f:
            f.write("\n".join(hash_strs) + "\n")
        cmd += [tmp_hash, str(wordlist)]

        print("[*] 命令: %s" % " ".join(cmd))
        print("[*] 正在启动 hashcat ...")
        sys.stdout.flush()

        proc = subprocess.Popen(
            cmd, stdin=subprocess.DEVNULL, stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT, text=True, encoding="utf-8",
            errors="replace", bufsize=1,
            cwd=str(Path(exe).parent),  # hashcat 需在其安装目录运行（OpenCL 相对路径）
        )
        try:
            for line in proc.stdout:
                print(line, end="")
                sys.stdout.flush()
        except KeyboardInterrupt:
            print("\n[!] 收到中断，正在终止 hashcat ...")
            proc.terminate()
            try:
                proc.wait(timeout=5)
            except subprocess.TimeoutExpired:
                proc.kill()
            return 130, {}
        finally:
            if proc.stdout:
                proc.stdout.close()
        proc.wait()
        print("[*] hashcat 退出码: %d" % proc.returncode)

        cracked = query_potfile(potfile, hash_strs) if potfile else {}
        if not cracked:
            cracked = hashcat_show(hash_strs, mode, potfile, hashcat_path)
        return proc.returncode, cracked
    finally:
        if tmp_hash and os.path.exists(tmp_hash):
            try:
                os.unlink(tmp_hash)
            except OSError:
                pass


def hashcat_show(hash_strs, mode, potfile=None, hashcat_path=None):
    """调用 hashcat --show 查询 -> {hash: password}"""
    exe = find_hashcat(hashcat_path)
    if not exe:
        return {}
    cmd = [exe, "-m", str(mode), "--show"]
    if potfile:
        cmd += ["--potfile-path", str(potfile)]
    tmp_hash = None
    try:
        fd, tmp_hash = tempfile.mkstemp(prefix="hashcrack_", suffix=".hash")
        with os.fdopen(fd, "w", encoding="utf-8") as f:
            f.write("\n".join(hash_strs) + "\n")
        cmd.append(tmp_hash)
        proc = subprocess.Popen(
            cmd, stdin=subprocess.DEVNULL, stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT, text=True, encoding="utf-8",
            errors="replace", cwd=str(Path(exe).parent))
        out = proc.stdout.read()
        proc.wait()
    except Exception:
        return {}
    finally:
        if tmp_hash and os.path.exists(tmp_hash):
            try:
                os.unlink(tmp_hash)
            except OSError:
                pass
    result = {}
    for line in out.splitlines():
        if ":" in line:
            h, p = line.split(":", 1)
            if h.strip() in hash_strs:
                result[h.strip()] = p.strip()
    return result


# ---------------------------------------------------------------------------
# 纯 Python 后端（多进程 + 进度）
# ---------------------------------------------------------------------------

def wordlist_lines(path):
    """逐行产出字典密码 bytes；支持普通文件 / .gz / '-' (stdin)。"""
    if str(path) == "-":
        for line in sys.stdin.buffer:
            yield line.rstrip(b"\r\n")
    else:
        opener = gzip.open if str(path).lower().endswith(".gz") else open
        with opener(path, "rb") as f:
            for line in f:
                yield line.rstrip(b"\r\n")


def _worker_init(specs):
    global _TARGETS
    _TARGETS = []
    for mode, hash_str, salt, rounds in specs:
        t = HashTarget(hash_str, mode)
        if salt is not None:
            t.salt, t.rounds = salt, rounds
        _TARGETS.append(t)


def _worker_check(pw):
    hits = [t.hash_str for t in _TARGETS if t.check(pw)]
    return (pw, hits if hits else None)


def crack_pure(hash_strs, mode, wordlist, threads=None, quiet=False):
    """纯 Python 多进程破解 -> {hash: password}。Linux/macOS 自动用系统 crypt 模块。"""
    threads = max(1, min(threads or (os.cpu_count() or 2), 64))
    specs = []
    for h in hash_strs:
        t = HashTarget(h, mode)
        specs.append((mode, h, getattr(t, "salt", None), getattr(t, "rounds", None)))

    print("[*] 纯 Python 多进程破解，线程数: %d" % threads)
    if mode in (1800, 7400):
        print("[*] 提示: sha512crypt 每候选 ~5000 轮哈希，纯 Python 较慢，建议装 hashcat 或用小字典。")

    try:
        import crypt as _crypt
        HAS_CRYPT = True
    except ImportError:
        HAS_CRYPT = False

    if HAS_CRYPT and mode in (1800, 7400, 500):
        return _crack_with_crypt(hash_strs, mode, wordlist, threads, quiet)

    results = {}
    start = time.monotonic()
    done, last_report = 0, 0.0
    pool = multiprocessing.Pool(processes=threads,
                                initializer=_worker_init, initargs=(specs,))
    try:
        try:
            for pw, hits in pool.imap_unordered(_worker_check,
                                                wordlist_lines(wordlist),
                                                chunksize=4096):
                done += 1
                if hits:
                    for h in hits:
                        results[h] = pw.decode("utf-8", "replace")
                        print("\n[+] 命中! %s : %s" % (h, results[h]))
                now = time.monotonic()
                if not quiet and now - last_report >= 2.0:
                    last_report = now
                    print("\r[*] 已测试 %d 个，速度 %.0f 个/秒，用时 %.0f 秒"
                          % (done, done / (now - start), now - start),
                          end="", flush=True)
                if len(results) >= len(hash_strs):
                    break
        except KeyboardInterrupt:
            print("\n[!] 收到中断，停止破解 ...")
    finally:
        pool.terminate()
        pool.join()
    if not quiet:
        print()
    return results


def _crack_with_crypt(hash_strs, mode, wordlist, threads, quiet):
    """用系统 crypt 模块（glibc）多进程破解，性能远高于纯 Python 实现。"""
    import crypt as _crypt
    targets = []
    for h in hash_strs:
        t = HashTarget(h, mode)
        prefix = {1800: "$6$", 7400: "$5$", 500: "$1$"}[mode]
        salt_arg = prefix + t.salt.decode("utf-8", "replace")
        targets.append((h, salt_arg))

    def check_one(pw):
        s = pw.decode("utf-8", "replace")
        for h, salt_arg in targets:
            try:
                if _crypt.crypt(s, salt_arg) == h:
                    return (pw, h)
            except Exception:
                pass
        return (pw, None)

    results = {}
    start = time.monotonic()
    done, last_report = 0, 0.0
    pool = multiprocessing.Pool(processes=threads)
    try:
        try:
            for pw, hit in pool.imap_unordered(check_one, wordlist_lines(wordlist),
                                               chunksize=4096):
                done += 1
                if hit:
                    results[hit] = pw.decode("utf-8", "replace")
                    print("\n[+] 命中! %s : %s" % (hit, results[hit]))
                now = time.monotonic()
                if not quiet and now - last_report >= 2.0:
                    last_report = now
                    print("\r[*] 已测试 %d 个，速度 %.0f 个/秒，用时 %.0f 秒"
                          % (done, done / (now - start), now - start),
                          end="", flush=True)
                if len(results) >= len(targets):
                    break
        except KeyboardInterrupt:
            print("\n[!] 收到中断，停止破解 ...")
    finally:
        pool.terminate()
        pool.join()
    if not quiet:
        print()
    return results


# ---------------------------------------------------------------------------
# 字典查找
# ---------------------------------------------------------------------------

def find_wordlist():
    candidates = [
        "/usr/share/wordlists/rockyou.txt",
        "/usr/share/wordlists/rockyou.txt.gz",
        "/usr/share/wordlists/rockyou.txt.zip",
        "/opt/wordlists/rockyou.txt",
        "rockyou.txt", "rockyou.txt.gz",
        str(Path.home() / "rockyou.txt"),
        str(Path.home() / "Downloads" / "rockyou.txt"),
    ]
    return next((c for c in candidates if os.path.exists(c)), None)


# ---------------------------------------------------------------------------
# 交互模式
# ---------------------------------------------------------------------------

def _ask(prompt, default=None, allow_empty=False):
    while True:
        suffix = (" [%s]" % default) if default else ""
        try:
            v = input(prompt + suffix + "> ").strip()
        except (EOFError, KeyboardInterrupt):
            print()
            return None
        if v:
            return v
        if default:
            return default
        if allow_empty:
            return ""
        print(_("input_empty"))


def _collect_hashes():
    print(_("paste_hint"))
    print(_("q_hint"))
    hashes = []
    while True:
        try:
            line = input("> ").strip()
        except (EOFError, KeyboardInterrupt):
            print()
            return None
        if line.lower() in ("q", "quit", "exit"):
            return None
        if not line:
            if hashes:
                break
            continue
        hashes.extend(p for p in line.split() if p)
    return hashes


def interactive(args):
    """常驻会话：完成一个任务后停留，等待下一条指令（继续下一个哈希或退出）。"""
    print("=" * 56)
    print("  " + _("banner_title").format(version=__version__))
    for line in _("banner_lines").split("\n"):
        print("  " + line)
    print("=" * 56)
    
    # 语言选择
    global LANGUAGE
    if LANGUAGE is None:
        LANGUAGE = select_language()
    
    print(_("welcome").format(version=__version__))
    
    while True:
        rc = _interactive_once(args)
        if rc in (130, 2):
            print("\n[!] " + _("exited"))
            return 0
        print()
        try:
            v = input(_("continue_prompt")).strip().lower()
        except (EOFError, KeyboardInterrupt):
            print("\n[!] " + _("exited"))
            return 0
        if v not in ("y", "yes"):
            print(_("exit_msg"))
            return 0
        print()


def _interactive_once(args):
    """完成一次完整的破解任务。返回 0=完成 1=出错 2=用户退出 130=中断。"""
    hashes = [h.strip() for h in (args.hash or []) if h.strip()]
    if not hashes:
        hashes = _collect_hashes()
        if hashes is None:
            return 2
    if not hashes:
        print("[!] 未输入任何哈希，退出。")
        return 1

    print("\n" + _("hashes_received") % len(hashes))
    for i, h in enumerate(hashes, 1):
        m = detect_mode(h)
        print(_("hash_list_item") % (i, h, MODE_NAMES.get(m, _("unknown_mode")), m or "?"))

    # 模式
    modes = {detect_mode(h) for h in hashes} - {None}
    if not modes:
        print("\n" + _("auto_detect_fail"))
        try:
            mode = int(_ask(_("ask_mode"), default="1800"))
        except (TypeError, ValueError):
            print(_("invalid_mode"))
            return 1
    elif len(modes) == 1:
        mode = modes.pop()
        print("\n" + _("auto_detected") % (MODE_NAMES.get(mode, _("mode_num") % mode), mode))
        if mode in (0, 1000) and len(hashes) == 1:
            v = _ask(_("md5_ntlm_choice"), default="0")
            try:
                mode = int(v) if v else 0
            except ValueError:
                mode = 0
            if mode not in (0, 1000):
                mode = 0
        else:
            v = _ask(_("confirm_mode"), default="y")
            if v is None or v.lower().startswith("n"):
                try:
                    mode = int(_ask(_("ask_mode"), default=str(mode)))
                except (TypeError, ValueError):
                    print(_("invalid_mode"))
                    return 1
    else:
        print("\n" + _("multi_mode"))
        try:
            mode = int(_ask(_("ask_mode"), default="1800"))
        except (TypeError, ValueError):
            print(_("invalid_mode"))
            return 1

    # 后端
    hc = find_hashcat(args.hashcat_path)
    if not hc and not args.pure:
        v = _ask(_("no_hashcat_ask"), allow_empty=True)
        if v:
            hc = find_hashcat(v)
            if hc:
                save_config(hashcat_path=hc)
                print(_("hashcat_saved") % hc)
    if hc and not args.pure:
        if mode in PURE_SUPPORTED:
            v = _ask(_("backend_choice") % hc, default="1")
            use_hashcat = (v is None or v == "1")
        else:
            print(_("backend_hashcat_only") % mode)
            use_hashcat = True
    else:
        if mode not in PURE_SUPPORTED:
            print(_("no_backend") % mode)
            return 1
        print(_("backend_pure"))
        use_hashcat = False

    # 字典
    wl = args.wordlist
    if not wl:
        found = find_wordlist()
        if found:
            v = _ask(_("dict_found") % found, default="y")
            wl = found if (v is None or v.lower().startswith("y")) else _ask(_("ask_dict"))
        else:
            wl = _ask(_("ask_dict2"))
    if not wl or not os.path.exists(wl):
        print(_("dict_missing") % wl)
        return 1

    # 运行
    print()
    potfile = Path(args.potfile) if args.potfile else default_potfile()
    results = {}
    if use_hashcat:
        code, results = run_hashcat(hashes, mode, wl, device=args.device,
                                    potfile=str(potfile),
                                    hashcat_path=args.hashcat_path)
        if code == 130:
            return 130
    else:
        results = crack_pure(hashes, mode, wl, threads=args.threads,
                             quiet=args.quiet)

    print("\n" + "=" * 56)
    if results:
        print(_("results_header"))
        for h, p in results.items():
            print("  %s : %s" % (h, p))
        save_potfile(str(potfile), results)
        print(_("potfile_saved") % potfile)
    else:
        print(_("no_result"))
        print(_("no_result_tip"))
    return 0


# ---------------------------------------------------------------------------
# 自检
# ---------------------------------------------------------------------------

def selftest():
    print("[*] 运行算法自检 ...")
    ok = True

    def check(name, got, expected):
        nonlocal ok
        good = got == expected
        ok = ok and good
        print("  %-30s %s" % (name, "OK" if good else "FAIL"))
        if not good:
            print("    期望: %s\n    实际: %s" % (expected, got))

    check("sha512crypt Hello world!",
          "$6$saltstring$" + sha512_crypt(b"Hello world!", b"saltstring", 5000),
          "$6$saltstring$svn8UoSVapNtMuq1ukKS4tPQd8iKwSMHWjl/O817G3uBnIFNjnQJuesI68u4OTLiBFdcbYEdFCoEOfaS35inz1")
    check("sha512crypt rounds=10000",
          "$6$rounds=10000$saltstringsaltst$" + sha512_crypt(b"Hello world!", b"saltstringsaltst", 10000),
          "$6$rounds=10000$saltstringsaltst$OW1/O6BYHV6BcXZu8QVeXbDWra3Oeqh0sbHbbMCVNSnCM/UrjmM0Dp8vOuZeHBy/YTBmSK6H9qs/y3RnOaw5v.")
    check("sha512crypt rounds=77777 short",
          "$6$rounds=77777$short$" + sha512_crypt(b"we have a short salt string but not a short password", b"short", 77777),
          "$6$rounds=77777$short$WuQyW2YR.hBNpjjRhpYD/ifIw05xdfeEyQoMxIXbkvr0gge1a1x3yRULJ5CCaUeOxFmtlcGZelFl5CxtgfiAc0")
    check("sha512crypt rounds=1000 clamp",
          "$6$rounds=1000$roundstoolow$" + sha512_crypt(b"the minimum number is still observed", b"roundstoolow", 1000),
          "$6$rounds=1000$roundstoolow$kUMsbe306n21p9R.FRkW3IGn.S9NPN0x50YhH1xhLsPuWGsUSklZt58jaTfF4ZEQpyUNGc0dqbpBYYBaHHrsX.")
    check("sha256crypt Hello world!",
          "$5$saltstring$" + sha256_crypt(b"Hello world!", b"saltstring", 5000),
          "$5$saltstring$5B8vYYiY.CVt1RlTTf8KbXBH3hsxY/GNooZaBBGWEc5")
    check("sha256crypt rounds=123456",
          "$5$rounds=123456$asaltof16chars..$" + sha256_crypt(b"a short string", b"asaltof16chars..", 123456),
          "$5$rounds=123456$asaltof16chars..$gP3VQ/6X7UUEW3HkBn2w1/Ptq2jxPyzV/cZKmF/wJvD")
    check("md5crypt password/salt",
          "$1$salt$" + md5_crypt(b"password", b"salt"),
          "$1$salt$qJH7.N4xYta3aEG/dfqo/0")
    check("md5crypt Hello world!/saltstri",
          "$1$saltstri$" + md5_crypt(b"Hello world!", b"saltstri"),
          "$1$saltstri$YMyguxXMBpd2TEZ.vS/3q1")
    check("sha512crypt 真实案例 (s3cret)",
          "$6$PYikyu28$" + sha512_crypt(b"s3cret", b"PYikyu28", 5000),
          "$6$PYikyu28$gaZOe5FUDn62MDPkhAwj8KnYdu4S1MZoT44AuehXiFtwGIToYRutVTVKnr66j0298FTWd55YIpEpIPOQMh.tB.")
    check("MD5('123456')", hashlib.md5(b"123456").hexdigest(),
          "e10adc3949ba59abbe56e057f20f883e")
    check("SHA1('123456')", hashlib.sha1(b"123456").hexdigest(),
          "7c4a8d09ca3762af61e59520943dc26494f8941b")

    print("\n[%s] 自检 %s" % ("通过" if ok else "失败", "all tests OK" if ok else "存在失败项"))
    return 0 if ok else 1


# ---------------------------------------------------------------------------
# 入口
# ---------------------------------------------------------------------------

def main():
    parser = argparse.ArgumentParser(
        prog="hashcrack",
        description="交互式哈希破解工具：哈希直接命令行/交互输入，无需 hash.txt。"
                    "优先 hashcat 加速，无 hashcat 时纯 Python 多进程兜底。",
        epilog="示例:\n"
               "  hashcrack\n"
               "  hashcrack -h '$6$salt$hash' -w rockyou.txt\n"
               "  hashcrack -h '$6$salt$hash' -m 1800 -w dict.txt -d 1\n"
               "  hashcrack --pure -h '$6$salt$hash' -w dict.txt\n"
               "  hashcrack --show -h '$6$salt$hash'",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        add_help=False,
    )
    parser.add_argument("--help", action="help", help="显示帮助并退出")
    parser.add_argument("-h", "--hash", action="append", dest="hash",
                        help="要破解的哈希（可多次指定；不指定则进入交互粘贴模式）")
    parser.add_argument("-m", "--mode", type=int, default=None,
                        help="hashcat 模式号（如 1800=sha512crypt；默认自动识别）")
    parser.add_argument("-w", "--wordlist", default=None,
                        help="字典文件路径（支持 .gz；默认自动查找 rockyou.txt）")
    parser.add_argument("-d", "--device", default=None,
                        help="hashcat 设备号（透传给 hashcat -d）")
    parser.add_argument("--hashcat-path", default=None,
                        help="hashcat 可执行文件路径")
    parser.add_argument("--pure", action="store_true",
                        help="强制纯 Python 后端（不调用 hashcat）")
    parser.add_argument("--threads", type=int, default=None,
                        help="纯 Python 后端线程数（默认 CPU 核数）")
    parser.add_argument("--potfile", default=None,
                        help="potfile 路径（默认 ~/.hashcrack/potfile）")
    parser.add_argument("--import-potfile", default=None,
                        help="导入现有 potfile（如 hashcat.potfile）到本工具 potfile")
    parser.add_argument("--show", action="store_true",
                        help="只查询 potfile 中已破解的结果，不运行破解")
    parser.add_argument("--quiet", action="store_true",
                        help="纯 Python 后端不显示进度")
    parser.add_argument("--selftest", action="store_true",
                        help="运行算法自检后退出")
    parser.add_argument("--version", action="version", version="%(prog)s " + __version__)
    args = parser.parse_args()

    # Windows 控制台 UTF-8 输出（避免中文乱码）
    if sys.platform == "win32":
        try:
            import ctypes
            ctypes.windll.kernel32.SetConsoleOutputCP(65001)
        except Exception:
            pass
    try:
        sys.stdout.reconfigure(errors="replace")
        sys.stderr.reconfigure(errors="replace")
    except Exception:
        pass

    if args.selftest:
        return selftest()

    potfile = Path(args.potfile) if args.potfile else default_potfile()

    if args.import_potfile:
        src = Path(args.import_potfile)
        if src.exists():
            entries = load_potfile(str(src))
            if entries:
                save_potfile(str(potfile), entries)
                print("[*] 已从 %s 导入 %d 条结果到 %s" % (src, len(entries), potfile))
        else:
            print("[!] 导入源不存在: %s" % src)

    if args.show:
        if not args.hash:
            store = load_potfile(str(potfile))
            if not store:
                print("[!] potfile 为空: %s" % potfile)
                return 1
            print("potfile 中全部已破解结果 (%d 条):" % len(store))
            for h, p in store.items():
                print("  %s : %s" % (h, p))
            return 0
        found = query_potfile(str(potfile), [h.strip() for h in args.hash])
        if found:
            for h, p in found.items():
                print("%s:%s" % (h, p))
            return 0
        print("[!] potfile 中没有这些哈希的结果: %s" % potfile)
        return 1

    # 非交互一键模式
    if args.hash:
        hashes = [h.strip() for h in args.hash if h.strip()]
        if not hashes:
            print("[!] -h 参数为空")
            return 1

        if args.mode is None:
            modes = {detect_mode(h) for h in hashes} - {None}
            if len(modes) == 1:
                mode = modes.pop()
                print("[*] 自动识别模式 %d (%s)" % (mode, MODE_NAMES.get(mode, "自定义")))
            elif len(modes) > 1:
                print("[!] 多个哈希类型不一致，请用 -m 指定模式")
                return 1
            else:
                print("[!] 无法自动识别哈希类型，请用 -m 指定模式")
                return 1
        else:
            mode = args.mode

        # 破解前先查 potfile（避免重复跑已破解的哈希）
        pre = query_potfile(str(potfile), hashes)
        if pre:
            print("[*] potfile 中已有结果，无需重新破解：")
            for h, p in pre.items():
                print("    %s : %s" % (h, p))
            return 0

        wl = args.wordlist or find_wordlist()
        if not wl:
            print("[!] 未找到字典，请用 -w 指定（如 rockyou.txt）")
            return 1
        if not os.path.exists(wl):
            print("[!] 字典不存在: %s" % wl)
            return 1

        if args.pure:
            if mode not in PURE_SUPPORTED:
                print("[!] 模式 %d 不被纯 Python 后端支持（支持: %s）"
                      % (mode, ", ".join(str(x) for x in sorted(PURE_SUPPORTED))))
                return 1
            print("[*] 使用纯 Python 后端")
            results = crack_pure(hashes, mode, wl, threads=args.threads,
                                 quiet=args.quiet)
        else:
            hc = find_hashcat(args.hashcat_path)
            if not hc:
                print("[!] 未找到 hashcat，改用纯 Python 后端（可用 --pure 显式指定）")
                if mode not in PURE_SUPPORTED:
                    print("[!] 但模式 %d 不被纯 Python 后端支持，退出。" % mode)
                    return 1
                results = crack_pure(hashes, mode, wl, threads=args.threads,
                                     quiet=args.quiet)
            else:
                if args.hashcat_path:
                    save_config(hashcat_path=hc)
                    print("[*] 已记住 hashcat 路径: %s" % hc)
                print("[*] 使用 hashcat: %s" % hc)
                code, results = run_hashcat(hashes, mode, wl, device=args.device,
                                            potfile=str(potfile),
                                            hashcat_path=args.hashcat_path)
                if code == 130:
                    return 130

        if results:
            print("\n[+] 破解结果：")
            for h, p in results.items():
                print("    %s : %s" % (h, p))
            save_potfile(str(potfile), results)
            print("[*] 已保存到 potfile: %s" % potfile)
            return 0
        print("[-] 未破解出结果。")
        return 1

    return interactive(args)


if __name__ == "__main__":
    sys.exit(main())