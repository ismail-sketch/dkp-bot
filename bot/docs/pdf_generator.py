"""Акт приёма-передачи и расписка (fpdf2, шрифт DejaVu с кириллицей).

Договор формируется отдельным модулем contract_form.py по типовому бланку.
LibreOffice не нужен: PDF собирается напрямую из данных, в памяти.
"""
from __future__ import annotations

from fpdf import FPDF
from fpdf.enums import XPos, YPos

from config import FONTS_DIR
from bot.utils.money import (city_text, date_to_text, date_to_text_short, initials,
                             rubles_to_words)

FONT = "DejaVu"


class Doc(FPDF):
    def __init__(self, subtitle: str = "") -> None:
        super().__init__(orientation="P", unit="mm", format="A4")
        self.subtitle = subtitle
        self.add_font(FONT, "", str(FONTS_DIR / "DejaVuSans.ttf"))
        self.add_font(FONT, "B", str(FONTS_DIR / "DejaVuSans-Bold.ttf"))
        self.set_auto_page_break(auto=True, margin=10)
        self.set_margins(12, 10, 12)
        self.set_font(FONT, "", 10)

    # --- примитивы ---
    BODY_LH = 3.8  # высота строки основного текста

    def h1(self, text: str) -> None:
        self.set_font(FONT, "B", 11.5)
        self.multi_cell(0, 5, text, align="C", new_x=XPos.LMARGIN, new_y=YPos.NEXT)
        self.ln(1)

    def h2(self, text: str) -> None:
        self.set_font(FONT, "B", 9)
        self.multi_cell(0, 4.2, text, align="L", new_x=XPos.LMARGIN, new_y=YPos.NEXT)
        self.ln(0.4)

    def p(self, text: str, align: str = "J", size: float = 8.6, bold: bool = False,
          indent: float = 0, gap: float = 0.7) -> None:
        self.set_font(FONT, "B" if bold else "", size)
        if indent:
            self.set_x(self.l_margin + indent)
        self.multi_cell(0, self.BODY_LH, text, align=align, new_x=XPos.LMARGIN, new_y=YPos.NEXT)
        self.ln(gap)

    def kv(self, label: str, value: str, label_w: float = 58) -> None:
        """Строка «Параметр: значение».

        Если метка не помещается в отведённую ширину — значение уходит на
        следующую строку, чтобы текст не накладывался.
        """
        self.set_font(FONT, "", 8.6)
        self.set_x(self.l_margin + 3)
        fits = self.get_string_width(label) <= label_w - 2
        if not fits:
            self.multi_cell(0, 3.9, label, align="L",
                            new_x=XPos.LMARGIN, new_y=YPos.NEXT)
            self.set_x(self.l_margin + 3)
            self.multi_cell(0, 3.9, value or "—", align="L",
                            new_x=XPos.LMARGIN, new_y=YPos.NEXT)
            return
        self.cell(label_w, 3.9, label, new_x=XPos.RIGHT, new_y=YPos.TOP)
        self.multi_cell(0, 3.9, value or "—", align="L",
                        new_x=XPos.LMARGIN, new_y=YPos.NEXT)

    def signature_block(self, left_title: str, left: dict, right_title: str, right: dict) -> None:
        self.ln(2)
        col_w = (self.w - self.l_margin - self.r_margin) / 2 - 3
        x0 = self.l_margin
        y0 = self.get_y()

        for i, (title, person) in enumerate(((left_title, left), (right_title, right))):
            x = x0 + i * (col_w + 6)
            self.set_xy(x, y0)
            self.set_font(FONT, "B", 9.2)
            self.cell(col_w, 4.5, title, new_x=XPos.LEFT, new_y=YPos.NEXT)
            self.set_x(x)
            self.set_font(FONT, "", 8.2)
            self.multi_cell(col_w, 3.9,
                            f"{person['full_name']}\n"
                            f"паспорт {person['passport_series']} № {person['passport_number']}\n"
                            f"{person['registration_address']}",
                            align="L", new_x=XPos.LEFT, new_y=YPos.NEXT)
            self.ln(3)
            self.set_x(x)
            self.cell(col_w * 0.5, 4.5, "Подпись:", new_x=XPos.RIGHT, new_y=YPos.TOP)
            self.cell(col_w * 0.5, 4.5, "/ " + initials(person["full_name"]) + " /",
                      new_x=XPos.LEFT, new_y=YPos.NEXT)
        self.set_y(y0 + 30)

    def copy_mark(self, text: str) -> None:
        self.set_font(FONT, "", 8)
        self.set_text_color(110, 110, 110)
        self.cell(0, 4, text, align="R", new_x=XPos.LMARGIN, new_y=YPos.NEXT)
        self.set_text_color(0, 0, 0)


def _side_text(person: dict, role_word: str) -> str:
    """Описание стороны в преамбуле с согласованием по роду."""
    g = person.get("gender", "м")
    citizen = "гражданка" if g == "ж" else "гражданин"
    return (
        f"{citizen} Российской Федерации "
        f"{person['full_name']}, {date_to_text_short(person['birth_date'])} года рождения, "
        f"паспорт гражданина РФ серия {person['passport_series']} № {person['passport_number']}, "
        f"выдан {person['passport_issued_by']} {date_to_text(person['passport_issue_date'])}, "
        f"код подразделения {person['passport_dept_code']}, "
        f"зарегистрированн{'ая' if g == 'ж' else 'ый'} по адресу: "
        f"{person['registration_address']}, именуем{'ая' if g == 'ж' else 'ый'} в дальнейшем "
        f"«{role_word}»"
    )


