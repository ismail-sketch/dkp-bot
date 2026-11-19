"""Демо-данные и генерация образцов в data/preview/ (проверка без Telegram)."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from bot.docs.pdf_generator import build_all, make_filename  # noqa: E402

SAMPLE = {
    "city": "г. Краснодар",
    "date": "18.11.2026",
    "price_kopecks": 1_250_000_00,
    "seller": {
        "full_name": "Кузнецов Сергей Петрович",
        "gender": "м",
        "birth_date": "12.04.1988",
        "passport_series": "0307",
        "passport_number": "123456",
        "passport_issued_by": "ОВД Центрального округа г. Краснодара",
        "passport_issue_date": "21.05.2008",
        "passport_dept_code": "232-001",
        "registration_address": "г. Краснодар, ул. Красная, д. 15, кв. 42",
    },
    "buyer": {
        "full_name": "Смирнова Анна Викторовна",
        "gender": "ж",
        "birth_date": "03.09.1992",
        "passport_series": "0312",
        "passport_number": "654321",
        "passport_issued_by": "УФМС России по Краснодарскому краю",
        "passport_issue_date": "14.10.2012",
        "passport_dept_code": "232-002",
        "registration_address": "г. Краснодар, ул. Северная, д. 220, кв. 7",
    },
    "car": {
        "brand": "Toyota",
        "model": "Camry",
        "year": 2014,
        "vin": "JTNBK46K70J123456",
        "body_no": "JTNBK46K70J123456",
        "chassis_no": "",
        "engine_no": "2AR1234567",
        "color": "чёрный",
        "mileage": 187000,
        "power": 181,
        "volume": 2494,
        "gosnomer": "О456ММ99",
        "pts_series_no": "77 УН 123456",
        "pts_date": "15.06.2014",
        "pts_issued_by": "ООО «Тойота Мотор»",
        "sts_series_no": "99 12 345678",
        "sts_date": "20.07.2014",
    },
}


def main() -> None:
    out_dir = Path(__file__).resolve().parent.parent / "data" / "preview"
    out_dir.mkdir(parents=True, exist_ok=True)
    for kind, content in build_all(SAMPLE).items():
        path = out_dir / make_filename(kind, SAMPLE)
        path.write_bytes(content)
        print(f"{path.name}: {len(content) / 1024:.0f} КБ")


if __name__ == "__main__":
    main()
