"""Бланк договора купли-продажи ТС — одна страница на экземпляр.

Геометрия (координаты линеек, кегли, отступы) снята с типового бланка,
принятого в практике сделок. Шрифт Liberation Sans метрически совместим
с Arial, поэтому переносы строк совпадают с оригиналом.
"""
from __future__ import annotations

from fpdf import FPDF

from config import FONTS_DIR
from bot.utils.money import city_text, date_to_text, split_money_words

FONT = "Lib"
PAGE_W, PAGE_H = 595.28, 841.89
LEFT, RIGHT = 30.0, 565.3
CONTENT_W = RIGHT - LEFT

# y-координаты линеек и подписей (pt)
Y_HDR_RULE = 31.2
Y_TITLE = 59.2
SELLER_RULES = (96.1, 117.6, 139.0, 160.4)
BUYER_RULES = (199.4, 220.8, 242.3, 263.7)
Y_SELLER_TAIL = 168.3
Y_BUYER_TAIL = 271.5
Y_SEC1 = 301.3
Y_SEC1_TEXT = 322.0
GRID_RULES = (363.9, 385.6, 407.3, 429.0, 450.7, 472.4)
ROW_H = 21.7  # высота строки таблицы ТС
Y_SEC2 = 503.4
Y_PRICE_RULE = 538.0
Y_SEC3 = 567.8
PARA_Y = (587.5, 628.5, 669.5)
Y_SIGN_TITLE = 703.7
SIGN1_RULE = 736.2
Y_SIGN_CAPTION = 750.9
SIGN2_RULE = 786.9
LEADING = 12.4

# три одинаковых экземпляра: продавцу, покупателю и для ГИБДД
COPIES = (1, 2, 3)

# три колонки таблицы ТС: (x начала, правый край ячейки)
COL_X = (LEFT, 213.4, 396.9)
COL_W = 168.4


class Form(FPDF):
    def __init__(self) -> None:
        super().__init__(orientation="P", unit="pt", format="A4")
        self.set_auto_page_break(False)
        self.set_margins(LEFT, 20, PAGE_W - RIGHT)
        self.c_margin = 0  # убираем внутренний отступ ячейки: текст встаёт точно по x
        self.add_font(FONT, "", str(FONTS_DIR / "LiberationSans-Regular.ttf"))
        self.add_font(FONT, "B", str(FONTS_DIR / "LiberationSans-Bold.ttf"))
        self.set_text_color(0, 0, 0)

    def rule(self, x1: float, y: float, x2: float) -> None:
        self.set_draw_color(0, 0, 0)
        self.set_line_width(0.5)
        self.line(x1, y, x2, y)

    def baseline(self, top: float, size: float) -> float:
        """Верх текста -> базовая линия."""
        return top + size * 0.9

    def label(self, x: float, top: float, text: str, size: float = 6.0) -> None:
        self.set_font(FONT, "", size)
        self.text(x, self.baseline(top, size), text)

    def value(self, x: float, baseline: float, width: float, text: str,
              size: float = 8.0, style: str = "") -> None:
        """Значение поля с подгонкой кегля под ширину."""
        eff = _fit_size(self, text, width, size, 5.5, style)
        self.set_font(FONT, style, eff)
        self.text(x, baseline, text)

    def para(self, top: float, text: str, size: float = 8.0) -> None:
        self.set_font(FONT, "", size)
        self.set_xy(LEFT, top - size * 0.22)
        self.multi_cell(CONTENT_W, LEADING, text, markdown=True,
                        new_x="LMARGIN", new_y="NEXT")


def _fit_size(pdf: FPDF, text: str, width: float, max_size: float = 8.0,
              min_size: float = 5.5, style: str = "") -> float:
    size = max_size
    while size > min_size:
        pdf.set_font(FONT, style, size)
        if pdf.get_string_width(text) <= width:
            return size
        size -= 0.25
    return min_size


def _wrapped(pdf: FPDF, text: str, width: float, size: float) -> list[str]:
    pdf.set_font(FONT, "", size)
    return [ln for ln in pdf.multi_cell(width, LEADING, text,
                                        dry_run=True, output="LINES") if ln.strip()]


def _cell_text(pdf: Form, x: float, width: float, top: float, bottom: float,
               text: str) -> None:
    """Текст по центру строки бланка; при нехватке места уменьшаем кегль."""
    size = 8.0
    lines = _wrapped(pdf, text, width, size)
    while len(lines) > 2 and size > 5.5:
        size -= 0.25
        lines = _wrapped(pdf, text, width, size)

    step = size * 1.15
    first = top + (bottom - top - step * len(lines)) / 2 + size * 0.85
    pdf.set_font(FONT, "", size)
    for i, line in enumerate(lines):
        pdf.text(x, first + i * step, line)


