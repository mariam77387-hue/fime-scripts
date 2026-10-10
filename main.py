
import json
import random
import string
import time
import os
import urllib.request
import urllib.error
from datetime import datetime

# ==========================================
# Username Finder - Replit / main.py
# ==========================================

API_URL = (
    "https://discord.com/api/v9/"
    "unique-username/username-attempt-unauthed"
)

OUTPUT_DIR = "results"
os.makedirs(OUTPUT_DIR, exist_ok=True)

LETTERS = string.ascii_lowercase
DIGITS = string.digits

HEADERS = {
    "Content-Type": "application/json",
    "Accept": "*/*",
    "Origin": "https://discord.com",
    "Referer": "https://discord.com/register",
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/124.0.0.0 Safari/537.36"
    ),
}


def generate_username(length, letters_only=False):
    chars = LETTERS if letters_only else LETTERS + DIGITS
    return "".join(random.choices(chars, k=length))


def valid_username(name):
    if not 2 <= len(name) <= 32:
        return False
    if any(c not in LETTERS + DIGITS + "._" for c in name):
        return False
    if name.startswith(".") or name.endswith("."):
        return False
    if ".." in name:
        return False
    return True


def check_username(name):
    """النتيجة: available / taken / unknown / rate_limited."""
    name = name.lower()

    if not valid_username(name):
        return "invalid"

    payload = json.dumps({"username": name}).encode("utf-8")
    request = urllib.request.Request(
        API_URL,
        data=payload,
        headers=HEADERS,
        method="POST",
    )

    try:
        with urllib.request.urlopen(request, timeout=15) as response:
            data = json.loads(response.read().decode("utf-8"))

        if not isinstance(data, dict):
            return "unknown"

        taken = data.get("taken")

        if taken is True:
            return "taken"
        if taken is False:
            return "available"

        return "unknown"

    except urllib.error.HTTPError as error:
        if error.code == 429:
            return "rate_limited"
        return "unknown"

    except (urllib.error.URLError, TimeoutError, OSError, ValueError):
        return "unknown"


def save_file(filename, values):
    with open(filename, "w", encoding="utf-8") as file:
        for value in values:
            file.write(value + "\n")


def main():
    print("=" * 48)
    print("   USERNAME FINDER")
    print("   مولّد وفاحص أسماء المستخدمين")
    print("=" * 48)
    print("ملاحظة: نتيجة الفحص تعتمد على استجابة الواجهة.\n")

    try:
        amount = int(input("عدد الأسماء (1-200): "))
        if not 1 <= amount <= 200:
            print("اختر عددًا من 1 إلى 200.")
            return
    except ValueError:
        print("الرجاء إدخال رقم صحيح.")
        return

    print("\n1 - ثلاثة أحرف")
    print("2 - أربعة أحرف")
    print("3 - خليط من 3 و4 أحرف")
    choice = input("اختيارك: ").strip()

    if choice not in ("1", "2", "3"):
        print("اختيار غير صحيح.")
        return

    letters_only = (
        input("حروف فقط؟ (y/n): ").strip().lower() == "y"
    )

    if choice == "1":
        lengths = [3]
    elif choice == "2":
        lengths = [4]
    else:
        lengths = [3, 4]

    candidates = set()
    while len(candidates) < amount:
        length = random.choice(lengths)
        candidates.add(generate_username(length, letters_only))

    available = []
    taken = []
    unknown = []
    stopped = False

    print("\nبدأ الفحص...\n")

    for index, name in enumerate(candidates, start=1):
        status = check_username(name)
        print(f"[{index}/{amount}] {name} -> {status}")

        if status == "available":
            available.append(name)
        elif status == "taken":
            taken.append(name)
        elif status == "rate_limited":
            unknown.append(name + " | rate_limited")
            print(
                "\nتم إيقاف الفحص لأن الخدمة حدّت الطلبات. "
                "أعد التشغيل لاحقًا بدل تجاوز الحد."
            )
            stopped = True
            break
        else:
            unknown.append(name + " | " + status)

        if index < amount:
            time.sleep(2)

    stamp = datetime.now().strftime("%Y%m%d_%H%M%S")

    save_file(
        os.path.join(OUTPUT_DIR, f"available_{stamp}.txt"),
        available,
    )
    save_file(
        os.path.join(OUTPUT_DIR, f"taken_{stamp}.txt"),
        taken,
    )
    save_file(
        os.path.join(OUTPUT_DIR, f"unknown_{stamp}.txt"),
        unknown,
    )

    print("\n" + "=" * 48)
    print(f"متاح بحسب الاستجابة: {len(available)}")
    print(f"مشغول بحسب الاستجابة: {len(taken)}")
    print(f"غير مؤكد: {len(unknown)}")
    print(f"النتائج محفوظة في مجلد: {OUTPUT_DIR}")

    if stopped:
        print("الفحص توقف بسبب تحديد الطلبات.")

    print("تحقق من الاسم نهائيًا في إعدادات ديسكورد.")
    print("=" * 48)


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\nتم إيقاف البرنامج.")
