"""Воспроизведение бага: редактирование и нажатие «.» (оставить как есть)."""
import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from aiogram.fsm.context import FSMContext
from aiogram.fsm.storage.base import StorageKey
from aiogram.fsm.storage.memory import MemoryStorage

from bot import wizard

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


class M:
    def __init__(self, text=""):
        self.text = text
        self.sent = []

    async def answer(self, text, **kw):
        self.sent.append(text)
        return self


async def main():
    st = FSMContext(storage=MemoryStorage(),
                    key=StorageKey(bot_id=1, chat_id=1, user_id=1))
    await st.update_data(role="buyer", _me=ME, _cp=CP, _car=CAR, _terms=TERMS,
                         _first_person=None, _target=None)

    print("=== Имитируем «Изменить данные» → «Вторую сторону» ===")
    await st.update_data(_person=dict(CP), _edit="cp")
    await wizard.start(M(), st, "person")
    print("состояние:", await st.get_state(), "| _idx:", (await st.get_data()).get("_idx"))

    print("\n=== Жмём «.» на каждом шаге (оставить как есть) ===")
    for i in range(12):
        data = await st.get_data()
        state = await st.get_state()
        print(f"\nшаг {i+1}: state={state} idx={data.get('_idx')}")
        msg = M(".")
        result = await wizard.handle(msg, st)
        print(f"  результат: {result!r}")
        print(f"  ответ бота: {msg.sent!r}")
        if result:
            print(f"  -> форма завершена, новый state={await st.get_state()}")
            break
        if not msg.sent:
            print("  !!! БОТ МОЛЧИТ — ЗАВИСАНИЕ")
            break
    else:
        print("\n!!! ЦИКЛ НЕ ЗАВЕРШИЛСЯ")

    d = await st.get_data()
    print("\n=== Итог ===")
    print("state:", await st.get_state())
    print("_cp:", bool(d.get("_cp")), "| _edit:", d.get("_edit"))


asyncio.run(main())
