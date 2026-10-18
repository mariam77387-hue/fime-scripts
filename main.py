#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Discord + TikTok Username Checker v3
pip install requests
"""

import os
import re
import sys
import time
import json
import string
import secrets
import threading
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import Optional, List, Dict, Set, Tuple

try:
    import requests
except ImportError:
    print("مكتبة requests غير مثبتة. نفّذ: pip install requests")
    sys.exit(1)


# =========================================================
# ألوان
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
    "available": c("[+] متاح", C.GREEN),
    "taken": c("[-] مأخوذ", C.RED),
    "unknown": c("[?] غير محسوم", C.YELLOW),
    "invalid": c("[!] صيغة مرفوضة", C.MAGENTA),
    "blocked": c("[!!] توقف", C.BLUE),
}


# =========================================================
# ثوابت
# =========================================================
BASE_DIR = Path(__file__).resolve().parent
RESULTS_DIR = BASE_DIR / "results"
PROXY_FILE = BASE_DIR / "proxies.txt"

DISCORD_API = "https://discord.com/api/v9/unique-username/username-attempt-unauthed"
TIKTOK_PROFILE = "https://www.tiktok.com/@{name}?lang=en"

DISCORD_RE = re.compile(r"^[a-z0-9_.]{2,32}$")
TIKTOK_RE = re.compile(r"^[a-zA-Z0-9._]{2,24}$")

UA = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
      "AppleWebKit/537.36 (KHTML, like Gecko) "
      "Chrome/124.0.0.0 Safari/537.36")


# =========================================================
# تحقق محلي
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
# أدوات مساعدة
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


# =========================================================
# بروكسيات
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
# تخزين
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


# =========================================================
# أساس الفاحص
# =========================================================
class BaseChecker:
    platform = ""
    default_delay = 1.0
    default_workers = 1

    def __init__(self, store: Store, proxy_pool: ProxyPool,
                 workers: Optional[int] = None, delay: Optional[float] = None):
        self.store = store
        self.proxy_pool = proxy_pool
        self.workers = max(1, int(workers or self.default_workers))
        self.delay = max(0.05, float(delay if delay is not None else self.default_delay))
        self.max_retries = 3
        self.skip_checked = True
        self.stop_event = threading.Event()

        self._rate_lock = threading.Lock()
        self._cooldown_lock = threading.Lock()
        self._last_request = 0.0
        self._cooldown_until = 0.0
        self._local = threading.local()

    @property
    def session(self) -> requests.Session:
        s = getattr(self._local, "session", None)
        if s is None:
            s = self._make_session()
            self._local.session = s
        return s

    def _make_session(self) -> requests.Session:
        s = requests.Session()
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

    def _wait_turn(self):
        with self._rate_lock:
            now = time.monotonic()
            wait = max(
                self.delay - (now - self._last_request),
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

    def validate(self, name: str) -> bool:
        raise NotImplementedError

    def check(self, name: str) -> Tuple[str, str]:
        raise NotImplementedError


# =========================================================
# Discord
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
            "Referer": "https://discord.com/",
        }

    def validate(self, name: str) -> bool:
        return valid_discord(name)

    def check(self, name: str) -> Tuple[str, str]:
        payload = {"username": name}
        last_detail = "unknown"

        for attempt in range(self.max_retries + 1):
            self._wait_turn()
            try:
                resp = self.session.post(DISCORD_API, json=payload, timeout=15)
            except requests.RequestException as e:
                last_detail = f"network: {e.__class__.__name__}"
                if attempt < self.max_retries:
                    self._set_cooldown(min(2 ** attempt, 30))
                    self._rotate_proxy()
                    continue
                return "unknown", last_detail

            body = parse_json(resp)

            if resp.status_code == 200 and isinstance(body, dict) and isinstance(body.get("taken"), bool):
                return ("taken" if body["taken"] else "available"), "ok"

            if resp.status_code == 429:
                wait = retry_after(resp, body)
                self._set_cooldown(wait)
                last_detail = f"429 wait {wait:g}s"
                if attempt < self.max_retries:
                    continue
                return "blocked", last_detail

            if resp.status_code in (401, 403):
                return "blocked", f"http {resp.status_code}"

            if resp.status_code == 400:
                return "invalid", snippet(resp)

            if resp.status_code >= 500 and attempt < self.max_retries:
                self._set_cooldown(2 ** attempt)
                continue

            return "unknown", f"http {resp.status_code}"

        return "unknown", last_detail


# =========================================================
# TikTok
# =========================================================
class TikTokChecker(BaseChecker):
    platform = "tiktok"
    default_delay = 0.5
    default_workers = 3

    def headers(self):
        return {
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8",
            "Accept-Language": "en-US,en;q=0.9",
            "User-Agent": UA,
            "Sec-Fetch-Dest": "document",
            "Sec-Fetch-Mode": "navigate",
            "Sec-Fetch-Site": "none",
            "Upgrade-Insecure-Requests": "1",
        }

    def validate(self, name: str) -> bool:
        return valid_tiktok(name)

    def check(self, name: str) -> Tuple[str, str]:
        if name.isdigit():
            return "invalid", "numeric only"

        url = TIKTOK_PROFILE.format(name=name)
        last_detail = "unknown"

        for attempt in range(self.max_retries + 1):
            self._wait_turn()
            try:
                resp = self.session.get(url, timeout=15, allow_redirects=True)
            except requests.RequestException as e:
                last_detail = f"network: {e.__class__.__name__}"
                if attempt < self.max_retries:
                    self._set_cooldown(min(2 ** attempt, 30))
                    self._rotate_proxy()
                    continue
                return "unknown", last_detail

            text = resp.text or ""
            low = text.lower()

            if resp.status_code == 200:
                if ("captcha" in low or "verify" in low) and len(text) < 6000:
                    self._set_cooldown(30)
                    last_detail = "captcha/verify"
                    if attempt < self.max_retries:
                        continue
                    return "blocked", last_detail

                if (
                    "couldn't find this account" in low
                    or "user not found" in low
                    or "page not available" in low
                ):
                    return "available", "not found page"

                return "taken", "profile exists"

            if resp.status_code == 404:
                return "available", "404"

            if resp.status_code == 429:
                wait = retry_after(resp, None)
                self._set_cooldown(wait)
                last_detail = f"429 wait {wait:g}s"
                if attempt < self.max_retries:
                    continue
                return "blocked", last_detail

            if resp.status_code == 403:
                self._set_cooldown(20)
                return "blocked", "403"

            if resp.status_code >= 500 and attempt < self.max_retries:
                self._set_cooldown(2 ** attempt)
                continue

            return "unknown", f"http {resp.status_code}"

        return "unknown", last_detail


# =========================================================
# فحص
# =========================================================
def scan(checker: BaseChecker, names: List[str], skip_checked: Optional[bool] = None) -> int:
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
        print(c(f"\n[{checker.platform}] لا توجد أسماء صالحة للفحص.", C.YELLOW))
        return 0

    total = len(valid)
    found = 0
    done = 0
    lock = threading.Lock()

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
            label = LABELS.get(status, status)
            print(
                f"\r[{checker.platform}] [{done}/{total}] {name} -> {label} | {detail}"
                + " " * 30,
                end="",
                flush=True,
            )

    print(
        c(
            f"\n[{checker.platform}] فحص {total} اسمًا | عمال: {checker.workers} | تأخير: {checker.delay:g}s",
            C.CYAN,
        )
    )
    print("-" * 70)

    with ThreadPoolExecutor(max_workers=checker.workers) as pool:
        futures = [pool.submit(task, n) for n in valid]
        for f in as_completed(futures):
            f.result()

    print()

    if checker.stop_event.is_set():
        print(
            c(
                f"[!] توقف فحص {checker.platform} بسبب تقييد الطلبات. "
                "الأسماء غير المفحوصة لم تُحفظ.",
                C.YELLOW,
            )
        )

    print(
        c(
            f"[{checker.platform}] متاح في الجلسة: {found} | "
            f"إجمالي المتاح المحفوظ: {len(store.data['available'])}",
            C.GREEN,
        )
    )
    return found


# =========================================================
# توليد
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
    limit = max(amount * 500, 1000)

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
# مدخلات
# =========================================================
def ask_int(prompt: str, minimum: int, maximum: int, default: Optional[int] = None) -> Optional[int]:
    raw = input(prompt).strip()
    if not raw and default is not None:
        return default
    try:
        value = int(raw)
    except ValueError:
        print(c("أدخل رقمًا صحيحًا.", C.RED))
        return default
    if not minimum <= value <= maximum:
        print(c(f"اختر من {minimum} إلى {maximum}.", C.RED))
        return default
    return value


def ask_float(prompt: str, minimum: float, maximum: float, default: Optional[float] = None) -> Optional[float]:
    raw = input(prompt).strip()
    if not raw and default is not None:
        return default
    try:
        value = float(raw)
    except ValueError:
        print(c("أدخل رقمًا صحيحًا.", C.RED))
        return default
    if not minimum <= value <= maximum:
        print(c(f"اختر من {minimum} إلى {maximum}.", C.RED))
        return default
    return value


def choose_lengths(max_len: int) -> Optional[List[int]]:
    print("\nاختر الطول:")
    print("1. 3 أحرف")
    print("2. 4 أحرف")
    print("3. 5 أحرف")
    print("4. 3-4")
    print("5. 3-5")
    print("6. 3-6")
    print(f"7. مخصص (2-{max_len})")

    choice = input("اختيارك: ").strip()

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
        lo = ask_int("أصغر طول: ", 2, max_len)
        hi = ask_int("أكبر طول: ", lo or 2, max_len)
        if not lo or not hi:
            return None
        return list(range(lo, hi + 1))

    print(c("اختيار غير صحيح.", C.RED))
    return None


def choose_alphabet() -> Optional[str]:
    print("\nنوع الأحرف:")
    print("1. أحرف فقط (a-z)")
    print("2. أرقام فقط (0-9)")
    print("3. أحرف وأرقام (a-z0-9)")
    print("4. أحرف وأرقام ونقطة وشرطة سفلية (a-z0-9._)")
    print("5. مخصص")

    choice = input("اختيارك: ").strip()

    mapping = {
        "1": string.ascii_lowercase,
        "2": string.digits,
        "3": string.ascii_lowercase + string.digits,
        "4": string.ascii_lowercase + string.digits + "._",
    }

    if choice in mapping:
        return mapping[choice]

    if choice == "5":
        raw = input("اكتب الأحرف المسموحة: ").strip().lower()
        if not raw:
            return None
        return "".join(dict.fromkeys(raw))

    print(c("اختيار غير صحيح.", C.RED))
    return None


# =========================================================
# عمليات
# =========================================================
def generate_and_scan(checker: BaseChecker):
    max_len = 32 if checker.platform == "discord" else 24
    validator = valid_discord if checker.platform == "discord" else valid_tiktok

    lengths = choose_lengths(max_len)
    if not lengths:
        return

    alphabet = choose_alphabet()
    if not alphabet:
        return

    amount = ask_int("\nكم اسمًا تريد توليده؟ ", 1, 50000, 100)
    if not amount:
        return

    prefix = input("بادئة (اختياري): ").strip().lower()
    suffix = input("لاحقة (اختياري): ").strip().lower()

    exclude_raw = input("كلمات مستبعدة مفصولة بفاصلة (اختياري): ").strip()
    exclude = [w.strip().lower() for w in exclude_raw.split(",") if w.strip()] if exclude_raw else []

    names = generate_names(
        checker.store, lengths, alphabet, amount, validator, prefix, suffix, exclude
    )

    if not names:
        print(c("تعذر توليد أسماء جديدة. جرّب إعدادات أوسع.", C.YELLOW))
        return

    print(c(f"\nتم توليد {len(names)} اسمًا. عينة:", C.CYAN))
    for n in names[:10]:
        print("  " + n)
    if len(names) > 10:
        print(f"  ... و{len(names) - 10} غيرها")

    if input("\nابدأ الفحص؟ (نعم/لا): ").strip().lower() not in ("نعم", "yes", "y"):
        return

    scan(checker, names)


def scan_file(checker: BaseChecker):
    raw = input("\nمسار ملف TXT (اسم في كل سطر): ").strip().strip('"').strip("'")
    path = Path(raw)

    if not path.is_file():
        print(c("الملف غير موجود.", C.RED))
        return

    names = read_names(path)
    if not names:
        print(c("الملف فارغ.", C.YELLOW))
        return

    scan(checker, names)


def scan_both(discord: BaseChecker, tiktok: BaseChecker):
    raw = input("\nمسار ملف TXT لفحصه على المنصتين: ").strip().strip('"').strip("'")
    path = Path(raw)

    if not path.is_file():
        print(c("الملف غير موجود.", C.RED))
        return

    names = read_names(path)
    if not names:
        print(c("الملف فارغ.", C.YELLOW))
        return

    print(c(f"\nسيتم فحص {len(names)} اسمًا على Discord ثم TikTok.", C.CYAN))
    scan(discord, names)
    scan(tiktok, names)
    show_intersection(discord, tiktok)


def retry_unknown(checker: BaseChecker):
    names = sorted(checker.store.data["unknown"])
    if not names:
        print(c(f"\n[{checker.platform}] لا توجد أسماء غير محسومة.", C.YELLOW))
        return

    print(c(f"\n[{checker.platform}] إعادة فحص {len(names)} اسمًا.", C.CYAN))
    if input("اكتب نعم للمتابعة: ").strip().lower() not in ("نعم", "yes", "y"):
        print(c("تم الإلغاء.", C.YELLOW))
        return

    scan(checker, names, skip_checked=False)


def show_stats(discord: BaseChecker, tiktok: BaseChecker):
    print("\n" + "=" * 60)
    for checker in (discord, tiktok):
        counts = checker.store.counts()
        print(c(f"[{checker.platform}]", C.BOLD))
        print(f"  المتاح:        {counts['available']}")
        print(f"  المأخوذ:       {counts['taken']}")
        print(f"  غير المحسوم:   {counts['unknown']}")
        print(f"  مرفوض صيغةً:   {counts['invalid']}")
        print(f"  موقوف:         {counts['blocked']}")
        print(f"  سبق فحصه:      {counts['checked']}")
        print(f"  المجلد:        {checker.store.dir}")
    print("=" * 60)


def show_intersection(discord: BaseChecker, tiktok: BaseChecker):
    d = discord.store.data["available"]
    t = tiktok.store.data["available"]
    both = sorted(d & t)

    out = RESULTS_DIR / "both_available.txt"
    out.write_text("".join(f"{n}\n" for n in both), encoding="utf-8")

    print(c(f"\nالمتاح على المنصتين معًا: {len(both)}", C.GREEN))
    if both:
        print(f"حُفظ في: {out}")
        for n in both[:20]:
            print("  " + n)
        if len(both) > 20:
            print(f"  ... و{len(both) - 20} غيرها")


# =========================================================
# إعدادات
# =========================================================
def settings_menu(settings: Dict) -> Dict:
    while True:
        print("\n" + "=" * 45)
        print("الإعدادات")
        print("=" * 45)
        print(f"1. تأخير Discord: {settings['discord_delay']:g}s")
        print(f"2. تأخير TikTok: {settings['tiktok_delay']:g}s")
        print(f"3. عمال Discord: {settings['discord_workers']}")
        print(f"4. عمال TikTok: {settings['tiktok_workers']}")
        print(f"5. تخطي المفحوص: {'نعم' if settings['skip_checked'] else 'لا'}")
        print("6. رجوع")

        choice = input("اختيارك: ").strip()

        if choice == "1":
            v = ask_float("تأخير Discord بالثواني: ", 0.1, 60, settings["discord_delay"])
            if v is not None:
                settings["discord_delay"] = v
        elif choice == "2":
            v = ask_float("تأخير TikTok بالثواني: ", 0.1, 60, settings["tiktok_delay"])
            if v is not None:
                settings["tiktok_delay"] = v
        elif choice == "3":
            v = ask_int("عمال Discord: ", 1, 10, settings["discord_workers"])
            if v is not None:
                settings["discord_workers"] = v
        elif choice == "4":
            v = ask_int("عمال TikTok: ", 1, 10, settings["tiktok_workers"])
            if v is not None:
                settings["tiktok_workers"] = v
        elif choice == "5":
            settings["skip_checked"] = not settings["skip_checked"]
        elif choice == "6":
            break

    return settings


# =========================================================
# بناء الفاحصات
# =========================================================
def build_checkers(settings: Dict):
    pool = ProxyPool(PROXY_FILE)

    discord_store = Store(RESULTS_DIR, "discord")
    tiktok_store = Store(RESULTS_DIR, "tiktok")

    discord = DiscordChecker(
        discord_store, pool,
        workers=settings["discord_workers"],
        delay=settings["discord_delay"],
    )
    tiktok = TikTokChecker(
        tiktok_store, pool,
        workers=settings["tiktok_workers"],
        delay=settings["tiktok_delay"],
    )

    discord.skip_checked = settings["skip_checked"]
    tiktok.skip_checked = settings["skip_checked"]

    return discord, tiktok


# =========================================================
# القائمة الرئيسية
# =========================================================
def main():
    settings = {
        "discord_delay": 2.0,
        "tiktok_delay": 0.5,
        "discord_workers": 2,
        "tiktok_workers": 3,
        "skip_checked": True,
    }

    discord, tiktok = build_checkers(settings)

    while True:
        print("\n" + "=" * 50)
        print(c("      Discord + TikTok Username Checker v3", C.BOLD))
        print("=" * 50)
        print("1. Discord — توليد وفحص")
        print("2. Discord — فحص من ملف TXT")
        print("3. TikTok — توليد وفحص")
        print("4. TikTok — فحص من ملف TXT")
        print("5. المنصتان — فحص ملف واحد + تقاطع المتاح")
        print("6. إعادة فحص غير المحسوم")
        print("7. الإحصائيات")
        print("8. الإعدادات")
        print("9. خروج")

        choice = input("\nاختيارك: ").strip()

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
            print("3. الاثنان")
            sub = input("اختيارك: ").strip()
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
            settings = settings_menu(settings)
            discord, tiktok = build_checkers(settings)
            print(c("تم تطبيق الإعدادات.", C.GREEN))
        elif choice == "9":
            print(c("تم إغلاق الأداة.", C.CYAN))
            break
        else:
            print(c("اختيار غير صحيح.", C.RED))


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print(c("\nتم إيقاف الأداة.", C.YELLOW))