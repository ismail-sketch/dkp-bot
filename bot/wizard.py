"""Универсальный пошаговый визард.

Один и тот же движок обслуживает: профиль пользователя, контрагента,
автомобиль и условия сделки. Поля описаны декларативно — добавить поле
значит добавить строку в список, а не писать новый обработчик.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Callable

from aiogram.fsm.context import FSMContext
from aiogram.types import Message

from bot.keyboards import (BTN_BACK, BTN_CANCEL, BTN_SKIP, gender_kb, main_menu,
                           remove_kb, skip_kb)
from bot.states import CarForm, PersonForm, TermsForm
from bot.utils import validators as v

Validator = Callable[[str], Any]


@dataclass(frozen=True)
class Field:
    state: Any
    key: str
    title: str
    example: str
    validator: Validator
    optional: bool = False
    kind: str = "text"  # text | gender | money | int | date


# ---------------------------------------------------------------- формы
PERSON_FIELDS: list[Field] = [
    Field(PersonForm.full_name, "full_name", "ФИО полностью",
          "Иванов Иван Иванович", v.validate_fio),
    Field(PersonForm.gender, "gender", "Пол (нужно для согласования слов в договоре)",
          "Мужской или Женский", v.validate_gender, kind="gender"),
    Field(PersonForm.birth_date, "birth_date", "Дата рождения",
          "21.03.1985", v.validate_past_date),
    Field(PersonForm.passport_series, "passport_series", "Серия паспорта",
          "4507", v.validate_passport_series),
    Field(PersonForm.passport_number, "passport_number", "Номер паспорта",
          "123456", v.validate_passport_number),
    Field(PersonForm.passport_issued_by, "passport_issued_by", "Кем выдан паспорт",
          "ОВД Центрального округа г. Краснодара", v.validate_text(300)),
    Field(PersonForm.passport_issue_date, "passport_issue_date", "Дата выдачи паспорта",
          "14.10.2012", v.validate_past_date),
    Field(PersonForm.passport_dept_code, "passport_dept_code", "Код подразделения",
          "232-001", v.validate_dept_code),
    Field(PersonForm.registration_address, "registration_address", "Адрес регистрации",
          "г. Краснодар, ул. Красная, д. 15, кв. 42", v.validate_address),
    Field(PersonForm.phone, "phone", "Телефон", "+7 (999) 123-45-67",
          v.validate_phone, optional=True),
]

CAR_FIELDS: list[Field] = [
    Field(CarForm.brand, "brand", "Марка автомобиля", "Toyota", v.validate_text(60)),
    Field(CarForm.model, "model", "Модель", "Camry", v.validate_text(60)),
    Field(CarForm.year, "year", "Год выпуска", "2014", v.validate_year, kind="int"),
    Field(CarForm.vin, "vin", "VIN (идентификационный номер)",
          "JTNBK46K70J123456", v.validate_vin),
    Field(CarForm.body_no, "body_no", "Номер кузова", "JTNBK46K70J123456",
          v.validate_text(40), optional=True),
    Field(CarForm.chassis_no, "chassis_no", "Номер шасси (рамы)",
          "отсутствует", v.validate_text(40), optional=True),
    Field(CarForm.engine_no, "engine_no", "Номер двигателя", "2AR1234567",
          v.validate_text(40), optional=True),
    Field(CarForm.color, "color", "Цвет", "чёрный", v.validate_text(40)),
    Field(CarForm.ts_type, "type", "Тип ТС", "Легковой",
          v.validate_text(30), optional=True),
    Field(CarForm.mileage, "mileage", "Пробег, км", "187000",
          lambda s: v.validate_int(s, 0, 3_000_000), optional=True, kind="int"),
    Field(CarForm.power, "power", "Мощность двигателя, л.с.", "181",
          lambda s: v.validate_int(s, 1, 2000), optional=True, kind="int"),
    Field(CarForm.volume, "volume", "Объём двигателя, см³", "2494",
          lambda s: v.validate_int(s, 1, 20000), optional=True, kind="int"),
    Field(CarForm.gosnomer, "gosnomer", "Госномер", "О456ММ99", v.validate_gosnomer,
          optional=True),
    Field(CarForm.pts_series_no, "pts_series_no", "ПТС: серия и номер",
          "77 УН 123456", v.validate_pts_sts_number),
    Field(CarForm.pts_date, "pts_date", "ПТС: дата выдачи",
          "15.06.2014", v.validate_past_date),
    Field(CarForm.pts_issued_by, "pts_issued_by", "ПТС: кем выдан",
          "ООО «Тойота Мотор»", v.validate_text(300)),
    Field(CarForm.sts_series_no, "sts_series_no", "СТС: серия и номер",
          "99 12 345678", v.validate_pts_sts_number),
    Field(CarForm.sts_date, "sts_date", "СТС: дата выдачи",
          "20.07.2014", v.validate_past_date),
]

TERMS_FIELDS: list[Field] = [
    Field(TermsForm.price, "price", "Цена автомобиля, ₽", "1250000",
          v.validate_money, kind="money"),
    Field(TermsForm.city, "city", "Город составления договора",
          "г. Краснодар", v.validate_text(100)),
    Field(TermsForm.deal_date, "deal_date", "Дата договора", "18.11.2026",
          v.validate_past_date, optional=True),
]

FORMS: dict[str, list[Field]] = {
    "person": PERSON_FIELDS,
    "car": CAR_FIELDS,
    "terms": TERMS_FIELDS,
}

STATE_TO_FORM: dict[str, str] = {
    f.state.state: name for name, fields in FORMS.items() for f in fields
}


def _current(data: dict, form: str, key: str):
    """Текущее значение поля — для режима редактирования."""
    source = {"person": "_person", "car": "_car", "terms": "_terms"}[form]
    return data.get(source, {}).get(key)


def _field_index(form: str, state_name: str) -> int:
    return next(i for i, f in enumerate(FORMS[form]) if f.state.state == state_name)


async def ask(message: Message, state: FSMContext, frame: int | None = None,
              intro: str = "") -> None:
    """Задать текущий (или указанный по индексу) вопрос формы."""
    data = await state.get_data()
    form = data["_form"]
    fields = FORMS[form]
    idx = frame if frame is not None else data.get("_idx", 0)

    if idx >= len(fields):
        return

    field = fields[idx]
    await state.set_state(field.state)
    await state.update_data(_idx=idx)

    current_value = _current(data, form, field.key)

    total = len(fields)
    lines = [f"<b>{intro}</b>"] if intro else []
    lines.append(f"<i>Шаг {idx + 1} из {total}</i>")
    lines.append(f"\n<b>{field.title}</b>")
    if current_value not in (None, "", 0):
        shown = current_value / 100 if field.kind == "money" else current_value
        lines.append(f"Сейчас: <b>{shown}</b>")
        lines.append("Отправьте <code>.</code>, чтобы оставить как есть.")
    elif field.optional:
        lines.append("Можно пропустить кнопкой ниже или отправить <code>.</code>")
    lines.append(f"Например: <code>{field.example}</code>")

    kb = gender_kb() if field.kind == "gender" else skip_kb(field.optional)

    prev_error = data.get("_error")
    if prev_error:
        lines.insert(0, f"⚠️ {prev_error}\n")
        await state.update_data(_error=None)

    await message.answer("\n".join(lines), reply_markup=kb)


async def start(message: Message, state: FSMContext, form: str, intro: str = "") -> None:
    await state.update_data(_form=form, _idx=0, _error=None)
    await message.answer(intro or "Заполняем по шагам.", reply_markup=remove_kb())
    await ask(message, state, 0)


async def handle(message: Message, state: FSMContext) -> str | None:
    """Обработать ответ на текущий вопрос.

    Возвращает:
      None — форма продолжается,
      "cancelled" — пользователь отменил,
      "done:<form>" — форма завершена.
    """
    text = (message.text or "").strip()
    data = await state.get_data()
    form = data.get("_form")
    current = await state.get_state()

    if text == BTN_CANCEL:
        await state.clear()
        return "cancelled"
    if text == BTN_BACK:
        idx = max(0, data.get("_idx", 0) - 1)
        await ask(message, state, idx)
        return None
    if form is None or current is None or current not in STATE_TO_FORM:
        return None

    fields = FORMS[form]
    idx = _field_index(form, current)
    field = fields[idx]

    if text == BTN_SKIP and field.optional:
        value = "" if field.kind in ("text", "date") else 0
        await _save_value(state, field, value)
        return await _advance(message, state, form, idx)

    if text == ".":
        current_value = _current(data, form, field.key)
        if current_value not in (None, "", 0):
            # значение уже есть — оставляем как есть
            return await _advance(message, state, form, idx)
        if field.optional:
            # пустое необязательное поле — «.» работает как «пропустить»
            await _save_value(state, field, "" if field.kind in ("text", "date") else 0)
            return await _advance(message, state, form, idx)
        # обязательное и пустое: подсказываем и остаёмся на шаге, но без тупика —
        # пользователь может ввести значение, нажать «Назад» или «Отмена»
        await state.update_data(
            _error="Это поле обязательное. Введите значение, нажмите «Назад» или «Отмена»."
        )
        await ask(message, state, idx)
        return None

    try:
        value = field.validator(text)
    except ValueError as exc:
        await state.update_data(_error=str(exc))
        await ask(message, state, idx)
        return None

    await _save_value(state, field, value)
    return await _advance(message, state, form, idx)


async def _save_value(state: FSMContext, field: Field, value: Any) -> None:
    data = await state.get_data()
    form = data["_form"]
    if form == "person":
        person = data.get("_person", {})
        person[field.key] = value
        await state.update_data(_person=person)
    elif form == "car":
        car = data.get("_car", {})
        car[field.key] = value
        await state.update_data(_car=car)
    else:
        terms = data.get("_terms", {})
        terms[field.key] = value
        await state.update_data(_terms=terms)


async def _advance(message: Message, state: FSMContext, form: str, idx: int) -> str | None:
    if idx + 1 < len(FORMS[form]):
        await ask(message, state, idx + 1)
        return None
    return f"done:{form}"
