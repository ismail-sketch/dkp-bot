"""Сумма прописью и дата словами — по правилам русского языка, со склонениями."""

_UNITS_M = ["", "один", "два", "три", "четыре", "пять", "шесть", "семь", "восемь", "девять"]
_UNITS_F = ["", "одна", "две", "три", "четыре", "пять", "шесть", "семь", "восемь", "девять"]
_TEENS = ["десять", "одиннадцать", "двенадцать", "тринадцать", "четырнадцать",
          "пятнадцать", "шестнадцать", "семнадцать", "восемнадцать", "девятнадцать"]
_TENS = ["", "", "двадцать", "тридцать", "сорок", "пятьдесят",
         "шестьдесят", "семьдесят", "восемьдесят", "девяносто"]
_HUNDREDS = ["", "сто", "двести", "триста", "четыреста", "пятьсот",
             "шестьсот", "семьсот", "восемьсот", "девятьсот"]

# (формы для 1 / 2-4 / 5-20, род)
_GROUPS = [
    (("", "", ""), "m"),
    (("тысяча", "тысячи", "тысяч"), "f"),
    (("миллион", "миллиона", "миллионов"), "m"),
    (("миллиард", "миллиарда", "миллиардов"), "m"),
]

MONTHS_GEN = ["января", "февраля", "марта", "апреля", "мая", "июня",
              "июля", "августа", "сентября", "октября", "ноября", "декабря"]


def _plural(n: int, forms: tuple[str, str, str]) -> str:
    n = abs(n) % 100
    if 11 <= n <= 19:
        return forms[2]
    n %= 10
    if n == 1:
        return forms[0]
    if 2 <= n <= 4:
        return forms[1]
    return forms[2]


def _triad(n: int, gender: str) -> list[str]:
    """Число 1..999 словами."""
    words: list[str] = []
    h, rest = divmod(n, 100)
    if h:
        words.append(_HUNDREDS[h])
    t, u = divmod(rest, 10)
    if t == 1:
        words.append(_TEENS[u])
        return words
    if t:
        words.append(_TENS[t])
    if u:
        words.append(_UNITS_F[u] if gender == "f" else _UNITS_M[u])
    return words


def number_to_words(n: int) -> str:
    if n == 0:
        return "ноль"
    groups: list[str] = []
    idx = 0
    while n > 0:
        n, rem = divmod(n, 1000)
        if rem == 0:
            idx += 1
            continue
        forms, gender = _GROUPS[idx] if idx < len(_GROUPS) else (("", "", ""), "m")
        words = _triad(rem, gender)
        if forms[0]:
            words.append(_plural(rem, forms))
        groups.insert(0, " ".join(words))
        idx += 1
    return " ".join(groups)


def rubles_to_words(kopecks: int) -> str:
    """125000050 -> «Один миллион двести пятьдесят тысяч рублей 50 копеек»."""
    rub = kopecks // 100
    kop = kopecks % 100
    rub_word = _plural(rub, ("рубль", "рубля", "рублей"))
    kop_word = _plural(kop, ("копейка", "копейки", "копеек"))
    text = f"{number_to_words(rub)} {rub_word} {kop:02d} {kop_word}"
    return text[0].upper() + text[1:]


def split_money_words(kopecks: int) -> tuple[str, str]:
    """Для бланка с полями «Цифрами» и «Прописью».

    125000000 -> ('1 250 000', 'Один миллион двести пятьдесят тысяч рублей 00 копеек')
    Копейки в «цифрах» показываем только если они есть.
    """
    rub = kopecks // 100
    kop = kopecks % 100
    digits = f"{rub:,}".replace(",", " ")
    if kop:
        digits += f",{kop:02d}"
    return digits, rubles_to_words(kopecks)


def date_to_text(value: str) -> str:
    """'21.03.2019' -> '21 марта 2019 г.'"""
    d, m, y = value.split(".")
    return f"{int(d)} {MONTHS_GEN[int(m) - 1]} {y} г."


def date_to_text_short(value: str) -> str:
    """'21.03.2019' -> '21 марта 2019' (без «г.» — когда дальше идёт «года рождения»)."""
    d, m, y = value.split(".")
    return f"{int(d)} {MONTHS_GEN[int(m) - 1]} {y}"


def city_text(city: str) -> str:
    """'Краснодар' -> 'г. Краснодар'; 'г. Краснодар' -> без дубля."""
    c = city.strip()
    low = c.lower()
    if low.startswith(("г.", "г ", "город")):
        return c
    return f"г. {c}"


def fio_short(full_name: str) -> str:
    """Иванов Иван Иванович -> Иванов И. И."""
    parts = full_name.split()
    if len(parts) < 2:
        return full_name
    initials = " ".join(f"{p[0]}." for p in parts[1:3])
    return f"{parts[0]} {initials}"


def initials(full_name: str) -> str:
    """Иванов Иван Иванович -> И. И. Иванов (для подписи)."""
    parts = full_name.split()
    if len(parts) < 2:
        return full_name
    return f"{' '.join(p[0] + '.' for p in parts[1:3])} {parts[0]}"
