"""Точечное редактирование отдельных полей готовой сделки.

Пользователь выбирает конкретное поле (например «Цена»), вводит новое значение —
и сразу возвращается к сводке. Не нужно проходить весь блок заново.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Callable

from aiogram.fsm.context import FSMContext
from aiogram.types import Message

from bot.utils import validators as v

# ключ поля -> (заголовок, пример, валидатор, куда писать, имя ключа в данных)
# «куда писать»: me | cp | car | terms
FIELDS: dict[str, tuple[str, str, Callable[[str], Any], str, str]] = {
    # --- стороны ---
    "seller.full_name": ("ФИО продавца", "Иванов Иван Иванович",
                         v.validate_fio, "side", "full_name"),
    "buyer.full_name": ("ФИО покупателя", "Петров Пётр Петрович",
                        v.validate_fio, "side", "full_name"),
    "seller.passport": ("Паспорт продавца: серия, номер, кем выдан, дата, код",
                        "4507 123456, ОВД г. Москвы, 14.10.2012, 770-001",
                        None, "passport", ""),
    "buyer.passport": ("Паспорт покупателя: серия, номер, кем выдан, дата, код",
                       "4507 123456, ОВД г. Москвы, 14.10.2012, 770-001",
                       None, "passport", ""),
    # --- авто ---
    "car.brand_model": ("Марка и модель", "Toyota Camry", None, "brand_model", ""),
    "car.vin": ("VIN", "JTNBK46K70J123456", v.validate_vin, "car", "vin"),
    "car.year": ("Год выпуска", "2014", v.validate_year, "car", "year"),
    "car.color": ("Цвет", "чёрный", v.validate_text(40), "car", "color"),
    "car.pts": ("ПТС: серия/номер, кем выдан, дата",
                "77 УН 123456, ООО «Тойота Мотор», 15.06.2014", None, "pts", ""),
    "car.sts": ("СТС: серия/номер, дата выдачи", "99 12 345678, 20.07.2014",
                None, "sts", ""),
    # --- условия ---
    "terms.price": ("Цена, ₽", "1250000", v.validate_money, "terms", "price"),
    "terms.city_date": ("Город и дата договора", "г. Краснодар, 18.11.2026",
                        None, "city_date", ""),
}


def _side_key(state_data: dict, side: str) -> str:
    """seller/buyer -> _me или _cp в зависимости от роли."""
    role = state_data["role"]
    if side == "seller":
        return "_me" if role == "seller" else "_cp"
    return "_cp" if role == "seller" else "_me"


def current_value(state_data: dict, field_key: str) -> str:
    """Текущее значение поля в человекочитаемом виде (для подсказки)."""
    title, _, _, target, name = FIELDS[field_key]
    if target == "side":
        side = field_key.split(".")[0]
        person = state_data.get(_side_key(state_data, side), {})
        return str(person.get(name, "—"))
    if target == "car":
        return str(state_data.get("_car", {}).get(name, "—"))
    if target == "terms":
        val = state_data.get("_terms", {}).get(name)
        return f"{val / 100:,.0f} ₽" if name == "price" and val else str(val or "—")
    if target == "passport":
        side = field_key.split(".")[0]
        p = state_data.get(_side_key(state_data, side), {})
        return (f"{p.get('passport_series', '')} {p.get('passport_number', '')}, "
                f"{p.get('passport_issued_by', '')}, {p.get('passport_issue_date', '')}, "
                f"{p.get('passport_dept_code', '')}")
    if target == "brand_model":
        c = state_data.get("_car", {})
        return f"{c.get('brand', '')} {c.get('model', '')}"
    if target == "pts":
        c = state_data.get("_car", {})
        return f"{c.get('pts_series_no', '')}, {c.get('pts_issued_by', '')}, {c.get('pts_date', '')}"
    if target == "sts":
        c = state_data.get("_car", {})
        return f"{c.get('sts_series_no', '')}, {c.get('sts_date', '')}"
    if target == "city_date":
        t = state_data.get("_terms", {})
        return f"{t.get('city', '')}, {t.get('deal_date', '')}"
    return "—"


def _parse_passport(text: str) -> dict:
    """«4507 123456, ОВД г. Москвы, 14.10.2012, 770-001» -> поля паспорта."""
    parts = [p.strip() for p in text.split(",")]
    if len(parts) < 4:
        raise ValueError(
            "Нужно 4 части через запятую: серия и номер, кем выдан, дата выдачи, код подразделения.\n"
            "Пример: 4507 123456, ОВД г. Москвы, 14.10.2012, 770-001"
        )
    digits = "".join(ch for ch in parts[0] if ch.isdigit())
    if len(digits) != 10:
        raise ValueError("В первой части нужны 10 цифр: серия (4) и номер (6). Пример: 4507 123456")
    return {
        "passport_series": digits[:4],
        "passport_number": digits[4:],
        "passport_issued_by": v.validate_text(300)(parts[1]),
        "passport_issue_date": v.validate_past_date(parts[2]),
        "passport_dept_code": v.validate_dept_code(parts[3]),
    }


def _parse_brand_model(text: str) -> dict:
    parts = text.split(maxsplit=1)
    if len(parts) < 2:
        raise ValueError("Укажите марку и модель через пробел. Пример: Toyota Camry")
    return {"brand": v.validate_text(60)(parts[0]), "model": v.validate_text(60)(parts[1])}


def _parse_pts(text: str) -> dict:
    parts = [p.strip() for p in text.split(",")]
    if len(parts) < 3:
        raise ValueError("Нужно: серия и номер, кем выдан, дата выдачи.\n"
                         "Пример: 77 УН 123456, ООО «Тойота Мотор», 15.06.2014")
    return {
        "pts_series_no": v.validate_pts_sts_number(parts[0]),
        "pts_issued_by": v.validate_text(300)(parts[1]),
        "pts_date": v.validate_past_date(parts[2]),
    }


def _parse_sts(text: str) -> dict:
    parts = [p.strip() for p in text.split(",")]
    if len(parts) < 2:
        raise ValueError("Нужно: серия и номер, дата выдачи. Пример: 99 12 345678, 20.07.2014")
    return {
        "sts_series_no": v.validate_pts_sts_number(parts[0]),
        "sts_date": v.validate_past_date(parts[1]),
    }


def _parse_city_date(text: str) -> dict:
    parts = [p.strip() for p in text.split(",")]
    if len(parts) < 2:
        raise ValueError("Нужно: город, дата. Пример: г. Краснодар, 18.11.2026")
    return {"city": v.validate_text(100)(parts[0]), "deal_date": v.validate_past_date(parts[1])}


def apply(state_data: dict, field_key: str, raw: str) -> dict:
    """Применить новое значение к данным сделки. Возвращает обновлённый dict данных."""
    _, example, validator, target, name = FIELDS[field_key]
    text = raw.strip()

    if target == "side":
        side = field_key.split(".")[0]
        key = _side_key(state_data, side)
        person = dict(state_data.get(key) or {})
        person[name] = validator(text)
        state_data[key] = person
    elif target == "passport":
        side = field_key.split(".")[0]
        key = _side_key(state_data, side)
        person = dict(state_data.get(key) or {})
        person.update(_parse_passport(text))
        state_data[key] = person
    elif target == "car":
        car = dict(state_data.get("_car") or {})
        car[name] = validator(text)
        state_data["_car"] = car
    elif target == "terms":
        terms = dict(state_data.get("_terms") or {})
        terms[name] = validator(text)
        state_data["_terms"] = terms
    elif target == "brand_model":
        car = dict(state_data.get("_car") or {})
        car.update(_parse_brand_model(text))
        state_data["_car"] = car
    elif target == "pts":
        car = dict(state_data.get("_car") or {})
        car.update(_parse_pts(text))
        state_data["_car"] = car
    elif target == "sts":
        car = dict(state_data.get("_car") or {})
        car.update(_parse_sts(text))
        state_data["_car"] = car
    elif target == "city_date":
        terms = dict(state_data.get("_terms") or {})
        terms.update(_parse_city_date(text))
        state_data["_terms"] = terms
    else:
        raise ValueError("Неизвестное поле")

    return state_data


def prompt_text(state_data: dict, field_key: str) -> str:
    title, example, _, _, _ = FIELDS[field_key]
    now = current_value(state_data, field_key)
    return (
        f"✏️ <b>{title}</b>\n\n"
        f"Сейчас: {now}\n\n"
        f"Введите новое значение.\n"
        f"Например: <code>{example}</code>\n\n"
        f"<i>Отправьте «.» чтобы оставить как есть.</i>"
    )
