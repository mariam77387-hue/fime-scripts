
import os
import re
import time
import random
import string
from datetime import datetime

import requests

# =========================================================
# Discord Username Checker
# لا يحتاج إلى API Token
# ملاحظة: نقطة الفحص غير الرسمية قد تتغير أو تتوقف.
# =========================================================

API_URL = (
    "https://discord.com/api/v9/"
    "unique-username/username-attempt-unauthed"
)

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
RESULTS_DIR = os.path.join(BASE_DIR, "results")

AVAILABLE_FILE = os.path.join(RESULTS_DIR, "available.txt")
TAKEN_FILE = os.path.join(RESULTS_DIR, "taken.txt")
UNKNOWN_FILE = os.path.join(RESULTS_DIR, "unknown.txt")
CHECKED_FILE = os.path.join(RESULTS_DIR, "checked.txt")

# مهلة بين الطلبات لتقليل احتمالية التقييد
REQUEST_DELAY = 2.0
MAX_RETRIES = 2
MAX_RETRY_WAIT = 120

CHARS = string.ascii_lowercase + string.digits

os.makedirs(RESULTS_DIR, exist_ok=True)

session = requests.Session()
session.headers.update({
    "Content-Type": "application/json",
    "Accept": "application/json",
    "User-Agent": "DiscordUsernameChecker/1.0",
})

# =========================================================
# الملفات
# =========================================================

def read_names(path):
    if not os.path.exists(path):
        return set()

    try:
        with open(path, "r", encoding="utf-8") as file:
            return {
                line.strip().lower()
                for line in file
                if line.strip()
            }
    except OSError:
        return set()


def append_name(path, username):
    with open(path, "a", encoding="utf-8") as file:
        file.write(username.lower() + "\n")


def record_result(username, status):
    username = username.lower()

    if status == "available":
        append_name(AVAILABLE_FILE, username)
    elif status == "taken":
        append_name(TAKEN_FILE, username)
    else:
        append_name(UNKNOWN_FILE, username)

    append_name(CHECKED_FILE, username)


def load_unknown():
    return sorted(read_names(UNKNOWN_FILE))


def remove_from_unknown(username):
    names = read_names(UNKNOWN_FILE)
    names.discard(username.lower())

    with open(UNKNOWN_FILE, "w", encoding="utf-8") as file:
        for name in sorted(names):
            file.write(name + "\n")


# =========================================================
# التحقق من صيغة اليوزر
# =========================================================

def valid_username(username):
    username = username.strip().lower()

    # فحص الصيغة المحلية فقط، وليس الإتاحة
    if not 2 <= len(username) <= 32:
        return False

    if not re.fullmatch(r"[a-z0-9_.]+", username):
        return False

    if username.startswith(".") or username.endswith("."):
        return False

    if ".." in username:
        return False

    return True


# =========================================================
# فحص الإتاحة
# =========================================================

def check_username(username):
    username = username.strip().lower()

    if not valid_username(username):
        return "invalid", "صيغة اليوزر غير مقبولة محليًا"

    for attempt in range(MAX_RETRIES + 1):
        try:
            response = session.post(
                API_URL,
                json={"username": username},
                timeout=15,
            )

        except requests.RequestException as error:
            if attempt < MAX_RETRIES:
                time.sleep(REQUEST_DELAY * (attempt + 1))
                continue

            return "unknown", f"خطأ اتصال: {error}"

        if response.status_code == 429:
            retry_after = response.headers.get("Retry-After", "10")

            try:
                wait_seconds = max(1, float(retry_after))
            except (TypeError, ValueError):
                wait_seconds = 10

            # لا ننتظر مدة ضخمة داخل البرنامج
            if attempt < MAX_RETRIES and wait_seconds <= MAX_RETRY_WAIT:
                print(
                    f"\n[!] ديسكورد طلب الانتظار "
                    f"{wait_seconds:g} ثانية."
                )
                time.sleep(wait_seconds)
                continue

            return "blocked", "تقييد طلبات (429)"

        if response.status_code in (401, 403):
            return "blocked", (
                f"رفض ديسكورد الطلب: HTTP {response.status_code}"
            )

        if response.status_code >= 500:
            if attempt < MAX_RETRIES:
                time.sleep(REQUEST_DELAY * (attempt + 1))
                continue

            return "unknown", (
                f"خطأ من الخادم: HTTP {response.status_code}"
            )

        if response.status_code != 200:
            return "unknown", (
                f"استجابة غير متوقعة: HTTP {response.status_code}"
            )

        try:
            data = response.json()
        except ValueError:
            return "unknown", "الاستجابة ليست JSON صالحًا"

        # لا نستنتج شيئًا إلا إذا وصلنا حقل taken بصيغة Boolean
        taken = data.get("taken")

        if isinstance(taken, bool):
            if taken:
                return "taken", "الاسم مأخوذ حسب استجابة الفحص"

            return "available", "الاسم غير مأخوذ حسب استجابة الفحص"

        return "unknown", "الاستجابة لا تحتوي نتيجة إتاحة مؤكدة"

    return "unknown", "انتهت محاولات الفحص"


