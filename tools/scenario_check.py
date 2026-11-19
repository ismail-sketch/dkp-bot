"""Проверка: все данные из ТЕСТ-СЦЕНАРИЙ.md проходят валидаторы и создают документы."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from bot.docs.pdf_generator import build_all
from bot.services import make_deal_data
from bot.utils import validators as v

FAILED = []


def check(name, fn, arg, expected=None):
    try:
        got = fn(arg)
    except ValueError as exc:
        print(f"  FAIL {name}: отклонено — {exc}")
        FAILED.append(name)
        return None
    if expected is not None and got != expected:
        print(f"  FAIL {name}: получено {got!r}, ожидалось {expected!r}")
        FAILED.append(name)
        return got
    print(f"  ok   {name}")
    return got


print("=== Тест 2: профиль ===")
me = {}
me["full_name"] = check("ФИО", v.validate_fio, "Смирнова Анна Викторовна")
me["gender"] = check("Пол", v.validate_gender, "Женский", "ж")
me["birth_date"] = check("Дата рождения", v.validate_past_date, "03.09.1992")
me["passport_series"] = check("Серия", v.validate_passport_series, "0312", "0312")
me["passport_number"] = check("Номер", v.validate_passport_number, "654321")
me["passport_issued_by"] = check("Кем выдан", v.validate_text(300),
                                 "УФМС России по Краснодарскому краю")
me["passport_issue_date"] = check("Дата выдачи", v.validate_past_date, "14.10.2012")
me["passport_dept_code"] = check("Код без дефиса", v.validate_dept_code, "232002", "232-002")
me["registration_address"] = check("Адрес", v.validate_address,
                                   "г. Краснодар, ул. Северная, д. 220, кв. 7")
me["phone"] = ""

print("\n=== Тест 5: вторая сторона ===")
cp = {}
cp["full_name"] = check("ФИО", v.validate_fio, "Кузнецов Сергей Петрович")
cp["gender"] = check("Пол", v.validate_gender, "Мужской", "м")
cp["birth_date"] = check("Дата рождения", v.validate_past_date, "12.04.1988")
cp["passport_series"] = check("Серия", v.validate_passport_series, "0307")
cp["passport_number"] = check("Номер", v.validate_passport_number, "123456")
cp["passport_issued_by"] = check("Кем выдан", v.validate_text(300),
                                 "ОВД Центрального округа г. Краснодара")
cp["passport_issue_date"] = check("Дата выдачи", v.validate_past_date, "21.05.2008")
cp["passport_dept_code"] = check("Код", v.validate_dept_code, "232-001", "232-001")
cp["registration_address"] = check("Адрес", v.validate_address,
                                   "г. Краснодар, ул. Красная, д. 15, кв. 42")
cp["phone"] = check("Телефон", v.validate_phone, "+7 999 111-22-33", "+7 (999) 111-22-33")

print("\n=== Тест 5: автомобиль ===")
car = {}
car["brand"] = check("Марка", v.validate_text(60), "Toyota")
car["model"] = check("Модель", v.validate_text(60), "Camry")
car["year"] = check("Год", v.validate_year, "2014", 2014)
car["vin"] = check("VIN", v.validate_vin, "JTNBK46K70J123456")
car["body_no"] = "JTNBK46K70J123456"
car["chassis_no"] = ""
car["engine_no"] = "2AR1234567"
car["color"] = check("Цвет", v.validate_text(40), "чёрный")
car["type"] = "Легковой"
car["mileage"] = check("Пробег", lambda s: v.validate_int(s, 0, 3_000_000), "187000", 187000)
car["power"] = check("Мощность", lambda s: v.validate_int(s, 1, 2000), "181", 181)
car["volume"] = check("Объём", lambda s: v.validate_int(s, 1, 20000), "2494", 2494)
car["gosnomer"] = check("Госномер", v.validate_gosnomer, "О456ММ99")
car["pts_series_no"] = check("ПТС", v.validate_pts_sts_number, "77 УН 123456")
car["pts_date"] = check("ПТС дата", v.validate_past_date, "15.06.2014")
car["pts_issued_by"] = check("ПТС кем выдан", v.validate_text(300), "ООО «Тойота Мотор»")
car["sts_series_no"] = check("СТС", v.validate_pts_sts_number, "99 12 345678")
car["sts_date"] = check("СТС дата", v.validate_past_date, "20.07.2014")

print("\n=== Тест 5: условия ===")
terms = {}
terms["price"] = check("Цена", v.validate_money, "1250000", 125_000_000)
terms["city"] = check("Город", v.validate_text(100), "г. Краснодар")
terms["deal_date"] = check("Дата договора", v.validate_past_date, "18.11.2026")

print("\n=== Тест 7: правки из чек-листа ===")
check("Новая цена", v.validate_money, "1350000", 135_000_000)
check("Новый VIN", v.validate_vin, "XW8ZZZ61ZJG000001")
from bot.quickedit import _parse_pts
pts_new = _parse_pts("50 ТХ 654321, ООО «Фольксваген Групп Рус», 12.05.2016")
print(f"  ok   ПТС разобран: {pts_new['pts_series_no']}, {pts_new['pts_date']}")

print("\n=== Тест 8: документы ===")
deal = make_deal_data({"role": "buyer", "_me": dict(me), "_cp": dict(cp),
                       "_car": dict(car), "_terms": dict(terms)})
docs = build_all(deal)
for kind, content in docs.items():
    print(f"  ok   {kind}: {len(content) / 1024:.0f} КБ")

print("\n=== Итог ===")
if FAILED:
    print("❌ ПРОВАЛЕНО: " + ", ".join(FAILED))
    sys.exit(1)
print("✅ Все данные из сценария проходят корректно")
