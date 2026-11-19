"""Тесты критичной логики. Запуск: python tools/selftest.py"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from bot.services import make_deal_data, person_complete  # noqa: E402
from bot.utils import validators as v  # noqa: E402
from bot.utils.money import initials, rubles_to_words  # noqa: E402

FAILED: list[str] = []


def check(name: str, actual, expected) -> None:
    if actual == expected:
        print(f"  ok   {name}")
    else:
        print(f"  FAIL {name}\n       получено: {actual!r}\n       ожидалось: {expected!r}")
        FAILED.append(name)


def check_raises(name: str, fn, *args) -> None:
    try:
        fn(*args)
    except ValueError:
        print(f"  ok   {name} (отклонено)")
        return
    print(f"  FAIL {name}: ошибка не возникла")
    FAILED.append(name)


print("Сумма прописью:")
check("0", rubles_to_words(0), "Ноль рублей 00 копеек")
check("1", rubles_to_words(100), "Один рубль 00 копеек")
check("2", rubles_to_words(200), "Два рубля 00 копеек")
check("5", rubles_to_words(500), "Пять рублей 00 копеек")
check("11", rubles_to_words(1100), "Одиннадцать рублей 00 копеек")
check("21", rubles_to_words(2100), "Двадцать один рубль 00 копеек")
check("1000", rubles_to_words(100000), "Одна тысяча рублей 00 копеек")
check("2000", rubles_to_words(200000), "Две тысячи рублей 00 копеек")
check("5000", rubles_to_words(500000), "Пять тысяч рублей 00 копеек")
check("125 тыс.", rubles_to_words(125_000_00),
      "Сто двадцать пять тысяч рублей 00 копеек")
check("1.25 млн", rubles_to_words(125_000_000),
      "Один миллион двести пятьдесят тысяч рублей 00 копеек")
check("копейки", rubles_to_words(12345),
      "Сто двадцать три рубля 45 копеек")
check("11 копеек", rubles_to_words(11), "Ноль рублей 11 копеек")

print("\nИнициалы:")
check("муж", initials("Кузнецов Сергей Петрович"), "С. П. Кузнецов")
check("жен", initials("Смирнова Анна Викторовна"), "А. В. Смирнова")

print("\nВалидаторы (принимаем):")
check("ФИО", v.validate_fio("  Иванов  Иван Иванович "), "Иванов Иван Иванович")
check("серия", v.validate_passport_series("4507"), "4507")
check("номер", v.validate_passport_number("123456"), "123456")
check("код подразделения", v.validate_dept_code("232001"), "232-001")
check("код с дефисом", v.validate_dept_code("232-001"), "232-001")
check("дата", v.validate_date("1.2.2019"), "01.02.2019")
check("телефон 11", v.validate_phone("+7 999 123-45-67"), "+7 (999) 123-45-67")
check("телефон 10", v.validate_phone("9991234567"), "+7 (999) 123-45-67")
check("VIN", v.validate_vin("jtnbk46k70j123456"), "JTNBK46K70J123456")
check("год", v.validate_year("2014"), 2014)
check("госномер", v.validate_gosnomer("о456мм99"), "О456ММ99")
check("госномер нет", v.validate_gosnomer("нет"), "отсутствует")
check("ПТС", v.validate_pts_sts_number("77 УН 123456"), "77 УН 123456")
check("ПТС цифры", v.validate_pts_sts_number("7712345678"), "7712 345678")
check("цена", v.validate_money("1 250 000"), 125_000_000)
check("цена с копейками", v.validate_money("125000,50"), 12_500_050)
check("пробег", v.validate_int("187000", 0, 3_000_000), 187000)

print("\nВалидаторы (отклоняем):")
check_raises("ФИО одно слово", v.validate_fio, "Иванов")
check_raises("ФИО цифры", v.validate_fio, "Иванов Иван 123")
check_raises("серия 3 цифры", v.validate_passport_series, "450")
check_raises("код 5 цифр", v.validate_dept_code, "23200")
check_raises("дата в будущем", v.validate_past_date, "01.01.2099")
check_raises("дата мусор", v.validate_date, "32.13.2020")
check_raises("VIN 16 символов", v.validate_vin, "JTNBK46K70J12345")
check_raises("VIN с буквой I", v.validate_vin, "JTNBK46K70J12345I")
check_raises("год 1800", v.validate_year, "1800")
check_raises("цена 0", v.validate_money, "0")
check_raises("госномер кривой", v.validate_gosnomer, "12345")
check_raises("адрес без дома", v.validate_address, "г. Краснодар, ул. Красная")

print("\nСборка сделки:")
ME = {
    "full_name": "Смирнова Анна Викторовна", "gender": "ж", "birth_date": "03.09.1992",
    "passport_series": "0312", "passport_number": "654321",
    "passport_issued_by": "УФМС России по Краснодарскому краю",
    "passport_issue_date": "14.10.2012", "passport_dept_code": "232-002",
    "registration_address": "г. Краснодар, ул. Северная, д. 220, кв. 7", "phone": "",
}
CP = {
    "full_name": "Кузнецов Сергей Петрович", "gender": "м", "birth_date": "12.04.1988",
    "passport_series": "0307", "passport_number": "123456",
    "passport_issued_by": "ОВД Центрального округа г. Краснодара",
    "passport_issue_date": "21.05.2008", "passport_dept_code": "232-001",
    "registration_address": "г. Краснодар, ул. Красная, д. 15, кв. 42", "phone": "",
}
CAR = {"brand": "Toyota", "model": "Camry", "year": 2014, "vin": "JTNBK46K70J123456",
       "color": "чёрный", "pts_series_no": "77 УН 123456", "pts_date": "15.06.2014",
       "pts_issued_by": "ООО «Тойота Мотор»", "sts_series_no": "99 12 345678",
       "sts_date": "20.07.2014"}
TERMS = {"price": 125_000_000, "city": "г. Краснодар", "deal_date": "18.11.2026"}

check("профиль полный", person_complete(ME), True)
check("профиль неполный", person_complete({"full_name": "Иванов Иван"}), False)

data = make_deal_data({"role": "buyer", "_me": ME, "_cp": CP, "_car": CAR, "_terms": TERMS})
check("покупатель = я", data["buyer"]["full_name"], ME["full_name"])
check("продавец = контрагент", data["seller"]["full_name"], CP["full_name"])
check("копейки", data["price_kopecks"], 125_000_000)

data2 = make_deal_data({"role": "seller", "_me": ME, "_cp": CP, "_car": CAR, "_terms": TERMS})
check("я продавец", data2["seller"]["full_name"], ME["full_name"])
check("покупатель = контрагент", data2["buyer"]["full_name"], CP["full_name"])

print("\nГенерация PDF:")
from bot.docs.pdf_generator import build_all  # noqa: E402
docs = build_all(data)
for kind, content in docs.items():
    ok = content.startswith(b"%PDF") and len(content) > 5000
    print(f"  {'ok  ' if ok else 'FAIL'} {kind}: {len(content) / 1024:.0f} КБ")
    if not ok:
        FAILED.append(f"pdf:{kind}")

print("\n" + ("❌ ПРОВАЛЕНО: " + ", ".join(FAILED) if FAILED else "✅ Все проверки пройдены"))
sys.exit(1 if FAILED else 0)
