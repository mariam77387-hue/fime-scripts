
import random
import string
import time
import os
from datetime import datetime

# ==========================================
# Discord Username Generator
# Replit - main.py
# ==========================================

LETTERS = string.ascii_lowercase
DIGITS = string.digits
CHARS = LETTERS + DIGITS

OUTPUT_DIR = "results"
os.makedirs(OUTPUT_DIR, exist_ok=True)


def generate_username(length=3, numbers=True):
    """توليد اسم عشوائي."""
    chars = CHARS if numbers else LETTERS
    return "".join(random.choices(chars, k=length))


def generate_unique(count, min_length=3, max_length=4,
                    numbers=True):
    """توليد أسماء فريدة ضمن التشغيل الحالي."""
    found = set()
    possible = sum(
        len(CHARS if numbers else LETTERS) ** length
        for length in range(min_length, max_length + 1)
    )

    count = min(count, possible)

    while len(found) < count:
        length = random.randint(min_length, max_length)
        found.add(generate_username(length, numbers))

    return list(found)


def save_results(names, filename):
    """حفظ الأسماء في ملف نصي."""
    with open(filename, "w", encoding="utf-8") as file:
        file.write("\n".join(names))
        file.write("\n")


def main():
    print("=" * 42)
    print("     DISCORD USERNAME GENERATOR")
    print("     مولّد اقتراحات يوزرات ديسكورد")
    print("=" * 42)
    print("تنبيه: الأسماء المولدة ليست مؤكدة الإتاحة.")
    print("لا تستخدم الأداة لتجاوز حدود ديسكورد.\n")

    while True:
        try:
            count = int(input("كم اسم تبي تولّد؟ (1-10000): "))
            if 1 <= count <= 10000:
                break
            print("اختر رقمًا بين 1 و10000.")
        except ValueError:
            print("اكتب رقمًا صحيحًا.")

    while True:
        length_choice = input(
            "نوع الأسماء: [1] ثلاثة أحرف [2] أربعة أحرف "
            "[3] خليط: "
        ).strip()

        if length_choice in ("1", "2", "3"):
            break
        print("اختر 1 أو 2 أو 3.")

    while True:
        number_choice = input(
            "تضمين الأرقام؟ [y/n]: "
        ).strip().lower()

        if number_choice in ("y", "n"):
            break
        print("اكتب y أو n.")

    if length_choice == "1":
        min_length = max_length = 3
    elif length_choice == "2":
        min_length = max_length = 4
    else:
        min_length, max_length = 3, 4

    print("\nجاري توليد الأسماء...\n")

    names = generate_unique(
        count,
        min_length,
        max_length,
        numbers=(number_choice == "y")
    )

    for index, name in enumerate(names, 1):
        print(f"{index:>5}. {name}")

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filepath = os.path.join(
        OUTPUT_DIR, f"usernames_{timestamp}.txt"
    )

    save_results(names, filepath)

    print("\n" + "=" * 42)
    print(f"تم توليد {len(names)} اسم.")
    print(f"حُفظت النتائج في: {filepath}")
    print("الحالة: اقتراحات فقط، لم يتم تأكيد الإتاحة.")
    print("=" * 42)


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\nتم إيقاف الأداة.")
