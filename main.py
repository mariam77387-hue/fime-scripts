
import json
import random
import string
import time
import os
import urllib.request
import urllib.error
from datetime import datetime

# ==============================================
# PRO USERNAME FINDER - Replit / main.py
# توليد وفحص أسماء المستخدمين
# ==============================================

API_URL = (
    "https://discord.com/api/v9/"
    "unique-username/username-attempt-unauthed"
)

OUTPUT_DIR = "results"
os.makedirs(OUTPUT_DIR, exist_ok=True)

LETTERS = string.ascii_lowercase
DIGITS = string.digits
ALNUM = LETTERS + DIGITS

HEADERS = {
    "Content-Type": "application/json",
    "Accept": "application/json",
    "User-Agent": "UsernameAvailabilityChecker/1.0",
}

# إعادة المحاولة للأخطاء المؤقتة
RETRIES = 3
BASE_DELAY = 2.0
MAX_CONSECUTIVE_SERVICE_ERRORS = 10


def timestamp():
    return datetime.now().strftime("%Y%m%d_%H%M%S")


def valid_username(name):
    if not 2 <= len(name) <= 32:
        return False
    if any(c not in ALNUM + "._" for c in name):
        return False
    if name.startswith(".") or name.endswith("."):
        return False
    if ".." in name:
        return False
    return True


def generate_username(length, letters_only=False):
    chars = LETTERS if letters_only else ALNUM
    return "".join(random.choices(chars, k=length))


def request_check(name):
    """
    ترجع:
      available / taken / invalid / unknown / rate_limited
    مع مدة الانتظار إن كانت الخدمة قد حددتها.
    """
    payload = json.dumps(
        {"username": name},
        separators=(",", ":"),
    ).encode("utf-8")

    request = urllib.request.Request(
        API_URL,
        data=payload,
        headers=HEADERS,
        method="POST",
    )

    try:
        with urllib.request.urlopen(request, timeout=15) as response:
            body = response.read().decode("utf-8", errors="replace")
            data = json.loads(body)

        if not isinstance(data, dict):
            return "unknown", 0

        taken = data.get("taken")

        if taken is False:
            return "available", 0

        if taken is True:
            return "taken", 0

        return "unknown", 0

    except urllib.error.HTTPError as error:
        body = error.read().decode("utf-8", errors="replace")

        if error.code == 429:
            wait_seconds = 0

            retry_after = error.headers.get("Retry-After")
            if retry_after:
                try:
                    wait_seconds = float(retry_after)
                except ValueError:
                    pass

            try:
                data = json.loads(body)
                wait_seconds = max(
                    wait_seconds,
                    float(data.get("retry_after", 0)),
                )
            except (ValueError, TypeError, json.JSONDecodeError):
                pass

            return "rate_limited", max(wait_seconds, 1)

        if error.code in (400, 422):
            return "invalid", 0

        return "unknown", 0

    except (
        urllib.error.URLError,
        TimeoutError,
        OSError,
        ValueError,
    ):
        return "unknown", 0


def check_with_retries(name):
    """إعادة المحاولة عند تعذّر الفحص."""
    for attempt in range(RETRIES):
        status, wait_seconds = request_check(name)

        if status == "rate_limited":
            print(
                f"\n[انتظار] الخدمة حددت الطلبات. "
                f"الانتظار {wait_seconds:.1f} ثانية."
            )
            time.sleep(wait_seconds)
            # إعادة فحص الاسم نفسه بعد انتهاء الانتظار
            continue

        if status != "unknown":
            return status

        if attempt < RETRIES - 1:
            delay = BASE_DELAY * (2 ** attempt)
            print(
                f"[إعادة محاولة {attempt + 1}/{RETRIES - 1}] "
                f"تعذر التأكد من {name}، انتظار {delay:.0f} ث."
            )
            time.sleep(delay)

    return "unknown"


def save_available(names, filepath):
    with open(filepath, "w", encoding="utf-8") as file:
        file.write("\n".join(names))
        if names:
            file.write("\n")


def append_line(filepath, line):
    with open(filepath, "a", encoding="utf-8") as file:
        file.write(line + "\n")


