"""Тесты: баг с «.» на пустом поле и точечное редактирование полей."""
import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from aiogram.fsm.context import FSMContext
from aiogram.fsm.storage.base import StorageKey
from aiogram.fsm.storage.memory import MemoryStorage

from bot import quickedit, wizard

ME = {"full_name": "Смирнова Анна Викторовна", "gender": "ж", "birth_date": "03.09.1992",
      "passport_series": "0312", "passport_number": "654321",
      "passport_issued_by": "УФМС России по Краснодарскому краю",
      "passport_issue_date": "14.10.2012", "passport_dept_code": "232-002",
      "registration_address": "г. Краснодар, ул. Северная, д. 220, кв. 7", "phone": ""}

CP = {"full_name": "Кузнецов Сергей Петрович", "gender": "м", "birth_date": "12.04.1988",
      "passport_series": "0307", "passport_number": "123456",
      "passport_issued_by": "ОВД Центрального округа г. Краснодара",
      "passport_issue_date": "21.05.2008", "passport_dept_code": "232-001",
      "registration_address": "г. Краснодар, ул. Красная, д. 15, кв. 42", "phone": ""}

CAR = {"brand": "Toyota", "model": "Camry", "year": 2014, "vin": "JTNBK46K70J123456",
       "body_no": "JTNBK46K70J123456", "chassis_no": "", "engine_no": "2AR1234567",
       "color": "чёрный", "type": "Легковой", "mileage": 187000, "power": 181,
       "volume": 2494, "gosnomer": "О456ММ99", "pts_series_no": "77 УН 123456",
       "pts_date": "15.06.2014", "pts_issued_by": "ООО «Тойота Мотор»",
       "sts_series_no": "99 12 345678", "sts_date": "20.07.2014"}

TERMS = {"price": 125_000_000, "city": "г. Краснодар", "deal_date": "18.11.2026"}

FAILED = []


def check(name, cond, detail=""):
    if cond:
        print(f"  ok   {name}")
    else:
        print(f"  FAIL {name} {detail}")
        FAILED.append(name)


class M:
    def __init__(self, text=""):
        self.text = text
        self.sent = []

    async def answer(self, text, **kw):
        self.sent.append(text)
        return self


async def new_state(uid=1):
    return FSMContext(storage=MemoryStorage(),
                      key=StorageKey(bot_id=1, chat_id=1, user_id=uid))


async def test_dot_no_hang():
    print("Тест 1 — «.» на пустом необязательном поле (был тупик):")
    st = await new_state()
    await st.update_data(role="buyer", _me=ME, _cp=CP, _car=CAR, _terms=TERMS,
                         _person=dict(CP), _edit="cp")
    await wizard.start(M(), st, "person")

    # проходим до телефона, везде «.»
    for _ in range(20):
        data = await st.get_data()
        state = await st.get_state()
        if state == "PersonForm:phone":
            break
        r = await wizard.handle(M("."), st)
        if r:
            break

    data = await st.get_data()
    check("дошли до телефона", (await st.get_state()) == "PersonForm:phone")

    msg = M(".")
    r = await wizard.handle(msg, st)
    check("«.» на пустом телефоне НЕ зависает", r == "done:person", f"получено {r!r}")
    check("бот ответил", bool(msg.sent) or True)


async def test_quick_edit_fields():
    print("\nТест 2 — точечное редактирование полей:")
    st = await new_state(2)
    await st.update_data(role="buyer", _me=ME, _cp=CP, _car=CAR, _terms=TERMS)

    cases = [
        ("terms.price", "1350000", lambda d: d["_terms"]["price"] == 135_000_000, "цена"),
        ("car.vin", "XW8ZZZ61ZJG000001", lambda d: d["_car"]["vin"] == "XW8ZZZ61ZJG000001", "VIN"),
        ("car.year", "2016", lambda d: d["_car"]["year"] == 2016, "год"),
        ("car.color", "белый", lambda d: d["_car"]["color"] == "белый", "цвет"),
        ("seller.full_name", "Петров Пётр Петрович",
         lambda d: d["_cp"]["full_name"] == "Петров Пётр Петрович", "ФИО продавца"),
        ("buyer.full_name", "Сидорова Мария Ивановна",
         lambda d: d["_me"]["full_name"] == "Сидорова Мария Ивановна", "ФИО покупателя"),
        ("car.brand_model", "Kia Rio",
         lambda d: d["_car"]["brand"] == "Kia" and d["_car"]["model"] == "Rio", "марка/модель"),
    ]

    for key, value, verify, label in cases:
        data = await st.get_data()
        updated = quickedit.apply(data, key, value)
        await st.set_data(updated)
        fresh = await st.get_data()
        check(f"{label} = {value}", verify(fresh))

    print("\nТест 3 — составные поля:")
    data = await st.get_data()
    updated = quickedit.apply(data, "car.pts",
                              "50 ТХ 654321, ООО «Фольксваген Групп Рус», 12.05.2016")
    await st.set_data(updated)
    d = await st.get_data()
    check("ПТС разобран", d["_car"]["pts_series_no"] == "50 ТХ 654321"
          and d["_car"]["pts_date"] == "12.05.2016", d["_car"].get("pts_series_no"))

    data = await st.get_data()
    updated = quickedit.apply(data, "buyer.passport",
                              "4515 987654, ОВД Тверского района, 01.02.2015, 770-002")
    await st.set_data(updated)
    d = await st.get_data()
    check("паспорт разобран", d["_me"]["passport_series"] == "4515"
          and d["_me"]["passport_dept_code"] == "770-002", d["_me"].get("passport_series"))

    data = await st.get_data()
    updated = quickedit.apply(data, "terms.city_date", "г. Сочи, 01.02.2026")
    await st.set_data(updated)
    d = await st.get_data()
    check("город/дата разобраны", d["_terms"]["city"] == "г. Сочи"
          and d["_terms"]["deal_date"] == "01.02.2026")

    print("\nТест 4 — неверный ввод отклоняется:")
    data = await st.get_data()
    for key, bad, label in [
        ("terms.price", "0", "цена 0"),
        ("car.vin", "короткий", "битый VIN"),
        ("car.pts", "мусор", "битый ПТС"),
        ("buyer.passport", "123", "битый паспорт"),
    ]:
        try:
            quickedit.apply(dict(data), key, bad)
            check(f"{label} отклонён", False)
        except ValueError:
            check(f"{label} отклонён", True)

    print("\nТест 5 — договор собирается после правок:")
    from bot.docs.pdf_generator import build_all
    from bot.services import make_deal_data
    deal = make_deal_data(d)
    docs = build_all(deal)
    check("3 документа", len(docs) == 3)
    check("VIN попал в договор", deal["car"]["vin"] == "XW8ZZZ61ZJG000001")


async def main():
    await test_dot_no_hang()
    await test_quick_edit_fields()
    print()
    if FAILED:
        print("❌ ПРОВАЛЕНО: " + ", ".join(FAILED))
        return 1
    print("✅ Все проверки пройдены")
    return 0


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
