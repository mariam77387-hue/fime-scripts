import os
import re
import time
import string
import secrets
from pathlib import Path

import requests

# =========================================================
# Discord Username Checker v2
# ملاحظة: نقطة الفحص غير رسمية وقد تتغير أو تتوقف في أي وقت.
# =========================================================

API_URL = "https://discord.com/api/v9/unique-username/username-attempt-unauthed"
USER_AGENT = "DiscordUsernameChecker/2.0 (personal use)"

REQUEST_DELAY = 2.0        # ثواني بين كل اسم والذي بعده
TIMEOUT = 15
MAX_RETRIES = 2
MAX_RETRY_WAIT = 120       # أقصى مدة انتظار مقبولة عند 429
MAX_GENERATE = 10000

BASE_DIR = Path(__file__).resolve().parent
RESULTS_DIR = BASE_DIR / "results"
FILES = {
    "available": RESULTS_DIR / "available.txt",
    "taken": RESULTS_DIR / "taken.txt",
    "unknown": RESULTS_DIR / "unknown.txt",
    "checked": RESULTS_DIR / "checked.txt",
}

USERNAME_RE = re.compile(r"[a-z0-9_.]{2,32}")

LENGTH_OPTIONS = {
    "1": ("ثلاثة أحرف", [3]),
    "2": ("أربعة أحرف", [4]),
    "3": ("ثلاثة أو أربعة أحرف", [3, 4]),
}

CHARSET_OPTIONS = {
    "1": ("أحرف إنجليزية فقط", string.ascii_lowercase),
    "2": ("أرقام فقط", string.digits),
    "3": ("أحرف وأرقام", string.ascii_lowercase + string.digits),
}


# =========================================================
# التخزين
# =========================================================

class Store:
    def __init__(self):
        RESULTS_DIR.mkdir(parents=True, exist_ok=True)
        self.data = {key: self._read(path) for key, path in FILES.items()}

    @staticmethod
    def _read(path):
        if not path.exists():
            return set()
        with path.open("r", encoding="utf-8") as file:
            return {line.strip().lower() for line in file if line.strip()}

    def _append(self, key, name):
        if name in self.data[key]:
            return
        self.data[key].add(name)
        with FILES[key].open("a", encoding="utf-8") as file:
            file.write(name + "\n")

    def record(self, name, status):
        self._append(status, name)
        self._append("checked", name)

    def remove_unknown(self, name):
        if name not in self.data["unknown"]:
            return
        self.data["unknown"].discard(name)
        tmp = FILES["unknown"].with_suffix(".tmp")
        tmp.write_text(
            "".join(f"{n}\n" for n in sorted(self.data["unknown"])),
            encoding="utf-8",
        )
        os.replace(tmp, FILES["unknown"])

    def seen(self):
        return (
            self.data["checked"]
            | self.data["available"]
            | self.data["taken"]
            | self.data["unknown"]
        )


# =========================================================
# التحقق المحلي من الصيغة (ليس فحص الإتاحة)
# =========================================================

def is_valid(name):
    if not USERNAME_RE.fullmatch(name):
        return False
    if name.startswith(".") or name.endswith(".") or ".." in name:
        return False
    # قاعدة ديسكورد: اليوزر لا يحتوي على كلمة discord
    if "discord" in name:
        return False
    return True


# =========================================================
# الاتصال بديسكورد
# =========================================================

def make_session():
    session = requests.Session()
    session.headers.update({
        "Content-Type": "application/json",
        "Accept": "application/json",
        "User-Agent": USER_AGENT,
    })
    return session


def snippet(resp):
    text = (resp.text or "").strip().replace("\n", " ")
    return text[:200] if text else "(رد فارغ)"


def parse_json(resp):
    try:
        return resp.json()
    except ValueError:
        return None


def retry_after(resp, body):
    value = resp.headers.get("Retry-After")
    if value is None and isinstance(body, dict):
        value = body.get("retry_after")
    try:
        return max(1.0, float(value))
    except (TypeError, ValueError):
        return 10.0


def check_username(session, name):
    for attempt in range(MAX_RETRIES + 1):
        last = attempt == MAX_RETRIES

        try:
            resp = session.post(API_URL, json={"username": name}, timeout=TIMEOUT)
        except requests.RequestException as err:
            if not last:
                time.sleep(REQUEST_DELAY * (attempt + 1))
                continue
            return "unknown", f"خطأ اتصال: {err}"

        body = parse_json(resp)

        if resp.status_code == 200 and isinstance(body, dict):
            taken = body.get("taken")
            if isinstance(taken, bool):
                return ("taken" if taken else "available"), "نتيجة واضحة"

        if resp.status_code == 429:
            wait = retry_after(resp, body)
            if not last and wait <= MAX_RETRY_WAIT:
                print(f"\n    [!] ديسكورد طلب انتظار {wait:g} ثانية...")
                time.sleep(wait)
                continue
            return "blocked", "تقييد طلبات (429)"

        if resp.status_code in (401, 403):
            return "blocked", f"HTTP {resp.status_code}: {snippet(resp)}"

        if resp.status_code == 400:
            return "invalid", f"ديسكورد رفض الصيغة: {snippet(resp)}"

        if resp.status_code >= 500 and not last:
            time.sleep(REQUEST_DELAY * (attempt + 1))
            continue

        return "unknown", f"HTTP {resp.status_code}: {snippet(resp)}"

    return "unknown", "انتهت المحاولات"


# =========================================================
# الفحص
# =========================================================

