"""Клавиатуры. Reply-кнопки — для постоянного меню, inline — для выборов."""
from aiogram.types import (InlineKeyboardButton, InlineKeyboardMarkup, KeyboardButton,
                           ReplyKeyboardMarkup, ReplyKeyboardRemove)

BTN_NEW = "🚗 Новая сделка"
BTN_ARCHIVE = "📁 Мои договоры"
BTN_PROFILE = "👤 Мой профиль"
BTN_SETTINGS = "⚙️ Настройки"

BTN_SKIP = "⏭ Пропустить"
BTN_BACK = "◀️ Назад"
BTN_CANCEL = "✖️ Отмена"
BTN_PROFILE_EDIT = "✏️ Изменить профиль"
BTN_ONETIME = "✍️ Заполнить обе стороны вручную"
BTN_USE_PROFILE = "👤 Использовать мой профиль"


def profile_menu_kb() -> ReplyKeyboardMarkup:
    return ReplyKeyboardMarkup(
        keyboard=[[KeyboardButton(text=BTN_PROFILE_EDIT)], [KeyboardButton(text=BTN_NEW)]],
        resize_keyboard=True,
    )


def main_menu() -> ReplyKeyboardMarkup:
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text=BTN_NEW), KeyboardButton(text=BTN_ARCHIVE)],
            [KeyboardButton(text=BTN_PROFILE), KeyboardButton(text=BTN_SETTINGS)],
        ],
        resize_keyboard=True,
    )


def skip_kb(allow_skip: bool) -> ReplyKeyboardMarkup:
    row = [KeyboardButton(text=BTN_BACK)]
    if allow_skip:
        row.append(KeyboardButton(text=BTN_SKIP))
    return ReplyKeyboardMarkup(keyboard=[row, [KeyboardButton(text=BTN_CANCEL)]],
                               resize_keyboard=True)


def gender_kb() -> ReplyKeyboardMarkup:
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="Мужской"), KeyboardButton(text="Женский")],
            [KeyboardButton(text=BTN_BACK), KeyboardButton(text=BTN_CANCEL)],
        ],
        resize_keyboard=True,
    )


def remove_kb() -> ReplyKeyboardRemove:
    return ReplyKeyboardRemove()


def roles_kb() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[[
        InlineKeyboardButton(text="Я покупатель", callback_data="deal:role:buyer"),
        InlineKeyboardButton(text="Я продавец", callback_data="deal:role:seller"),
    ]])


def roles_kb(no_profile: bool = False) -> InlineKeyboardMarkup:
    rows = [
        [InlineKeyboardButton(text="Я покупатель", callback_data="deal:role:buyer")],
        [InlineKeyboardButton(text="Я продавец", callback_data="deal:role:seller")],
    ]
    if no_profile:
        rows.append([InlineKeyboardButton(
            text="ℹ️ Профиля нет — введём ваши данные один раз",
            callback_data="deal:noop")])
    return InlineKeyboardMarkup(inline_keyboard=rows)


def confirm_kb() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="✅ Сформировать документы", callback_data="deal:build")],
        [InlineKeyboardButton(text="✏️ Изменить данные", callback_data="deal:edit")],
    ])


def edit_fields_kb() -> InlineKeyboardMarkup:
    """Список конкретных полей для точечного редактирования."""
    rows = [
        [InlineKeyboardButton(text="Продавец: ФИО", callback_data="fld:seller.full_name"),
         InlineKeyboardButton(text="Продавец: паспорт", callback_data="fld:seller.passport")],
        [InlineKeyboardButton(text="Покупатель: ФИО", callback_data="fld:buyer.full_name"),
         InlineKeyboardButton(text="Покупатель: паспорт", callback_data="fld:buyer.passport")],
        [InlineKeyboardButton(text="Авто: марка/модель", callback_data="fld:car.brand_model"),
         InlineKeyboardButton(text="Авто: VIN", callback_data="fld:car.vin")],
        [InlineKeyboardButton(text="Авто: год", callback_data="fld:car.year"),
         InlineKeyboardButton(text="Авто: цвет", callback_data="fld:car.color")],
        [InlineKeyboardButton(text="Авто: ПТС", callback_data="fld:car.pts"),
         InlineKeyboardButton(text="Авто: СТС", callback_data="fld:car.sts")],
        [InlineKeyboardButton(text="Цена", callback_data="fld:terms.price"),
         InlineKeyboardButton(text="Город / дата", callback_data="fld:terms.city_date")],
        [InlineKeyboardButton(text="📝 Заполнить блок целиком", callback_data="deal:block")],
        [InlineKeyboardButton(text="↩️ К проверке", callback_data="deal:review")],
    ]
    return InlineKeyboardMarkup(inline_keyboard=rows)


def edit_kb() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="Вторую сторону", callback_data="deal:edit:cp")],
        [InlineKeyboardButton(text="Автомобиль", callback_data="deal:edit:car")],
        [InlineKeyboardButton(text="Цену / город / дату", callback_data="deal:edit:terms")],
        [InlineKeyboardButton(text="↩️ К проверке", callback_data="deal:review")],
    ])


def skip_inline() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="Пропустить", callback_data="wiz:skip")],
    ])
