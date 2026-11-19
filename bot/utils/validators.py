"""Валидация полей договора. Каждый валидатор возвращает нормализованное значение
или возбуждает ValueError с понятной пользователю подсказкой."""
import re
from datetime import date, datetime

VIN_ALLOWED = re.compile(r"^[A-HJ-NPR-Z0-9]{17}$")  # без I, O, Q — как в стандарте VIN


def clean(text: str) -> str:
    return " ".join(text.strip().split())


def validate_fio(value: str) -> str:
    v = clean(value)
    if len(v) < 5:
        raise ValueError("Слишком коротко. Пример: Иванов Иван Иванович")
    if len(v) > 200:
        raise ValueError("Слишком длинно. Максимум 200 символов")
    if not re.fullmatch(r"[А-Яа-яЁёA-Za-z\-\s.]+", v):
        raise ValueError("Допустимы только буквы, пробел, дефис и точка")
    if len(v.split()) < 2:
        raise ValueError("Укажите фамилию и имя. Пример: Иванов Иван Иванович")
    return v


def validate_gender(value: str) -> str:
    v = value.strip().lower()
    if v.startswith("м"):
        return "м"
    if v.startswith("ж"):
        return "ж"
    raise ValueError("Введите «м» или «ж»")


def validate_passport_series(value: str) -> str:
    v = re.sub(r"\D", "", value)
    if len(v) != 4:
        raise ValueError("Серия паспорта — 4 цифры. Пример: 4507")
    return v


def validate_passport_number(value: str) -> str:
    v = re.sub(r"\D", "", value)
    if len(v) != 6:
        raise ValueError("Номер паспорта — 6 цифр. Пример: 123456")
    return v


def validate_dept_code(value: str) -> str:
    digits = re.sub(r"\D", "", value)
    if len(digits) != 6:
        raise ValueError("Код подразделения — 6 цифр. Пример: 770-001")
    return f"{digits[:3]}-{digits[3:]}"


def validate_date(value: str) -> str:
    v = clean(value)
    for fmt in ("%d.%m.%Y", "%d.%m.%y", "%d-%m-%Y", "%d/%m/%Y"):
        try:
            return datetime.strptime(v, fmt).strftime("%d.%m.%Y")
        except ValueError:
            continue
    raise ValueError("Дата в формате ДД.ММ.ГГГГ. Пример: 21.03.2019")


def validate_past_date(value: str) -> str:
    norm = validate_date(value)
    d = datetime.strptime(norm, "%d.%m.%Y").date()
    if d > date.today():
        raise ValueError("Дата не может быть в будущем")
    if d.year < 1900:
        raise ValueError("Слишком старая дата")
    return norm


def validate_text(max_len: int = 300):
    def _v(value: str) -> str:
        v = clean(value)
        if len(v) < 3:
            raise ValueError("Слишком коротко, введите полное значение")
        if len(v) > max_len:
            raise ValueError(f"Слишком длинно, максимум {max_len} символов")
        return v
    return _v


def validate_address(value: str) -> str:
    v = clean(value)
    if len(v) < 10:
        raise ValueError("Адрес полностью: индекс, город, улица, дом, квартира")
    if not re.search(r"\d", v):
        raise ValueError("В адресе должен быть номер дома")
    return v


def validate_phone(value: str) -> str:
    digits = re.sub(r"\D", "", value)
    if len(digits) == 11 and digits[0] in "78":
        return f"+7 ({digits[1:4]}) {digits[4:7]}-{digits[7:9]}-{digits[9:11]}"
    if len(digits) == 10:
        return f"+7 ({digits[0:3]}) {digits[3:6]}-{digits[6:8]}-{digits[8:10]}"
    raise ValueError("Телефон в формате +7 (999) 123-45-67")


def validate_vin(value: str) -> str:
    v = clean(value).upper().replace(" ", "")
    if len(v) != 17:
        raise ValueError(f"VIN — ровно 17 символов, вы ввели {len(v)}")
    if not VIN_ALLOWED.fullmatch(v):
        raise ValueError("VIN: только латинские буквы и цифры, без I, O, Q")
    return v


def validate_year(value: str) -> int:
    v = re.sub(r"\D", "", value)
    if len(v) != 4:
        raise ValueError("Год — 4 цифры. Пример: 2014")
    year = int(v)
    if not (1950 <= year <= date.today().year + 1):
        raise ValueError(f"Год должен быть от 1950 до {date.today().year + 1}")
    return year


def validate_gosnomer(value: str) -> str:
    v = clean(value).upper().replace(" ", "")
    if v in ("", "-", "НЕТ", "ОТСУТСТВУЕТ"):
        return "отсутствует"
    if not re.fullmatch(r"[АВЕКМНОРСТУХ]\d{3}[АВЕКМНОРСТУХ]{2}\d{2,3}", v):
        raise ValueError("Формат: А123ВС777 (русские буквы). Пример: О456ММ99")
    return v


def validate_pts_sts_number(value: str) -> str:
    v = clean(value).upper()
    digits = re.sub(r"\D", "", v)
    if len(digits) == 10:
        return f"{digits[:4]} {digits[4:]}"
    if len(v) < 6:
        raise ValueError("Серия и номер через пробел. Пример: 63 НТ 123456")
    return v


def validate_int(value: str, minimum: int = 0, maximum: int = 10**9) -> int:
    digits = re.sub(r"\D", "", value)
    if not digits:
        raise ValueError("Введите число. Пример: 187000")
    n = int(digits)
    if n < minimum or n > maximum:
        raise ValueError(f"Допустимое значение — от {minimum} до {maximum}")
    return n


def validate_money(value: str) -> int:
    v = re.sub(r"[^\d,.]", "", value)
    if not v:
        raise ValueError("Введите сумму цифрами. Пример: 1250000")
    v = v.replace(",", ".").replace(" ", "")
    if v.count(".") > 1:
        raise ValueError("Введите сумму цифрами. Пример: 1250000")
    try:
        amount = float(v)
    except ValueError:
        raise ValueError("Введите сумму цифрами. Пример: 1250000") from None
    if amount <= 0:
        raise ValueError("Сумма должна быть больше нуля")
    if amount > 100_000_000:
        raise ValueError("Слишком большая сумма, проверьте ввод")
    return int(round(amount * 100))  # в копейках