def main():
    print("=" * 54)
    print("       PRO USERNAME FINDER")
    print("       أداة البحث عن يوزرات متاحة")
    print("=" * 54)
    print("تستمر الأداة حتى تجد العدد المطلوب.")
    print("أوقفها يدويًا باستخدام Ctrl+C عند الحاجة.\n")

    try:
        target = int(input("كم يوزر متاح تريد العثور عليه؟ (1-100): "))
        if not 1 <= target <= 100:
            print("أدخل عددًا بين 1 و100.")
            return
    except ValueError:
        print("الرجاء إدخال رقم صحيح.")
        return

    print("\n1 - ثلاثة أحرف")
    print("2 - أربعة أحرف")
    print("3 - خليط من 3 و4 أحرف")

    choice = input("اختر الطول: ").strip()
    if choice not in ("1", "2", "3"):
        print("اختيار غير صحيح.")
        return

    letters_only = (
        input("حروف فقط دون أرقام؟ (y/n): ").strip().lower() == "y"
    )

    if choice == "1":
        lengths = [3]
    elif choice == "2":
        lengths = [4]
    else:
        lengths = [3, 4]

    charset = LETTERS if letters_only else ALNUM

    total_possible = sum(
        len(charset) ** length for length in lengths
    )

    stamp = timestamp()
    available_path = os.path.join(
        OUTPUT_DIR, f"available_{stamp}.txt"
    )
    unknown_path = os.path.join(
        OUTPUT_DIR, f"unknown_{stamp}.txt"
    )

    found = []
    seen = set()
    attempts = 0
    consecutive_errors = 0

    print("\nبدأ البحث المستمر...")
    print(f"الهدف: {target} أسماء مؤكدة بحسب استجابة الخدمة.")
    print("النتائج تحفظ فور العثور عليها.\n")

    try:
        while len(found) < target:
            if len(seen) >= total_possible:
                print("\nانتهت جميع التركيبات الممكنة لهذا الاختيار.")
                break

            length = random.choice(lengths)
            name = generate_username(length, letters_only)

            if name in seen or not valid_username(name):
                continue

            seen.add(name)
            attempts += 1

            status = check_with_retries(name)

            print(
                f"[محاولة {attempts}] {name} -> {status}"
            )

            if status == "available":
                found.append(name)
                save_available(found, available_path)
                consecutive_errors = 0

                print(
                    f"\n[متاح بحسب الاستجابة] {name}"
                    f" | العدد المكتشف: {len(found)}/{target}\n"
                )

            elif status == "taken":
                consecutive_errors = 0

            elif status == "invalid":
                consecutive_errors += 1
                append_line(
                    unknown_path,
                    f"{name} | invalid_or_rejected",
                )

            else:
                consecutive_errors += 1
                append_line(
                    unknown_path,
                    f"{name} | {status}",
                )

            if consecutive_errors >= MAX_CONSECUTIVE_SERVICE_ERRORS:
                print(
                    "\nتوقفت الأداة لأن الفحص فشل مرارًا. "
                    "قد تكون الواجهة غير متاحة أو ترفض الطلبات."
                )
                print("لم يتم اعتبار الأسماء غير المؤكدة متاحة.")
                break

            # إيقاع هادئ للطلبات، دون تجاوز حدود الخدمة
            time.sleep(2)

    except KeyboardInterrupt:
        print("\nأوقف المستخدم البحث. حفظ النتائج المكتشفة.")

    finally:
        save_available(found, available_path)

        print("\n" + "=" * 54)
        print(f"إجمالي المحاولات: {attempts}")
        print(f"الأسماء المتاحة بحسب الاستجابة: {len(found)}")
        print(f"ملف الأسماء: {available_path}")
        print(f"ملف الحالات غير المؤكدة: {unknown_path}")
        print("=" * 54)

        if found:
            print("\nالأسماء التي أعادت الخدمة أنها غير مأخوذة:")
            for name in found:
                print("  " + name)

        print(
            "\nالإتاحة قد تتغير قبل تسجيل الاسم؛ "
            "تحقق منه في ديسكورد قبل الاعتماد عليه."
        )


if __name__ == "__main__":
    main()
