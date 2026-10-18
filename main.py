#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Discord + TikTok Username Checker v4
pip install requests
"""

import os
import re
import sys
import json
import time
import string
import random
import secrets
import threading
import warnings
from pathlib import Path
from datetime import datetime
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import Optional, List, Dict, Set, Tuple

warnings.filterwarnings("ignore", message="Unverified HTTPS request")

try:
    import requests
    from requests.adapters import HTTPAdapter
    try:
        from urllib3.util.retry import Retry
    except ImportError:
        from requests.packages.urllib3.util.retry import Retry
except ImportError:
    print("[!] 'requests' is not installed. Run: pip install requests")
    sys.exit(1)


# =========================================================
# Colors
# =========================================================
class C:
    RESET = "\033[0m"
    BOLD = "\033[1m"
    DIM = "\033[2m"
    RED = "\033[31m"
    GREEN = "\033[32m"
    YELLOW = "\033[33m"
    BLUE = "\033[34m"
    MAGENTA = "\033[35m"
    CYAN = "\033[36m"


def c(text: str, color: str) -> str:
    return f"{color}{text}{C.RESET}"


LABELS = {
    "available": c("[+] AVAILABLE", C.GREEN),
    "taken": c("[-] taken    ", C.RED),
    "unknown": c("[?] unknown  ", C.YELLOW),
    "invalid": c("[!] invalid  ", C.MAGENTA),
    "blocked": c("[x] blocked  ", C.BLUE),
}


# =========================================================
# Constants
# =========================================================
BASE_DIR = Path(__file__).resolve().parent
RESULTS_DIR = BASE_DIR / "results"
PROXY_FILE = BASE_DIR / "proxies.txt"
CONFIG_FILE = BASE_DIR / "config.json"

DISCORD_API = "https://discord.com/api/v9/unique-username/username-attempt-unauthed"
TIKTOK_PROFILE = "https://www.tiktok.com/@{name}?lang=en"

DISCORD_RE = re.compile(r"^[a-z0-9_.]{2,32}$")
TIKTOK_RE = re.compile(r"^[a-z0-9._]{2,24}$")

UA = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
      "AppleWebKit/537.36 (KHTML, like Gecko) "
      "Chrome/124.0.0.0 Safari/537.36")

DEFAULT_SETTINGS = {
    "discord_delay": 2.0,
    "tiktok_delay": 0.5,
    "discord_workers": 2,
    "tiktok_workers": 3,
    "skip_checked": True,
    "save_available_only": False,
    "jitter": 0.25,
}


# =========================================================
# Local validation
# =========================================================
def valid_discord(name: str) -> bool:
    if not DISCORD_RE.fullmatch(name):
        return False
    if name.startswith(".") or name.endswith(".") or ".." in name:
        return False
    if "discord" in name:
        return False
    return True


def valid_tiktok(name: str) -> bool:
    if not TIKTOK_RE.fullmatch(name):
        return False
    if name.startswith(".") or name.endswith(".") or ".." in name:
        return False
    if name.isdigit():
        return False
    return True


def valid_both(name: str) -> bool:
    return valid_discord(name) and valid_tiktok(name)


# =========================================================
# Helpers
# =========================================================
def parse_json(resp):
    try:
        return resp.json()
    except ValueError:
        return None


def retry_after(resp, body) -> float:
    value = resp.headers.get("Retry-After")
    if value is None and isinstance(body, dict):
        value = body.get("retry_after")
    if value is None:
        value = resp.headers.get("X-RateLimit-Reset-After")
    try:
        return max(1.0, float(value))
    except (TypeError, ValueError):
        return 10.0


def snippet(resp) -> str:
    text = (resp.text or "").strip().replace("\n", " ")
    return text[:180] if text else "(empty)"


def read_names(path: Path) -> List[str]:
    text = path.read_text(encoding="utf-8-sig", errors="ignore")
    names, seen = [], set()
    for line in text.splitlines():
        n = line.strip().lower()
        if not n or n in seen:
            continue
        seen.add(n)
        names.append(n)
    return names


def human_time(seconds: float) -> str:
    seconds = int(seconds)
    if seconds < 60:
        return f"{seconds}s"
    m, s = divmod(seconds, 60)
    if m < 60:
        return f"{m}m{s:02d}s"
    h, m = divmod(m, 60)
    return f"{h}h{m:02d}m"


def yes(raw: str) -> bool:
    return raw.strip().lower() in ("y", "yes", "1", "true")


def load_config() -> Dict:
    if CONFIG_FILE.is_file():
        try:
            data = json.loads(CONFIG_FILE.read_text(encoding="utf-8"))
            merged = dict(DEFAULT_SETTINGS)
            merged.update({k: v for k, v in data.items() if k in DEFAULT_SETTINGS})
            return merged
        except Exception:
            pass
    return dict(DEFAULT_SETTINGS)


def save_config(cfg: Dict) -> None:
    try:
        CONFIG_FILE.write_text(json.dumps(cfg, indent=2), encoding="utf-8")
    except OSError:
        pass


# =========================================================
# Proxy pool
# =========================================================
class ProxyPool:
    def __init__(self, path: Optional[Path]):
        self.path = path
        self.proxies: List[Dict[str, str]] = []
        self._index = 0
        self._lock = threading.Lock()
        self.reload()

    def reload(self):
        self.proxies.clear()
        if self.path and self.path.is_file():
            for line in self.path.read_text(encoding="utf-8", errors="ignore").splitlines():
                line = line.strip()
                if not line or line.startswith("#"):
                    continue
                if "://" not in line:
                    line = "http://" + line
                self.proxies.append({"http": line, "https": line})

    def get(self) -> Optional[Dict[str, str]]:
        if not self.proxies:
            return None
        with self._lock:
            p = self.proxies[self._index % len(self.proxies)]
            self._index += 1
            return dict(p)

    def __bool__(self):
        return bool(self.proxies)


# =========================================================
# Storage
# =========================================================
class Store:
    def __init__(self, root: Path, platform: str):
        self.platform = platform
        self.dir = root / platform
        self.dir.mkdir(parents=True, exist_ok=True)
        self.files = {
            "available": self.dir / "available.txt",
            "taken": self.dir / "taken.txt",
            "unknown": self.dir / "unknown.txt",
            "invalid": self.dir / "invalid.txt",
            "blocked": self.dir / "blocked.txt",
            "checked": self.dir / "checked.txt",
        }
        self.data = {k: self._read(p) for k, p in self.files.items()}
        self._lock = threading.Lock()

    @staticmethod
    def _read(path: Path) -> Set[str]:
        if not path.exists():
            return set()
        with path.open("r", encoding="utf-8") as f:
            return {line.strip().lower() for line in f if line.strip()}

    def record(self, name: str, status: str):
        name = name.lower()
        with self._lock:
            if name not in self.data[status]:
                self.data[status].add(name)
                with self.files[status].open("a", encoding="utf-8") as f:
                    f.write(name + "\n")
            if status != "blocked" and name not in self.data["checked"]:
                self.data["checked"].add(name)
                with self.files["checked"].open("a", encoding="utf-8") as f:
                    f.write(name + "\n")

    def remove_unknown(self, name: str):
        name = name.lower()
        with self._lock:
            if name not in self.data["unknown"]:
                return
            self.data["unknown"].discard(name)
            tmp = self.files["unknown"].with_suffix(".tmp")
            tmp.write_text(
                "".join(f"{n}\n" for n in sorted(self.data["unknown"])),
                encoding="utf-8",
            )
            os.replace(tmp, self.files["unknown"])

    def seen(self) -> Set[str]:
        return (
            set(self.data["checked"])
            | set(self.data["available"])
            | set(self.data["taken"])
            | set(self.data["unknown"])
        )

    def counts(self) -> Dict[str, int]:
        return {k: len(v) for k, v in self.data.items()}

    def export_available(self) -> Path:
        stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        out = RESULTS_DIR / f"{self.platform}_available_{stamp}.txt"
        out.write_text(
            "".join(f"{n}\n" for n in sorted(self.data["available"])),
            encoding="utf-8",
        )
        return out


# =========================================================
# Checker base
# =========================================================
class BaseChecker:
    platform = ""
    default_delay = 1.0
    default_workers = 1
    MAX_RETRIES = 3

    def __init__(self, store: Store, proxy_pool: ProxyPool,
                 workers: Optional[int] = None, delay: Optional[float] = None,
                 jitter: float = 0.25):
        self.store = store
        self.proxy_pool = proxy_pool
        self.workers = max(1, int(workers or self.default_workers))
        self.delay = max(0.05, float(delay if delay is not None else self.default_delay))
        self.jitter = max(0.0, min(1.0, jitter))
        self.skip_checked = True
        self.stop_event = threading.Event()

        self._rate_lock = threading.Lock()
        self._cooldown_lock = threading.Lock()
        self._last_request = 0.0
        self._cooldown_until = 0.0
        self._local = threading.local()

    # ---------- session ----------
    @property
    def session(self) -> requests.Session:
        s = getattr(self._local, "session", None)
        if s is None:
            s = self._make_session()
            self._local.session = s
        return s

    def _make_session(self) -> requests.Session:
        s = requests.Session()
        retries = Retry(
            total=0,
            connect=0,
            read=0,
            backoff_factor=0,
            status_forcelist=(),
            allowed_methods=frozenset(["GET", "POST"]),
        )
        adapter = HTTPAdapter(
            pool_connections=self.workers * 2,
            pool_maxsize=self.workers * 4,
            max_retries=retries,
        )
        s.mount("http://", adapter)
        s.mount("https://", adapter)
        s.headers.update(self.headers())
        p = self.proxy_pool.get()
        if p:
            s.proxies.update(p)
        return s

    def headers(self) -> Dict[str, str]:
        return {"Accept": "*/*", "User-Agent": UA}

    def _rotate_proxy(self):
        p = self.proxy_pool.get()
        if p:
            self.session.proxies.clear()
            self.session.proxies.update(p)

    # ---------- rate limiting ----------
    def _wait_turn(self):
        with self._rate_lock:
            now = time.monotonic()
            jitter = self.delay * self.jitter * random.random()
            wait = max(
                self.delay + jitter - (now - self._last_request),
                self._cooldown_until - now,
            )
            if wait > 0:
                time.sleep(wait)
            self._last_request = time.monotonic()

    def _set_cooldown(self, seconds: float):
        with self._cooldown_lock:
            until = time.monotonic() + seconds
            if until > self._cooldown_until:
                self._cooldown_until = until

    # ---------- overrides ----------
    def validate(self, name: str) -> bool:
        raise NotImplementedError

    def check(self, name: str) -> Tuple[str, str]:
        raise NotImplementedError


# =========================================================
# Discord checker
# =========================================================
class DiscordChecker(BaseChecker):
    platform = "discord"
    default_delay = 2.0
    default_workers = 2

    def headers(self):
        return {
            "Content-Type": "application/json",
            "Accept": "application/json",
            "User-Agent": UA,
            "Origin": "https://discord.com",
            "Referer": "https://discord.com/register",
            "Accept-Language": "en-US,en;q=0.9",
        }

    def validate(self, name: str) -> bool:
        return valid_discord(name)

    def check(self, name: str) -> Tuple[str, str]:
        payload = {"username": name}
        last_detail = "unknown"

        for attempt in range(self.MAX_RETRIES + 1):
            self._wait_turn()
            try:
                resp = self.session.post(DISCORD_API, json=payload, timeout=20)
            except requests.RequestException as e:
                last_detail = f"network: {e.__class__.__name__}"
                if attempt < self.MAX_RETRIES:
                    self._set_cooldown(min(2 ** attempt, 30))
                    self._rotate_proxy()
                    continue
                return "unknown", last_detail

            body = parse_json(resp)

            if resp.status_code == 200 and isinstance(body, dict):
                taken = body.get("taken")
                if isinstance(taken, bool):
                    return ("taken" if taken else "available"), "ok"
                last_detail = "200 no 'taken' field"
            elif resp.status_code == 429:
                wait = retry_after(resp, body)
                self._set_cooldown(wait)
                last_detail = f"429 wait {wait:g}s"
                if attempt < self.MAX_RETRIES:
                    continue
                return "blocked", last_detail
            elif resp.status_code in (401, 403):
                self._set_cooldown(15)
                return "blocked", f"http {resp.status_code}"
            elif resp.status_code == 400:
                # invalid username payload from Discord
                code = body.get("code") if isinstance(body, dict) else None
                if code == 50035:
                    return "invalid", "invalid username format"
                return "invalid", snippet(resp)
            elif resp.status_code >= 500 and attempt < self.MAX_RETRIES:
                self._set_cooldown(2 ** attempt)
                continue
            else:
                return "unknown", f"http {resp.status_code}"

            if attempt < self.MAX_RETRIES:
                self._set_cooldown(min(2 ** attempt, 15))

        return "unknown", last_detail


# =========================================================
# TikTok checker
# =========================================================
class TikTokChecker(BaseChecker):
    platform = "tiktok"
    default_delay = 0.5
    default_workers = 3

    NOT_FOUND_MARKERS = (
        "couldn't find this account",
        "couldn&#39;t find this account",
        "couldn\u2019t find this account",
        "user not found",
        "page not available",
        "this account doesn",
        "statuscode\":10221",
        "statusCode\":10221",
    )

    CAPTCHA_MARKERS = (
        "captcha",
        "verify to continue",
        "please complete the verification",
        "secsdk-captcha",
    )

    def headers(self):
        return {
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,"
                      "image/avif,image/webp,*/*;q=0.8",
            "Accept-Language": "en-US,en;q=0.9",
            "User-Agent": UA,
            "Sec-Fetch-Dest": "document",
            "Sec-Fetch-Mode": "navigate",
            "Sec-Fetch-Site": "none",
            "Upgrade-Insecure-Requests": "1",
            "Cache-Control": "no-cache",
        }

    def validate(self, name: str) -> bool:
        return valid_tiktok(name)

    def check(self, name: str) -> Tuple[str, str]:
        if name.isdigit():
            return "invalid", "numeric only"

        url = TIKTOK_PROFILE.format(name=name)
        last_detail = "unknown"

        for attempt in range(self.MAX_RETRIES + 1):
            self._wait_turn()
            try:
                resp = self.session.get(url, timeout=20, allow_redirects=True)
            except requests.RequestException as e:
                last_detail = f"network: {e.__class__.__name__}"
                if attempt < self.MAX_RETRIES:
                    self._set_cooldown(min(2 ** attempt, 30))
                    self._rotate_proxy()
                    continue
                return "unknown", last_detail

            text = resp.text or ""
            low = text.lower()

            if resp.status_code == 200:
                if any(m in low for m in self.CAPTCHA_MARKERS) and len(text) < 8000:
                    self._set_cooldown(30)
                    last_detail = "captcha"
                    if attempt < self.MAX_RETRIES:
                        continue
                    return "blocked", last_detail

                if any(m in low for m in self.NOT_FOUND_MARKERS):
                    return "available", "not found"

                # if page has a real profile payload
                if '"uniqueId":"' in text or "uniqueid" in low:
                    return "taken", "profile exists"

                # ambiguous 200 with tiny body
                if len(text) < 2000:
                    last_detail = "short body"
                    if attempt < self.MAX_RETRIES:
                        self._set_cooldown(3)
                        continue
                    return "unknown", last_detail

                return "taken", "profile exists"

            if resp.status_code == 404:
                return "available", "404"

            if resp.status_code == 429:
                wait = retry_after(resp, None)
                self._set_cooldown(wait)
                last_detail = f"429 wait {wait:g}s"
                if attempt < self.MAX_RETRIES:
                    continue
                return "blocked", last_detail

            if resp.status_code == 403:
                self._set_cooldown(20)
                if attempt < self.MAX_RETRIES:
                    self._rotate_proxy()
                    continue
                return "blocked", "403"

            if resp.status_code >= 500 and attempt < self.MAX_RETRIES:
                self._set_cooldown(2 ** attempt)
                continue

            return "unknown", f"http {resp.status_code}"

        return "unknown", last_detail


# =========================================================
# Scan
# =========================================================
def scan(checker: BaseChecker, names: List[str],
         skip_checked: Optional[bool] = None) -> int:
    store = checker.store
    checker.stop_event.clear()

    if skip_checked is None:
        skip_checked = checker.skip_checked

    if skip_checked:
        names = [n for n in names if n.lower() not in store.data["checked"]]

    valid: List[str] = []
    for n in names:
        n = n.lower()
        if checker.validate(n):
            valid.append(n)
        else:
            store.record(n, "invalid")

    if not valid:
        print(c(f"\n[{checker.platform}] no valid names to check.", C.YELLOW))
        return 0

    total = len(valid)
    found = 0
    done = 0
    lock = threading.Lock()
    start = time.monotonic()

    def task(name: str):
        nonlocal found, done
        if checker.stop_event.is_set():
            return
        status, detail = checker.check(name)
        if status == "blocked":
            checker.stop_event.set()
        with lock:
            store.record(name, status)
            done += 1
            if status == "available":
                found += 1

            elapsed = time.monotonic() - start
            rate = done / elapsed if elapsed > 0 else 0.0
            eta = (total - done) / rate if rate > 0 else 0.0
            pct = done / total * 100
            bar_width = 20
            filled = int(bar_width * done / total)
            bar = "#" * filled + "-" * (bar_width - filled)

            label = LABELS.get(status, status)
            line = (
                f"\r[{checker.platform}] [{bar}] {pct:5.1f}% "
                f"{done}/{total} | rate {rate:0.1f}/s | eta {human_time(eta)} "
                f"| +{found} {label} {name:<24.24}"
            )
            print(line, end="", flush=True)

    print(c(
        f"\n[{checker.platform}] scanning {total} names | "
        f"workers {checker.workers} | delay {checker.delay:g}s",
        C.CYAN,
    ))
    print("-" * 70)

    with ThreadPoolExecutor(max_workers=checker.workers) as pool:
        futures = [pool.submit(task, n) for n in valid]
        for f in as_completed(futures):
            f.result()

    print()

    if checker.stop_event.is_set():
        print(c(
            f"[!] {checker.platform} scan stopped (rate-limited). "
            "Unchecked names were not saved.",
            C.YELLOW,
        ))

    print(c(
        f"[{checker.platform}] session hits: {found} | "
        f"total available saved: {len(store.data['available'])}",
        C.GREEN,
    ))
    return found


# =========================================================
# Generation
# =========================================================
def generate_names(
    store: Store,
    lengths: List[int],
    alphabet: str,
    amount: int,
    validator,
    prefix: str = "",
    suffix: str = "",
    exclude: Optional[List[str]] = None,
) -> List[str]:
    used = store.seen()
    result: List[str] = []
    tries = 0
    limit = max(amount * 500, 2000)

    while len(result) < amount and tries < limit:
        tries += 1
        size = secrets.choice(lengths)
        core_len = size - len(prefix) - len(suffix)
        if core_len < 1:
            continue

        core = "".join(secrets.choice(alphabet) for _ in range(core_len))
        name = (prefix + core + suffix).lower()

        if name in used or not validator(name):
            continue
        if exclude and any(w in name for w in exclude):
            continue

        used.add(name)
        result.append(name)

    return result


# =========================================================
# Input helpers
# =========================================================
def ask_int(prompt: str, minimum: int, maximum: int,
            default: Optional[int] = None) -> Optional[int]:
    raw = input(prompt).strip()
    if not raw and default is not None:
        return default
    try:
        value = int(raw)
    except ValueError:
        print(c("Enter a valid number.", C.RED))
        return default
    if not minimum <= value <= maximum:
        print(c(f"Choose between {minimum} and {maximum}.", C.RED))
        return default
    return value


def ask_float(prompt: str, minimum: float, maximum: float,
              default: Optional[float] = None) -> Optional[float]:
    raw = input(prompt).strip()
    if not raw and default is not None:
        return default
    try:
        value = float(raw)
    except ValueError:
        print(c("Enter a valid number.", C.RED))
        return default
    if not minimum <= value <= maximum:
        print(c(f"Choose between {minimum} and {maximum}.", C.RED))
        return default
    return value


def choose_lengths(max_len: int) -> Optional[List[int]]:
    print("\n-- Username length --")
    print("1. 3 chars        (best for Discord rare)")
    print("2. 4 chars        (best for both)")
    print("3. 5 chars")
    print("4. 3-4            (best overall pick)")
    print("5. 3-5")
    print("6. 3-6")
    print(f"7. custom (2-{max_len})")

    choice = input("choice (default 4): ").strip() or "4"

    mapping = {
        "1": [3],
        "2": [4],
        "3": [5],
        "4": [3, 4],
        "5": [3, 4, 5],
        "6": [3, 4, 5, 6],
    }

    if choice in mapping:
        return mapping[choice]

    if choice == "7":
        lo = ask_int(f"min length (2-{max_len}): ", 2, max_len, 3)
        hi = ask_int(f"max length ({lo}-{max_len}): ", lo or 2, max_len, 4)
        if not lo or not hi:
            return None
        return list(range(lo, hi + 1))

    print(c("Invalid choice.", C.RED))
    return None


def choose_alphabet(platform: str) -> Optional[str]:
    print("\n-- Character set --")
    print("1. letters only            (a-z)      cleanest")
    print("2. digits only             (0-9)")
    print("3. letters + digits        (a-z0-9)   (best hit rate)")
    print("4. letters + digits + . _  (a-z0-9._) strictest")
    print("5. custom")

    choice = input("choice (default 3): ").strip() or "3"

    mapping = {
        "1": string.ascii_lowercase,
        "2": string.digits,
        "3": string.ascii_lowercase + string.digits,
        "4": string.ascii_lowercase + string.digits + "._",
    }

    if choice in mapping:
        return mapping[choice]

    if choice == "5":
        raw = input("allowed characters: ").strip().lower()
        if not raw:
            return None
        if platform == "discord":
            raw = "".join(ch for ch in raw if ch in string.ascii_lowercase + string.digits + "._")
        else:
            raw = "".join(ch for ch in raw if ch in string.ascii_lowercase + string.digits + "._")
        return "".join(dict.fromkeys(raw)) or None

    print(c("Invalid choice.", C.RED))
    return None


# =========================================================
# Actions
# =========================================================
def generate_and_scan(checker: BaseChecker):
    max_len = 32 if checker.platform == "discord" else 24
    validator = valid_discord if checker.platform == "discord" else valid_tiktok

    lengths = choose_lengths(max_len)
    if not lengths:
        return

    alphabet = choose_alphabet(checker.platform)
    if not alphabet:
        return

    amount = ask_int("\nhow many names to generate (default 100)? ",
                     1, 50000, 100)
    if not amount:
        return

    prefix = input("prefix (optional): ").strip().lower()
    suffix = input("suffix (optional): ").strip().lower()

    exclude_raw = input("excluded words, comma-separated (optional): ").strip()
    exclude = [w.strip().lower() for w in exclude_raw.split(",") if w.strip()] if exclude_raw else []

    names = generate_names(
        checker.store, lengths, alphabet, amount, validator, prefix, suffix, exclude
    )

    if not names:
        print(c("Could not generate new names. Widen the settings.", C.YELLOW))
        return

    print(c(f"\nGenerated {len(names)} names. Sample:", C.CYAN))
    for n in names[:10]:
        print("  " + n)
    if len(names) > 10:
        print(f"  ... and {len(names) - 10} more")

    if not yes(input("\nStart scan? (Y/n): ") or "y"):
        return

    scan(checker, names)


def scan_file(checker: BaseChecker):
    raw = input("\npath to TXT (one name per line): ").strip().strip('"').strip("'")
    path = Path(raw)

    if not path.is_file():
        print(c("File not found.", C.RED))
        return

    names = read_names(path)
    if not names:
        print(c("File is empty.", C.YELLOW))
        return

    scan(checker, names)


def scan_both(discord: BaseChecker, tiktok: BaseChecker):
    raw = input("\npath to TXT (checked on both platforms): ").strip().strip('"').strip("'")
    path = Path(raw)

    if not path.is_file():
        print(c("File not found.", C.RED))
        return

    names = read_names(path)
    if not names:
        print(c("File is empty.", C.YELLOW))
        return

    print(c(f"\nChecking {len(names)} names on Discord, then TikTok.", C.CYAN))
    scan(discord, names)
    scan(tiktok, names)
    show_intersection(discord, tiktok)


def retry_unknown(checker: BaseChecker):
    names = sorted(checker.store.data["unknown"])
    if not names:
        print(c(f"\n[{checker.platform}] no unknown names to retry.", C.YELLOW))
        return

    print(c(f"\n[{checker.platform}] retrying {len(names)} names.", C.CYAN))
    if not yes(input("type 'y' to continue: ") or "n"):
        print(c("Cancelled.", C.YELLOW))
        return

    scan(checker, names, skip_checked=False)


def show_stats(discord: BaseChecker, tiktok: BaseChecker):
    print("\n" + "=" * 60)
    for checker in (discord, tiktok):
        counts = checker.store.counts()
        print(c(f"[{checker.platform}]", C.BOLD))
        print(f"  available : {counts['available']}")
        print(f"  taken     : {counts['taken']}")
        print(f"  unknown   : {counts['unknown']}")
        print(f"  invalid   : {counts['invalid']}")
        print(f"  blocked   : {counts['blocked']}")
        print(f"  checked   : {counts['checked']}")
        print(f"  folder    : {checker.store.dir}")
    print("=" * 60)


def show_intersection(discord: BaseChecker, tiktok: BaseChecker):
    d = discord.store.data["available"]
    t = tiktok.store.data["available"]
    both = sorted(d & t)

    stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    out = RESULTS_DIR / f"both_available_{stamp}.txt"
    out.write_text("".join(f"{n}\n" for n in both), encoding="utf-8")

    print(c(f"\nAvailable on both platforms: {len(both)}", C.GREEN))
    if both:
        print(f"saved to: {out}")
        for n in both[:20]:
            print("  " + n)
        if len(both) > 20:
            print(f"  ... and {len(both) - 20} more")


def export_available(discord: BaseChecker, tiktok: BaseChecker):
    for checker in (discord, tiktok):
        if not checker.store.data["available"]:
            print(c(f"[{checker.platform}] nothing available to export.", C.YELLOW))
            continue
        path = checker.store.export_available()
        print(c(f"[{checker.platform}] exported -> {path}", C.GREEN))


# =========================================================
# Settings menu
# =========================================================
def settings_menu(settings: Dict) -> Dict:
    while True:
        print("\n" + "=" * 45)
        print("Settings")
        print("=" * 45)
        print(f"1. Discord delay      : {settings['discord_delay']:g}s (best 2.0)")
        print(f"2. TikTok delay       : {settings['tiktok_delay']:g}s (best 0.5)")
        print(f"3. Discord workers    : {settings['discord_workers']} (best 2)")
        print(f"4. TikTok workers     : {settings['tiktok_workers']} (best 3)")
        print(f"5. Skip checked names : {'yes' if settings['skip_checked'] else 'no'} (best yes)")
        print(f"6. Jitter             : {settings['jitter']:g} (best 0.25)")
        print("7. Back")

        choice = input("choice: ").strip()

        if choice == "1":
            v = ask_float("Discord delay (seconds): ", 0.1, 120, settings["discord_delay"])
            if v is not None:
                settings["discord_delay"] = v
        elif choice == "2":
            v = ask_float("TikTok delay (seconds): ", 0.1, 120, settings["tiktok_delay"])
            if v is not None:
                settings["tiktok_delay"] = v
        elif choice == "3":
            v = ask_int("Discord workers (1-10): ", 1, 10, settings["discord_workers"])
            if v is not None:
                settings["discord_workers"] = v
        elif choice == "4":
            v = ask_int("TikTok workers (1-10): ", 1, 10, settings["tiktok_workers"])
            if v is not None:
                settings["tiktok_workers"] = v
        elif choice == "5":
            settings["skip_checked"] = not settings["skip_checked"]
        elif choice == "6":
            v = ask_float("jitter 0-1: ", 0.0, 1.0, settings["jitter"])
            if v is not None:
                settings["jitter"] = v
        elif choice == "7":
            break

    save_config(settings)
    return settings


# =========================================================
# Build checkers
# =========================================================
def build_checkers(settings: Dict):
    pool = ProxyPool(PROXY_FILE)

    discord_store = Store(RESULTS_DIR, "discord")
    tiktok_store = Store(RESULTS_DIR, "tiktok")

    discord = DiscordChecker(
        discord_store, pool,
        workers=settings["discord_workers"],
        delay=settings["discord_delay"],
        jitter=settings["jitter"],
    )
    tiktok = TikTokChecker(
        tiktok_store, pool,
        workers=settings["tiktok_workers"],
        delay=settings["tiktok_delay"],
        jitter=settings["jitter"],
    )

    discord.skip_checked = settings["skip_checked"]
    tiktok.skip_checked = settings["skip_checked"]

    return discord, tiktok


# =========================================================
# Main menu
# =========================================================
def main():
    settings = load_config()
    discord, tiktok = build_checkers(settings)

    while True:
        print("\n" + "=" * 55)
        print(c("     Discord + TikTok Username Checker v4", C.BOLD))
        print("=" * 55)
        print("1. Discord  - generate + scan")
        print("2. Discord  - scan file")
        print("3. TikTok   - generate + scan")
        print("4. TikTok   - scan file")
        print("5. Both     - scan file on both + intersection")
        print("6. Retry unknown")
        print("7. Stats")
        print("8. Export available")
        print("9. Settings")
        print("0. Exit")

        choice = input("\nchoice (default 1): ").strip() or "1"

        if choice == "1":
            generate_and_scan(discord)
        elif choice == "2":
            scan_file(discord)
        elif choice == "3":
            generate_and_scan(tiktok)
        elif choice == "4":
            scan_file(tiktok)
        elif choice == "5":
            scan_both(discord, tiktok)
        elif choice == "6":
            print("\n1. Discord")
            print("2. TikTok")
            print("3. Both")
            sub = input("choice: ").strip()
            if sub == "1":
                retry_unknown(discord)
            elif sub == "2":
                retry_unknown(tiktok)
            elif sub == "3":
                retry_unknown(discord)
                retry_unknown(tiktok)
        elif choice == "7":
            show_stats(discord, tiktok)
        elif choice == "8":
            export_available(discord, tiktok)
        elif choice == "9":
            settings = settings_menu(settings)
            discord, tiktok = build_checkers(settings)
            print(c("Settings applied.", C.GREEN))
        elif choice == "0":
            print(c("Closed.", C.CYAN))
            break
        else:
            print(c("Invalid choice.", C.RED))


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print(c("\nStopped.", C.YELLOW))