"""Состояния диалогов (FSM). Порядок полей задаётся в wizard.py."""
from aiogram.fsm.state import State, StatesGroup


class PersonForm(StatesGroup):
    """Данные человека: профиль пользователя или контрагент — одинаковый набор полей."""
    full_name = State()
    gender = State()
    birth_date = State()
    passport_series = State()
    passport_number = State()
    passport_issued_by = State()
    passport_issue_date = State()
    passport_dept_code = State()
    registration_address = State()
    phone = State()


class CarForm(StatesGroup):
    brand = State()
    model = State()
    year = State()
    vin = State()
    body_no = State()
    chassis_no = State()
    engine_no = State()
    color = State()
    ts_type = State()
    mileage = State()
    power = State()
    volume = State()
    gosnomer = State()
    pts_series_no = State()
    pts_date = State()
    pts_issued_by = State()
    sts_series_no = State()
    sts_date = State()


class TermsForm(StatesGroup):
    price = State()
    city = State()
    deal_date = State()


class QuickEdit(StatesGroup):
    """Точечное редактирование одного поля: спрашиваем значение и сразу возвращаемся."""
    waiting = State()