# =========================================================
# توليد أسماء جديدة
# =========================================================

def generate_username(length, mode, used):
    if mode == "letters":
        alphabet = string.ascii_lowercase
    elif mode == "numbers":
        alphabet = string.digits
    else:
        alphabet = CHARS

    for _ in range(5000):
        username = "".join(
            random.choices(alphabet, k=length)
        )

        if username not in used and valid_username(username):
            used.add(username)
            return username

    return None


def choose_length():
    print("\nاختر طول اليوزر:")
    print("1. ثلاثة أحرف")
    print("2. أربعة أحرف")
    print("3. ثلاثة أو أربعة أحرف")

    choice = input("اختيارك: ").strip()

    if choice == "1":
        return [3]
    if choice == "2":
        return [4]
    if choice == "3":
        return [3, 4]

    print("اختيار غير صحيح.")
    return None


def choose_charset():
    print("\nاختر نوع الأحرف:")
    print("1. أحرف إنجليزية فقط")
    print("2. أرقام فقط")
    print("3. أحرف وأرقام")

    choice = input("اختيارك: ").strip()

    return {
        "1": "letters",
        "2": "numbers",
        "3": "mixed",
    }.get(choice)


# =========================================================
# واجهة الفحص
# =========================================================

def print_status(username, status, detail):
    labels = {
        "available": "[+] متاح حسب الاستجابة",
        "taken": "[-] مأخوذ حسب الاستجابة",
        "unknown": "[?] غير محسوم",
        "invalid": "[!] صيغة غير صالحة",
        "blocked": "[!] توقف الفحص",
    }

    print(f"{labels.get(status, status)} | {username} | {detail}")


def scan_names(names, skip_checked=True):
    checked = read_names(CHECKED_FILE)
    available = read_names(AVAILABLE_FILE)
    taken_names = read_names(TAKEN_FILE)

    total = len(names)
    found = 0

    print(f"\nبدء الفحص: {total} اسمًا")
    print("-" * 60)

    for index, username in enumerate(names, start=1):
        username = username.strip().lower()

        if not username:
            continue

        if skip_checked and username in checked:
            print(f"[تخطي] {username} سبق فحصه")
            continue

        if not valid_username(username):
            print_status(
                username,
                "invalid",
                "صيغة غير صالحة"
            )
            continue

        if username in available or username in taken_names:
            print(f"[تخطي] {username} موجود في النتائج السابقة")
            continue

        print(f"\n[{index}/{total}] فحص {username} ...")

        status, detail = check_username(username)
        print_status(username, status, detail)

        if status in ("available", "taken", "unknown"):
            record_result(username, status)

        if status == "available":
            found += 1

        if status == "blocked":
            print(
                "\nتم إيقاف الفحص لحماية الجلسة من "
                "استمرار الطلبات بعد رفضها أو تقييدها."
            )
            break

        if index < total:
            time.sleep(REQUEST_DELAY)

    print("\n" + "=" * 60)
    print(f"الأسماء المتاحة التي أكدتها الاستجابة: {found}")
    print(f"إجمالي الأسماء المحفوظة كمتاحة: {len(read_names(AVAILABLE_FILE))}")
    print(f"إجمالي الأسماء المحفوظة كمأخوذة: {len(read_names(TAKEN_FILE))}")
    print(f"إجمالي النتائج غير المحسومة: {len(read_names(UNKNOWN_FILE))}")
    print(f"مجلد النتائج: {RESULTS_DIR}")
    print("=" * 60)