# ------------------------------------------------------------------ блоки
def _header(pdf: Form, data: dict) -> None:
    pdf.rule(217.0, Y_HDR_RULE, 474.0)
    pdf.rule(485.3, Y_HDR_RULE, 565.3)
    pdf.label(217.0, 31.9, "Город и дата составления договора")
    pdf.label(485.3, 31.9, "Номер договора")

    pdf.value(217.0, Y_HDR_RULE - 3.0, 250.0,
              f"{city_text(data['city'])}, {date_to_text(data['date'])}")
    pdf.value(485.3, Y_HDR_RULE - 3.0, 78.0, data.get("contract_no") or "б/н")


def _person(pdf: Form, rules: tuple, lines: list[str], tail_y: float, tail: str) -> None:
    for y in rules:
        pdf.rule(LEFT, y, RIGHT)
    for i in range(len(rules) - 1):
        _cell_text(pdf, LEFT, CONTENT_W, rules[i], rules[i + 1], lines[i])
    pdf.set_font(FONT, "", 8)
    pdf.text(LEFT, pdf.baseline(tail_y, 8), tail)


def _grid(pdf: Form, car: dict) -> None:
    rows = [
        # (label, value, колонок)
        [("Марка и модель ТС", f"{car['brand']} {car['model']}", 1)],
        [("VIN", car["vin"], 3),
         ("Госномер", car.get("gosnomer") or "отсутствует", 3),
         ("Год выпуска", str(car["year"]), 3)],
        [("Модель и номер двигателя", car.get("engine_no") or "не указан", 3),
         ("Номер шасси, рама", car.get("chassis_no") or "отсутствует", 3),
         ("Номер кузова", car.get("body_no") or "отсутствует", 3)],
        [("Тип ТС", car.get("type") or "Легковой", 3),
         ("Цвет кузова", car["color"], 3),
         ("Пробег", f"{car['mileage']} км" if car.get("mileage") else "не указан", 3)],
        [("Номер ПТС, кем и когда выдан/код подразделения",
          f"{car['pts_series_no']}, {car['pts_issued_by']}, {car['pts_date']}", 1)],
        [("Номер СТС, когда и кем выдан/код подразделения",
          f"{car['sts_series_no']}, {car['sts_date']}", 1)],
    ]
    body = rows[1:4]

    pdf.rule(LEFT, GRID_RULES[0], RIGHT)
    # строка «Марка и модель ТС» — на всю ширину
    top, bottom = GRID_RULES[0], GRID_RULES[1]
    pdf.label(LEFT, top + 0.8, rows[0][0][0])
    pdf.value(LEFT, bottom - 4.0, CONTENT_W, rows[0][0][1])
    pdf.rule(LEFT, bottom, RIGHT)

    # три строки по три колонки — в образце только горизонтальные линейки
    for r, cells in enumerate(body, start=1):
        top, bottom = GRID_RULES[r], GRID_RULES[r + 1]
        for i, (label, val, _) in enumerate(cells):
            x = COL_X[i]
            pdf.label(x, top + 0.8, label)
            pdf.value(x, bottom - 4.0, COL_W, str(val))
        pdf.rule(LEFT, bottom, RIGHT)

    # ПТС и СТС — на всю ширину. У СТС (последней строки) нет нижней линейки,
    # но высота строки должна быть полной, иначе текст наезжает на ПТС.
    for offset, cells in ((4, rows[4]), (5, rows[5])):
        top = GRID_RULES[offset]
        bottom = top + ROW_H
        pdf.label(LEFT, top + 0.8, cells[0][0])
        pdf.value(LEFT, bottom - 4.0, CONTENT_W, str(cells[0][1]))
        if offset < 5:
            pdf.rule(LEFT, bottom, RIGHT)


def _price(pdf: Form, data: dict) -> None:
    digits, words = split_money_words(data["price_kopecks"])
    y = Y_PRICE_RULE

    pdf.label(LEFT, y + 1.1, "Цифрами")
    pdf.label(151.8, y + 1.1, "Прописью")
    pdf.rule(LEFT, y, 120.0)
    pdf.rule(151.8, y, 566.8)

    pdf.set_font(FONT, "", 8)
    pdf.text(123.0, y - 3.2, "руб.")
    size = _fit_size(pdf, digits, 86.0)
    pdf.set_font(FONT, "", size)
    pdf.text(118.0 - pdf.get_string_width(digits), y - 3.2, digits)
    pdf.value(151.8, y - 3.2, 413.0, words)


def _paragraphs(pdf: Form) -> None:
    blocks = [
        "3.1. ТС передано продавцом и принято покупателем при заключении сторонами "
        "настоящего договора. ТС пригодно для использования по его целевому назначению. "
        "Претензий по техническому состоянию, состоянию кузова и характеристикам (качеству) "
        "ТС покупатель не имеет. Отдельного документа о передаче ТС сторонами не составляется.",
        "3.2. Продавец гарантирует, что на дату заключения настоящего договора указанное ТС "
        "находится у него в собственности на законном основании, свободно от прав третьих лиц, "
        "никому не продано, не подарено, не заложено, в споре и под арестом (запрещением) "
        "не состоит, ограничения в пользовании ТС отсутствуют.",
        "3.3. Настоящий договор вступает в силу с момента подписания и составлен в "
        "**трех экземплярах**, имеющих равную юридическую силу. Настоящий договор действует "
        "до полного исполнения сторонами принятых на себя обязательств.",
    ]

    size = 8.0
    while size > 7.0:
        pdf.set_font(FONT, "", size)
        total = sum(len(pdf.multi_cell(CONTENT_W, LEADING, b, dry_run=True, output="LINES"))
                    for b in blocks)
        if PARA_Y[0] + total * LEADING <= SIGN1_RULE - 6:
            break
        size -= 0.25

    for y, text in zip(PARA_Y, blocks):
        pdf.para(y, text, size=size)


