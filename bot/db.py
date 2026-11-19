"""Модели БД. SQLAlchemy: локально SQLite, на VPS PostgreSQL — без правок кода.

Паспортные данные (ФИО, серия/номер, кем выдан, адрес) хранятся единым
зашифрованным JSON-блоком в колонке *_enc. Открытым текстом в БД лежит
только то, что не является персональными данными (VIN, цена, даты).
"""
from datetime import datetime

from sqlalchemy import JSON, DateTime, Integer, String, Text, create_engine
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, sessionmaker

from config import DATABASE_URL

_connect_args = {"check_same_thread": False} if DATABASE_URL.startswith("sqlite") else {}
engine = create_engine(DATABASE_URL, echo=False, future=True, connect_args=_connect_args)
SessionLocal = sessionmaker(bind=engine, expire_on_commit=False)


class Base(DeclarativeBase):
    pass


def now() -> datetime:
    return datetime.now()


class Profile(Base):
    """Профиль пользователя — данные «себя», подставляются в договор автоматически."""
    __tablename__ = "profiles"

    id: Mapped[int] = mapped_column(primary_key=True)
    telegram_id: Mapped[int] = mapped_column(Integer, unique=True, index=True)
    data_enc: Mapped[str] = mapped_column(Text)  # JSON: ФИО, паспорт, адрес, телефон
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=now, onupdate=now)


class Counterparty(Base):
    """Сохранённый контрагент — перекупы часто работают с одними и теми же людьми."""
    __tablename__ = "counterparties"

    id: Mapped[int] = mapped_column(primary_key=True)
    owner_telegram_id: Mapped[int] = mapped_column(Integer, index=True)
    full_name: Mapped[str] = mapped_column(String(200))  # для списка выбора, без паспорта
    data_enc: Mapped[str] = mapped_column(Text)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=now, onupdate=now)


class Deal(Base):
    """Сделка: снимок данных обеих сторон + авто + условия + file_id документа."""
    __tablename__ = "deals"

    id: Mapped[int] = mapped_column(primary_key=True)
    owner_telegram_id: Mapped[int] = mapped_column(Integer, index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=now)

    role: Mapped[str] = mapped_column(String(10))      # buyer | seller
    my_data_enc: Mapped[str] = mapped_column(Text)     # снимок «моей» стороны
    counterparty_enc: Mapped[str] = mapped_column(Text)

    car_data: Mapped[dict] = mapped_column(JSON)       # VIN, ПТС, СТС и т.д.
    price: Mapped[int] = mapped_column(Integer)        # рубли
    price_kopecks: Mapped[int] = mapped_column(Integer, default=0)
    city: Mapped[str] = mapped_column(String(100))
    deal_date: Mapped[str] = mapped_column(String(10))  # ДД.ММ.ГГГГ

    # Архив без файлового хранилища: Telegram отдаёт по file_id тот же документ
    pdf_file_id: Mapped[str | None] = mapped_column(String(200), nullable=True)
    docx_file_id: Mapped[str | None] = mapped_column(String(200), nullable=True)


def init_db() -> None:
    Base.metadata.create_all(engine)