def generate_and_scan():
    lengths = choose_length()
    if not lengths:
        print("اختيار غير صحيح.")
        return

    mode = choose_charset()
    if not mode:
        print("اختيار غير صحيح.")
        return

    try:
        amount = int(input("\nكم اسمًا تريد توليده؟ ").strip())
        if not 1 <= amount <= 10000:
            print("اختر رقمًا من 1 إلى 10000.")
            return
    except ValueError:
        print("أدخل رقمًا صحيحًا.")
        return

    checked = read_names(CHECKED_FILE)
    available = read_names(AVAILABLE_FILE)
    taken_names = read_names(TAKEN_FILE)
    unknown = read_names(UNKNOWN_FILE)

    used = checked | available | taken_names | unknown
    names = []

    attempts = 0
    max_generation_attempts = amount * 100

    while len(names) < amount and attempts < max_generation_attempts:
        attempts += 1
        length = random.choice(lengths)
        username = generate_username(length, mode, used)

        if username:
            names.append(username)

    if not names:
        print("تعذر توليد أسماء جديدة ضمن الإعدادات الحالية.")
        return

    print(f"\nتم توليد {len(names)} اسمًا جديدًا.")
    scan_names(names)


def check_custom_list():
    path = input(
        "\nاكتب مسار ملف TXT يحتوي اسمًا واحدًا في كل سطر: "
    ).strip().strip('"')

    if not os.path.isfile(path):
        print("الملف غير موجود.")
        return

    try:
        with open(path, "r", encoding="utf-8-sig") as file:
            names = [
                line.strip().lower()
                for line in file
                if line.strip()
            ]
    except OSError as error:
        print(f"تعذر قراءة الملف: {error}")
        return

    # إزالة التكرار مع الحفاظ على ترتيب الأسماء
    names = list(dict.fromkeys(names))

    if not names:
        print("الملف فارغ.")
        return

    scan_names(names)


def retry_unknown():
    names = load_unknown()

    if not names:
        print("\nلا توجد أسماء غير محسومة لإعادة فحصها.")
        return

    print(f"\nستتم إعادة فحص {len(names)} اسمًا.")
    print("إذا ظهرت قيود، سيتوقف الفحص.")

    confirmation = input("اكتب نعم للمتابعة: ").strip()

    if confirmation != "نعم":
        print("تم الإلغاء.")
        return

    # إعادة الفحص مسموحة حتى لو سبق تسجيل الاسم
    for username in names:
        remove_from_unknown(username)

    scan_names(names, skip_checked=False)


def show_statistics():
    available = read_names(AVAILABLE_FILE)
    taken = read_names(TAKEN_FILE)
    unknown = read_names(UNKNOWN_FILE)
    checked = read_names(CHECKED_FILE)

    print("\n========== الإحصائيات ==========")
    print(f"المتاح حسب الاستجابة: {len(available)}")
    print(f"المأخوذ حسب الاستجابة: {len(taken)}")
    print(f"غير المحسوم: {len(unknown)}")
    print(f"الأسماء التي سبق فحصها: {len(checked)}")
    print(f"الملفات: {RESULTS_DIR}")
    print("================================")


def main():
    while True:
        print("\n" + "=" * 45)
        print("      Discord Username Checker")
        print("=" * 45)
        print("1. توليد يوزرات وفحصها")
        print("2. فحص قائمة من ملف TXT")
        print("3. إعادة فحص النتائج غير المحسومة")
        print("4. عرض الإحصائيات")
        print("5. خروج")

        choice = input("\nاختيارك: ").strip()

        if choice == "1":
            generate_and_scan()
        elif choice == "2":
            check_custom_list()
        elif choice == "3":
            retry_unknown()
        elif choice == "4":
            show_statistics()
        elif choice == "5":
            print("تم إغلاق الأداة.")
            break
        else:
            print("اختيار غير صحيح.")


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\nتم إيقاف الأداة.")
    finally:
        session.close()
