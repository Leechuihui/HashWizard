**English** | [简体中文](README.zh-CN.md)

# 🔓 HashWizard

[![Python](https://img.shields.io/badge/Python-3.8%2B-3fb950?logo=python&logoColor=white)](https://python.org) [![License: MIT](https://img.shields.io/badge/License-MIT-yellow)](LICENSE) [![Security](https://img.shields.io/badge/Category-Security-8b5cf6)](https://github.com/Leechuihui/HashWizard)

Interactive password hash cracking tool in pure Python — paste a hash, auto-detect its type, crack it with hashcat or the built-in zero-dependency engine. Cross-platform.

Paste your hash directly into the command line — **no more manually creating `hash.txt` files**.

- **Interactive wizard**: paste hash(es) → auto-detect type → choose backend → pick wordlist → crack
- **hashcat backend**: automatically uses your local hashcat (GPU/CPU accelerated) when available
- **Pure Python backend**: built-in implementations of sha512crypt / sha256crypt / md5crypt, with multi-process parallelism and live progress — works even without hashcat
- **Smart potfile**: results are checked before cracking — already-cracked hashes are returned instantly without re-running
- **Cross-platform**: Linux / Windows / macOS (Python 3.8+)

---

## Requirements

- Python 3.8+ (no third-party packages required)
- Optional: [hashcat](https://hashcat.net/hashcat/) for GPU/CPU accelerated cracking
- Optional: `bcrypt` package (`pip install bcrypt`) for bcrypt hash support in the pure Python backend

---

## Quick Start

### 1. Interactive mode (recommended)

```bash
python3 hashcrack.py
```

You will be guided step by step:

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

### 2. One-liner mode

```bash
# Auto-detect hash type, auto-find wordlist and backend
python3 hashcrack.py -h '$6$salt$hash...'

# Specify everything explicitly
python3 hashcrack.py -h '$6$salt$hash...' -m 1800 -w rockyou.txt -d 1

# Multiple hashes at once
python3 hashcrack.py -h '$6$a$...' -h '$6$b$...' -w rockyou.txt
```

### 3. Query previously cracked results

```bash
python3 hashcrack.py --show -h '$6$salt$hash...'
```

---

## Command Line Options

| Option | Description |
|---|---|
| `-h, --hash HASH` | Hash to crack (repeatable). If omitted, interactive paste mode starts |
| `-m, --mode MODE` | hashcat mode number (e.g. `1800` = sha512crypt). Auto-detected if omitted |
| `-w, --wordlist FILE` | Wordlist path (`.gz` supported). Auto-searches for rockyou.txt if omitted |
| `-d, --device N` | hashcat device number (passed through to `hashcat -d`) |
| `--hashcat-path PATH` | Explicit path to the hashcat executable |
| `--pure` | Force the pure Python backend (skip hashcat) |
| `--threads N` | Worker processes for the pure Python backend (default: CPU cores) |
| `--potfile PATH` | Potfile path (default: alongside the tool) |
| `--import-potfile PATH` | Import an existing potfile (e.g. hashcat's `hashcat.potfile`) into the tool's potfile |
| `--show` | Only query the potfile for cracked results, do not crack |
| `--quiet` | Suppress progress output of the pure Python backend |
| `--selftest` | Run built-in algorithm self-tests and exit |
| `--version` | Show version |
| `--help` | Show help |

---

## Supported Hash Types

| hashcat mode | Type | Auto-detect prefix |
|---|---|---|
| 1800 | sha512crypt (`$6$`) | `$6$` |
| 7400 | sha256crypt (`$5$`) | `$5$` |
| 500 | md5crypt (`$1$`) | `$1$` |
| 3200 | bcrypt (`$2a$/$2b$/$2y$`) | `$2a$`/`$2b$`/`$2y$` (requires `pip install bcrypt` for pure backend) |
| 0 | MD5 | 32 hex chars |
| 100 | SHA1 | 40 hex chars |
| 1000 | NTLM | 32 hex chars (ambiguous with MD5 — confirmed in interactive mode) |

> Note: 32-character hex hashes are ambiguous (MD5 vs NTLM). In interactive mode you will be asked to confirm; in one-liner mode MD5 (0) is assumed — use `-m 1000` for NTLM.

Any other hashcat mode works as long as hashcat is installed (the tool passes the mode straight through).

---

## Backends

### hashcat backend (fast, default)

The tool locates hashcat automatically in this order:

1. `--hashcat-path` argument
2. `HASHCAT_PATH` environment variable
3. `PATH` (`hashcat` / `hashcat.exe`)
4. Current directory and the script's directory

The hash is written to a temporary file automatically and deleted after the run — **you never have to create a hash file yourself**. The tool also manages its own potfile (`--potfile-path`), so results are remembered across runs.

### Pure Python backend (fallback, no dependencies)

Used automatically when hashcat is not found, or forced with `--pure`.

- On Linux/macOS, the system `crypt` module (glibc) is used for sha512crypt/sha256crypt/md5crypt — about 10x faster than the pure Python implementation.
- On Windows (no `crypt` module), built-in implementations written from the official glibc/SHA-crypt specifications are used.
- Multi-process parallel cracking with live progress display.
- **Warning**: sha512crypt requires ~5000 hash rounds per candidate. Pure Python throughput is only a few thousand candidates/second — use a small wordlist, or install hashcat for serious cracking.

---

## Potfile

- Default location: alongside the tool itself (same directory as `hashcrack.py`, just like hashcat keeps its potfile next to the executable)
- Format: `hash:password` per line (compatible with hashcat's potfile format)
- Cracked results are saved automatically; `--show` queries them without re-cracking
- **Smart pre-check**: before cracking, the tool checks the potfile — hashes already cracked are returned instantly without re-running the attack
- Use `--import-potfile` to migrate results from an existing hashcat potfile:

## Configuration

The tool stores its settings in `hashcrack.ini` (same directory as the tool):

```
hashcat_path=D:\cybersec\hash 工具\Hashcat\hashcat.exe
```

- The hashcat path is **remembered automatically** the first time you enter it (or pass `--hashcat-path`), so the GPU backend is found on every later run without extra arguments
- Lookup order for hashcat: `--hashcat-path` argument → `hashcrack.ini` → `HASHCAT_PATH` env var → `PATH` → current/script directory

```bash
python3 hashcrack.py --import-potfile /path/to/hashcat.potfile --show
```

---

## Examples

```bash
# Crack a sha512crypt hash with rockyou.txt (Linux, auto-finds everything)
python3 hashcrack.py -h '$6$salt$hash...'

# Same, but force GPU device 1 and show the full hashcat command
python3 hashcrack.py -h '$6$salt$hash...' -w rockyou.txt -d 1

# Windows: hashcat not on PATH
python hashcrack.py -h '$6$salt$hash...' -w rockyou.txt --hashcat-path "D:\cybersec\hash 工具\Hashcat\hashcat.exe"

# No hashcat installed? Pure Python multi-process crack
python3 hashcrack.py --pure -h '$6$salt$hash...' -w small_dict.txt

# Crack an MD5 hash (32 hex chars)
python3 hashcrack.py -h '5f4dcc3b5aa765d61d8327deb882cf99' -w rockyou.txt

# Check if a hash was already cracked
python3 hashcrack.py --show -h '$6$salt$hash...'

# Verify the built-in algorithm implementations
python3 hashcrack.py --selftest
```

---

## Self-Test

Run `python3 hashcrack.py --selftest` to verify the built-in algorithm implementations against the official test vectors (from the SHA-crypt specification, glibc md5-crypt, and a real-world sha512crypt sample):

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

## Troubleshooting

| Problem | Solution |
|---|---|
| `hashcat: No such file or directory` / falls back to pure Python | Pass `--hashcat-path <path>` or set `HASHCAT_PATH` |
| hashcat fails with `./OpenCL/: No such file or directory` | The tool runs hashcat from its own directory automatically; if you invoke hashcat manually, `cd` into its folder first |
| hashcat fails with `Token length exception` on stdin | Known hashcat 6.2.6 Windows bug with stdin (`-`); the tool works around it with an auto-managed temporary file |
| `bcrypt` mode fails | `pip install bcrypt` |
| Slow pure Python cracking | Expected — install hashcat, or use `--threads` to tune workers |
| Chinese/Unicode paths garbled on Windows console | Set `chcp 65001` in the terminal, or use `PYTHONIOENCODING=utf-8` |

---

## How It Works

- **Hash input**: `-h` arguments or interactive paste (multi-line, empty line / Ctrl+D finishes)
- **Type detection**: prefix-based (`$6$` → 1800, `$5$` → 7400, `$1$` → 500, `$2x$` → 3200, hex length → MD5/SHA1/NTLM)
- **hashcat backend**: subprocess with `-m <mode> -a 0`, temporary hash file, own potfile, then `--show` to confirm results
- **Pure Python backend**: `multiprocessing.Pool` with chunked `imap_unordered`, live progress, system `crypt` module preferred on Linux/macOS

## License

Free to use for educational and authorized security testing purposes. Only crack hashes you own or are explicitly permitted to test.