LABELS = {
    "available": "[+] متاح",
    "taken": "[-] مأخوذ",
    "unknown": "[?] غير محسوم",
    "invalid": "[!] مرفوض صيغةً",
    "blocked": "[!!] توقف الفحص",
}


def scan(store, session, names, skip_checked=True):
    total = len(names)
    found = 0

    print(f"\nبدء الفحص: {total} اسمًا")
    print("-" * 60)

    for index, name in enumerate(names, start=1):
        if skip_checked and name in store.data["checked"]:
            print(f"[تخطي] {name} سبق فحصه")
            continue

        if not is_valid(name):
            print(f"[!] صيغة غير صالحة محليًا: {name}")
            continue

        print(f"[{index}/{total}] {name} ...", end=" ", flush=True)
        status, detail = check_username(session, name)
        print(f"{LABELS[status]} | {detail}")

        if status == "blocked":
            print("\n[!] ديسكورد رفض الطلبات، تم إيقاف الفحص. لم يُحفظ هذا الاسم.")
            break

        if status in ("available", "taken", "unknown"):
            store.record(name, status)
            store.remove_unknown(name) if status != "unknown" else None

        if status == "available":
            found += 1

        if index < total:
            time.sleep(REQUEST_DELAY)

    print("\n" + "=" * 60)
    print(f"متاح حسب الاستجابة في هذه الجلسة: {found}")
    print(f"إجمالي المتاح المحفوظ: {len(store.data['available'])}")
    print(f"إجمالي المأخوذ المحفوظ: {len(store.data['taken'])}")
    print(f"إجمالي غير المحسوم: {len(store.data['unknown'])}")
    print(f"مجلد النتائج: {RESULTS_DIR}")
    print("=" * 60)


# =========================================================
# القوائم والتوليد
# =========================================================

def ask_choice(title, options):
    print(f"\n{title}")
    for key, (label, _) in options.items():
        print(f"{key}. {label}")
    choice = input("اختيارك: ").strip()
    if choice not in options:
        print("اختيار غير صحيح.")
        return None
    return options[choice][1]


def generate(store, lengths, alphabet, amount):
    used = store.seen()
    result = []
    tries = 0
    limit = amount * 200

    while len(result) < amount and tries < limit:
        tries += 1
        size = secrets.choice(lengths)
        name = "".join(secrets.choice(alphabet) for _ in range(size))

        if name in used or not is_valid(name):
            continue

        used.add(name)
        result.append(name)

    return result


def generate_and_scan(store, session):
    lengths = ask_choice("اختر طول اليوزر:", LENGTH_OPTIONS)
    if not lengths:
        return

    alphabet = ask_choice("اختر نوع الأحرف:", CHARSET_OPTIONS)
    if not alphabet:
        return

    try:
        amount = int(input("\nكم اسمًا تريد توليده؟ ").strip())
    except ValueError:
        print("أدخل رقمًا صحيحًا.")
        return

    if not 1 <= amount <= MAX_GENERATE:
        print(f"اختر رقمًا من 1 إلى {MAX_GENERATE}.")
        return

    names = generate(store, lengths, alphabet, amount)
    if not names:
        print("تعذر توليد أسماء جديدة ضمن الإعدادات الحالية.")
        return

    print(f"\nتم توليد {len(names)} اسمًا جديدًا.")
    scan(store, session, names)


def scan_file(store, session):
    raw = input("\nمسار ملف TXT (اسم في كل سطر): ").strip().strip('"')
    path = Path(raw)

    if not path.is_file():
        print("الملف غير موجود.")
        return

    try:
        text = path.read_text(encoding="utf-8-sig")
    except OSError as err:
        print(f"تعذر قراءة الملف: {err}")
        return

    names = list(dict.fromkeys(
        line.strip().lower() for line in text.splitlines() if line.strip()
    ))

    if not names:
        print("الملف فارغ.")
        return

    scan(store, session, names)


def retry_unknown(store, session):
    names = sorted(store.data["unknown"])
    if not names:
        print("\nلا توجد أسماء غير محسومة.")
        return

    print(f"\nستتم إعادة فحص {len(names)} اسمًا.")
    if input("اكتب نعم للمتابعة: ").strip() != "نعم":
        print("تم الإلغاء.")
        return

    scan(store, session, names, skip_checked=False)


def show_statistics(store):
    print("\n========== الإحصائيات ==========")
    print(f"المتاح حسب الاستجابة: {len(store.data['available'])}")
    print(f"المأخوذ حسب الاستجابة: {len(store.data['taken'])}")
    print(f"غير المحسوم: {len(store.data['unknown'])}")
    print(f"سبق فحصه: {len(store.data['checked'])}")
    print(f"مجلد النتائج: {RESULTS_DIR}")
    print("================================")


# =========================================================
# القائمة الرئيسية
# =========================================================

def main():
    store = Store()
    session = make_session()

    try:
        while True:
            print("\n" + "=" * 45)
            print("      Discord Username Checker v2")
            print("=" * 45)
            print("1. توليد يوزرات وفحصها")
            print("2. فحص قائمة من ملف TXT")
            print("3. إعادة فحص النتائج غير المحسومة")
            print("4. عرض الإحصائيات")
            print("5. خروج")

            choice = input("\nاختيارك: ").strip()

            if choice == "1":
                generate_and_scan(store, session)
            elif choice == "2":
                scan_file(store, session)
            elif choice == "3":
                retry_unknown(store, session)
            elif choice == "4":
                show_statistics(store)
            elif choice == "5":
                print("تم إغلاق الأداة.")
                break
            else:
                print("اختيار غير صحيح.")
    finally:
        session.close()


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\nتم إيقاف الأداة.")