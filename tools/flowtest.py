"""Прогон диалога без Telegram: два сценария.

1. С профилем — «я покупатель», вводится только вторая сторона.
2. Без профиля (разовый режим) — вводятся обе стороны, ничего не сохраняется.

Запуск: python tools/flowtest.py
"""
import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from aiogram.fsm.context import FSMContext
from aiogram.fsm.storage.base import StorageKey
from aiogram.fsm.storage.memory import MemoryStorage

from bot import wizard
from bot.services import make_deal_data, person_complete

MY = [
    "Смирнова Анна Викторовна", "Женский", "03.09.1992",
    "0312", "654321", "УФМС России по Краснодарскому краю",
    "14.10.2012", "232-002", "г. Краснодар, ул. Северная, д. 220, кв. 7",
    "⏭ Пропустить",
]

OTHER = [
    "Кузнецов Сергей Петрович", "Мужской", "12.04.1988",
    "0307", "123456", "ОВД Центрального округа г. Краснодара",
    "21.05.2008", "232-001", "г. Краснодар, ул. Красная, д. 15, кв. 42",
    "⏭ Пропустить",
]

CAR = [
    "Toyota", "Camry", "2014", "JTNBK46K70J123456",
    "JTNBK46K70J123456", "⏭ Пропустить", "2AR1234567",
    "чёрный", "Легковой", "187000", "181", "2494", "О456ММ99",
    "77 УН 123456", "15.06.2014", "ООО «Тойота Мотор»", "99 12 345678", "20.07.2014",
]

TERMS = ["1250000", "г. Краснодар", "18.11.2026"]


class FakeMessage:
    def __init__(self, text: str = "") -> None:
        self.text = text
        self.sent: list[str] = []

    async def answer(self, text: str, **kwargs) -> "FakeMessage":
        self.sent.append(text)
        return self


async def run_person(state: FSMContext, answers: list[str]) -> dict:
    await wizard.start(FakeMessage(), state, "person")
    for ans in answers:
        result = await wizard.handle(FakeMessage(ans), state)
        if result and result.startswith("done:"):
            d = await state.get_data()
            return d["_person"]
    raise AssertionError("анкета не завершилась")


async def scenario_with_profile() -> list[str]:
    errors: list[str] = []
    state = FSMContext(storage=MemoryStorage(),
                       key=StorageKey(bot_id=1, chat_id=1, user_id=1))

    me = dict(zip(("full_name", "gender", "birth_date", "passport_series", "passport_number",
                   "passport_issued_by", "passport_issue_date", "passport_dept_code",
                   "registration_address", "phone"), MY))
    me["gender"] = "ж"
    me["phone"] = ""

    await state.update_data(role="buyer", _me=me, _cp={}, _first_person="cp")
    cp = await run_person(state, OTHER)
    if not person_complete(cp):
        errors.append("контрагент неполный")
    await state.update_data(_cp=cp, _first_person=None)

    await wizard.start(FakeMessage(), state, "car")
    for ans in CAR:
        r = await wizard.handle(FakeMessage(ans), state)
        if r and r.startswith("done:"):
            break
    await state.update_data(_car=(await state.get_data())["_car"])

    await wizard.start(FakeMessage(), state, "terms")
    for ans in TERMS:
        r = await wizard.handle(FakeMessage(ans), state)
        if r and r.startswith("done:"):
            break

    data = await state.get_data()
    deal = make_deal_data(data)
    if deal["buyer"]["full_name"] != me["full_name"]:
        errors.append("покупатель должен быть я")
    if deal["seller"]["full_name"] != cp["full_name"]:
        errors.append("продавец должен быть контрагент")
    print(f"  ok   режим с профилем: {deal['buyer']['full_name']} ← {deal['seller']['full_name']}")
    return errors


async def scenario_without_profile() -> list[str]:
    errors: list[str] = []
    state = FSMContext(storage=MemoryStorage(),
                       key=StorageKey(bot_id=1, chat_id=1, user_id=2))

    # профиля нет: _me = None, первую анкету вводит сам пользователь
    await state.update_data(role="seller", _me=None, _cp={}, _first_person="me")

    me = await run_person(state, MY)
    if not person_complete(me):
        errors.append("мои данные неполные")
    await state.update_data(_me=me, _person={}, _first_person="cp")

    cp = await run_person(state, OTHER)
    await state.update_data(_cp=cp, _first_person=None)

    await wizard.start(FakeMessage(), state, "car")
    for ans in CAR:
        r = await wizard.handle(FakeMessage(ans), state)
        if r and r.startswith("done:"):
            break

    await wizard.start(FakeMessage(), state, "terms")
    for ans in TERMS:
        r = await wizard.handle(FakeMessage(ans), state)
        if r and r.startswith("done:"):
            break

    data = await state.get_data()
    deal = make_deal_data(data)
    if deal["seller"]["full_name"] != me["full_name"]:
        errors.append("продавец должен быть я")
    if deal["buyer"]["full_name"] != cp["full_name"]:
        errors.append("покупатель должен быть контрагент")
    print(f"  ok   разовый режим: {deal['seller']['full_name']} → {deal['buyer']['full_name']}")

    from bot.docs.pdf_generator import build_all
    docs = build_all(deal)
    if len(docs) != 3:
        errors.append("не 3 документа")
    print(f"  ok   документов: {len(docs)}")
    return errors


async def main() -> int:
    print("Сценарий 1 — с сохранённым профилем:")
    errors = await scenario_with_profile()
    print("\nСценарий 2 — разово, без профиля:")
    errors += await scenario_without_profile()

    if errors:
        print("\n❌ " + "; ".join(errors))
        return 1
    print("\n✅ Оба сценария проходят")
    return 0


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