def _sign_rows(pdf: Form, rule_y: float, label_top: float) -> None:
    for x in (LEFT, 163.8, 312.6, 446.5):
        pdf.rule(x, rule_y, x + 118.8)
    pdf.label(LEFT, label_top, "Подпись")
    pdf.label(163.8, label_top, "Расшифровка")
    pdf.label(312.6, label_top, "Подпись")
    pdf.label(446.5, label_top, "Расшифровка")


def _signatures(pdf: Form, seller: dict, buyer: dict) -> None:
    pdf.set_font(FONT, "B", 8)
    pdf.text(LEFT, pdf.baseline(Y_SIGN_TITLE, 8), "Продавец")
    pdf.text(312.6, pdf.baseline(Y_SIGN_TITLE, 8), "Покупатель")

    _sign_rows(pdf, SIGN1_RULE, SIGN1_RULE + 0.8)
    pdf.value(163.8, SIGN1_RULE - 3.0, 115.0, seller["full_name"], 7.5)
    pdf.value(446.5, SIGN1_RULE - 3.0, 115.0, buyer["full_name"], 7.5)

    pdf.set_font(FONT, "", 8)
    pdf.text(LEFT, pdf.baseline(Y_SIGN_CAPTION, 8),
             "денежные средства в сумме, указанной в пункте 2, получил")
    pdf.text(312.6, pdf.baseline(Y_SIGN_CAPTION, 8),
             "ТС, указанное в пункте 1, получил")

    _sign_rows(pdf, SIGN2_RULE, SIGN2_RULE + 0.8)
    pdf.value(163.8, SIGN2_RULE - 3.0, 115.0, seller["full_name"], 7.5)
    pdf.value(446.5, SIGN2_RULE - 3.0, 115.0, buyer["full_name"], 7.5)


def _person_lines(person: dict) -> list[str]:
    birth = date_to_text(person["birth_date"]).replace(" г.", "")
    issued = person["passport_issued_by"]
    issued_at = date_to_text(person["passport_issue_date"]).replace(" г.", "")
    return [
        f"{person['full_name']}, {birth} года рождения",
        f"паспорт РФ {person['passport_series']} № {person['passport_number']}, "
        f"выдан {issued} {issued_at}",
        f"код подразделения {person['passport_dept_code']}, "
        f"адрес регистрации: {person['registration_address']}",
    ]


# ------------------------------------------------------------------ сборка
def build(data: dict) -> bytes:
    seller, buyer, car = data["seller"], data["buyer"], data["car"]
    pdf = Form()

    for _ in COPIES:
        pdf.add_page()
        _header(pdf, data)

        pdf.set_font(FONT, "B", 14)
        pdf.text(LEFT, pdf.baseline(Y_TITLE, 14),
                 "Договор купли-продажи транспортного средства")

        _person(pdf, SELLER_RULES, _person_lines(seller), Y_SELLER_TAIL,
                "именуемый(ая) в дальнейшем «Продавец», и")
        _person(pdf, BUYER_RULES, _person_lines(buyer), Y_BUYER_TAIL,
                "именуемый(ая) в дальнейшем «Покупатель», заключили настоящий "
                "договор о нижеследующем:")

        pdf.set_font(FONT, "B", 11)
        pdf.text(LEFT, pdf.baseline(Y_SEC1, 11), "1. Предмет договора")
        pdf.set_font(FONT, "", 8)
        pdf.set_xy(LEFT, Y_SEC1_TEXT - 1.8)
        pdf.multi_cell(CONTENT_W, LEADING,
                       "Продавец передает принадлежащее ему на праве собственности транспортное "
                       "средство (в дальнейшем ТС) покупателю, а покупатель принимает указанное "
                       "транспортное средство и обязуется уплатить за него денежную сумму, "
                       "указанную в п.2 настоящего договора.",
                       new_x="LMARGIN", new_y="NEXT")

        _grid(pdf, car)

        pdf.set_font(FONT, "B", 11)
        pdf.text(LEFT, pdf.baseline(Y_SEC2, 11), "2. Стоимость ТС")
        _price(pdf, data)

        pdf.set_font(FONT, "B", 11)
        pdf.text(LEFT, pdf.baseline(Y_SEC3, 11), "3. Ответственность и гарантии")
        _paragraphs(pdf)

        _signatures(pdf, seller, buyer)

    return bytes(pdf.output())
