
import json
import random
import string
import time
import os
import urllib.request
import urllib.error
from datetime import datetime

# ==========================================
# Discord Username Generator + Checker
# Replit / main.py
# ==========================================

API_URL = (
    "https://discord.com/api/v9/"
    "unique-username/username-attempt-unauthed"
)

OUTPUT_DIR = "results"
os.makedirs(OUTPUT_DIR, exist_ok=True)

CHARS = string.ascii_lowercase + string.digits


def generate_username(length, letters_only=False):
    chars = string.ascii_lowercase if letters_only else CHARS
    return "".join(random.choices(chars, k=length))


def check_username(username):
    """يفحص الاسم. لا يخمّن الإتاحة عند وجود خطأ."""
    payload = json.dumps({"username": username}).encode("utf-8")

    request = urllib.request.Request(
        API_URL,
        data=payload,
        headers={
            "Content-Type": "application/json",
            "User-Agent": "Python Username Availability Checker",
        },
        method="POST",
    )

    try:
        with urllib.request.urlopen(request, timeout=12) as response:
            data = json.loads(response.read().decode("utf-8"))

        # لا نعتبر الاسم متاحًا إلا إذا أعادت الواجهة
        # حقلًا واضحًا يدل على الإتاحة.
        if isinstance(data, dict) and data.get("taken") is False:
            return "AVAILABLE"

        if isinstance(data, dict) and data.get("taken") is True:
            return "TAKEN"

        if isinstance(data, dict) and data.get("username") == username:
            return "CHECK_MANUALLY"

        return "UNKNOWN"

    except urllib.error.HTTPError as error:
        if error.code == 429:
            return "RATE_LIMITED"
        if error.code in (400, 401, 403, 404):
            return "CHECK_FAILED"
        return "CHECK_FAILED"

    except (urllib.error.URLError, TimeoutError, OSError, ValueError):
        return "CHECK_FAILED"


def save_names(filename, names):
    with open(filename, "w", encoding="utf-8") as file:
        for name in names:
            file.write(name + "\n")


def main():
    print("=" * 48)
    print(" DISCORD USERNAME CHECKER")
    print(" مولد وفاحص اقتراحات اليوزرات")
    print("=" * 48)
    print("ملاحظة: فحص الإتاحة يعتمد على واجهة غير رسمية.")
    print("لن يتم تجاوز تحديد الطلبات أو إعادة المحاولة آليًا.\n")

    while True:
        try:
            amount = int(input("عدد الأسماء المطلوب توليدها (1-500): "))
            if 1 <= amount <= 500:
                break
        except ValueError:
            pass
        print("أدخل عددًا صحيحًا بين 1 و500.")

    print("\n1 - ثلاثة أحرف")
    print("2 - أربعة أحرف")
    print("3 - خليط من 3 و4 أحرف")

    choice = input("اختيارك: ").strip()
    if choice not in ("1", "2", "3"):
        print("اختيار غير صحيح.")
        return

    letters_only = input("حروف فقط؟ (y/n): ").strip().lower() == "y"

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

    print("\nبدء الفحص، طلب واحد كل ثانيتين.\n")

    for index, username in enumerate(candidates, 1):
        result = check_username(username)
        print(f"[{index}/{len(candidates)}] {username}: {result}")

        if result == "AVAILABLE":
            available.append(username)
        elif result == "TAKEN":
            taken.append(username)
        else:
            unknown.append(f"{username} | {result}")

        if result == "RATE_LIMITED":
            print(
                "\nديسكورد حدّ الطلبات. تم إيقاف الفحص "
                "بدل محاولة تجاوز الحد."
            )
            break

        if index < len(candidates):
            time.sleep(2)

    stamp = datetime.now().strftime("%Y%m%d_%H%M%S")

    save_names(
        os.path.join(OUTPUT_DIR, f"available_{stamp}.txt"),
        available
    )
    save_names(
        os.path.join(OUTPUT_DIR, f"taken_{stamp}.txt"),
        taken
    )
    save_names(
        os.path.join(OUTPUT_DIR, f"unknown_{stamp}.txt"),
        unknown
    )

    print("\n" + "=" * 48)
    print(f"متاح حسب استجابة الواجهة: {len(available)}")
    print(f"مشغول حسب استجابة الواجهة: {len(taken)}")
    print(f"غير مؤكد أو تعذر فحصه: {len(unknown)}")
    print(f"راجع مجلد النتائج: {OUTPUT_DIR}")
    print("تحقق من الاسم داخل إعدادات ديسكورد قبل الاعتماد عليه.")
    print("=" * 48)


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\nأوقف المستخدم الأداة.")