def build_contract(data: dict) -> bytes:
    """Договор по типовому одностраничному бланку — 3 экземпляра."""
    from bot.docs.contract_form import build
    return build(data)


def build_act(data: dict) -> bytes:
    """Акт приёма-передачи ТС."""
    seller, buyer, car = data["seller"], data["buyer"], data["car"]
    pdf = Doc()
    pdf.add_page()
    pdf.h1("АКТ\nприёма-передачи транспортного средства")
    pdf.set_font(FONT, "", 10)
    pdf.p(f"к договору купли-продажи транспортного средства от {date_to_text(data['date'])}, "
          f"{city_text(data['city'])}", align="C")

    pdf.p(f"{_side_text(seller, 'Продавец')}, передал, а "
          f"{_side_text(buyer, 'Покупатель')}, принял следующее транспортное средство:")

    pdf.kv("Марка, модель:", f"{car['brand']} {car['model']}")
    pdf.kv("Год выпуска:", str(car["year"]))
    pdf.kv("VIN:", car["vin"])
    pdf.kv("Номер кузова:", car.get("body_no") or "отсутствует")
    pdf.kv("Цвет:", car["color"])
    pdf.kv("Государственный регистрационный знак:", car.get("gosnomer") or "отсутствует")
    if car.get("mileage"):
        pdf.kv("Показания одометра:", f"{car['mileage']} км")
    pdf.ln(2)

    pdf.p("1. ТС передано в технически исправном состоянии, соответствующем условиям "
          "договора. Видимые повреждения и недостатки, о которых Покупатель был "
          "уведомлён до подписания договора: отсутствуют, если не указано иное.")
    pdf.p("2. Одновременно с ТС Покупателю переданы: ключи (2 комплекта), паспорт "
          "транспортного средства (ПТС), свидетельство о регистрации (СТС), "
          "иные принадлежности и документы, предусмотренные договором.")
    pdf.p("3. Расчёт по договору произведён в полном объёме. Стороны претензий "
          "друг к другу по исполнению договора не имеют.")

    pdf.signature_block("Передал (Продавец)", seller, "Принял (Покупатель)", buyer)
    return bytes(pdf.output())


def build_receipt(data: dict) -> bytes:
    """Расписка в получении денежных средств."""
    seller, buyer, car = data["seller"], data["buyer"], data["car"]
    amount = rubles_to_words(data["price_kopecks"])
    pdf = Doc()
    pdf.add_page()
    pdf.h1("РАСПИСКА\nв получении денежных средств")
    pdf.set_font(FONT, "", 10)
    pdf.cell(0, 5, city_text(data["city"]), new_x=XPos.RIGHT, new_y=YPos.TOP)
    pdf.cell(0, 5, date_to_text(data["date"]), align="R", new_x=XPos.LMARGIN, new_y=YPos.NEXT)
    pdf.ln(4)

    g = seller.get("gender", "м")
    pdf.p(f"Я, {seller['full_name']}, {date_to_text_short(seller['birth_date'])} года рождения, "
          f"паспорт гражданина РФ серия {seller['passport_series']} № {seller['passport_number']}, "
          f"выдан {seller['passport_issued_by']} {date_to_text(seller['passport_issue_date'])}, "
          f"код подразделения {seller['passport_dept_code']}, "
          f"зарегистрированн{'ая' if g == 'ж' else 'ый'} по адресу: "
          f"{seller['registration_address']}, настоящим подтверждаю, что получил{'а' if g == 'ж' else ''} "
          f"денежные средства в размере {amount} в счёт оплаты по договору "
          f"купли-продажи транспортного средства {car['brand']} {car['model']}, "
          f"{car['year']} года выпуска, VIN {car['vin']}, "
          f"заключённому {date_to_text_short(data['date'])}.")
    pdf.ln(1)
    pdf.p(f"Покупатель: {buyer['full_name']}, "
          f"паспорт {buyer['passport_series']} № {buyer['passport_number']}, "
          f"{buyer['registration_address']}.")
    pdf.ln(1)
    pdf.p("Денежные средства получены в полном объёме. Претензий к Покупателю "
          "по расчётам не имею.")
    pdf.ln(8)
    pdf.set_font(FONT, "", 10)
    pdf.cell(60, 5, "Деньги получил:", new_x=XPos.RIGHT, new_y=YPos.TOP)
    pdf.cell(60, 5, "/ " + initials(seller["full_name"]) + " /",
             new_x=XPos.LMARGIN, new_y=YPos.NEXT)
    pdf.ln(5)
    pdf.p(f"Расшифровка подписи: {seller['full_name']}", align="L")
    return bytes(pdf.output())


def build_all(data: dict) -> dict[str, bytes]:
    """Комплект документов одной сделкой."""
    return {
        "contract": build_contract(data),
        "act": build_act(data),
        "receipt": build_receipt(data),
    }


def make_filename(kind: str, data: dict) -> str:
    car = data["car"]
    safe = lambda s: "".join(c for c in s if c.isalnum() or c in " -_").strip().replace(" ", "_")
    base = f"{safe(car['brand'])}_{safe(car['model'])}_{car['year']}_{safe(data['date'].replace('.', '-'))}"
    names = {
        "contract": "Dogovor_kupli_prodazhi",
        "act": "Akt_priema_peredachi",
        "receipt": "Raspiska",
    }
    return f"{names[kind]}_{base}.pdf"
