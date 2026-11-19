"""Обработчики: меню, профиль, визард сделки, архив."""
from __future__ import annotations

import logging

from aiogram import Bot, F, Router
from aiogram.filters import Command, CommandStart, StateFilter
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message

from bot import crypto, quickedit, wizard
from bot.db import Counterparty, Deal, Profile, SessionLocal
from bot.keyboards import (BTN_ARCHIVE, BTN_CANCEL, BTN_NEW, BTN_PROFILE, BTN_PROFILE_EDIT,
                           BTN_SETTINGS, BTN_SKIP, confirm_kb, edit_fields_kb, edit_kb,
                           main_menu, profile_menu_kb, remove_kb, roles_kb, skip_kb)
from bot.services import build_and_send, make_deal_data, person_complete
from bot.states import QuickEdit
from bot.utils.money import date_to_text, rubles_to_words

log = logging.getLogger(__name__)
router = Router()

HELP = (
    "Я формирую комплект документов для сделки с автомобилем:\n"
    "• договор купли-продажи — 3 экземпляра\n"
    "• акт приёма-передачи\n"
    "• расписка в получении денег\n\n"
    "<b>Как начать:</b> заполните профиль один раз, затем нажимайте "
    "«🚗 Новая сделка» — дальше только данные второй стороны и авто.\n\n"
    "<i>Документы формируются по шаблону, проверенному в практике сделок. "
    "Ответственность за введённые данные несёт пользователь. "
    "Это не юридическая услуга.</i>"
)


# ------------------------------------------------------------------ старт
@router.message(CommandStart())
async def cmd_start(message: Message, state: FSMContext) -> None:
    await state.clear()
    with SessionLocal() as s:
        has_profile = s.query(Profile).filter_by(telegram_id=message.from_user.id).first() is not None

    text = f"Здравствуйте, {message.from_user.first_name}!\n\n{HELP}"
    if not has_profile:
        text += "\n\n👉 Начнём с профиля — нажмите «👤 Мой профиль»."
    await message.answer(text, reply_markup=main_menu())


@router.message(Command("help"))
async def cmd_help(message: Message) -> None:
    await message.answer(HELP, reply_markup=main_menu())


# ------------------------------------------------------------------ профиль
@router.message(F.text == BTN_PROFILE)
async def profile_menu(message: Message, state: FSMContext) -> None:
    await state.clear()
    with SessionLocal() as s:
        profile = s.query(Profile).filter_by(telegram_id=message.from_user.id).first()
        data = crypto.decrypt(profile.data_enc) if profile else None

    if not data:
        await message.answer(
            "Профиль пока не заполнен.\n\nЭто данные <b>вас</b> — они автоматически "
            "подставятся в каждый договор. Заполняем один раз.",
            reply_markup=remove_kb(),
        )
        await _start_profile(message, state)
        return

    lines = [
        "<b>Ваш профиль</b>",
        f"ФИО: {data['full_name']}",
        f"Дата рождения: {data['birth_date']}",
        f"Паспорт: {data['passport_series']} № {data['passport_number']}",
        f"Выдан: {data['passport_issued_by']}, {data['passport_issue_date']}",
        f"Код подразделения: {data['passport_dept_code']}",
        f"Адрес: {data['registration_address']}",
    ]
    if data.get("phone"):
        lines.append(f"Телефон: {data['phone']}")
    lines.append("\nЧтобы изменить данные — заполните профиль заново.")
    await message.answer("\n".join(lines), reply_markup=profile_menu_kb())


@router.message(F.text == BTN_PROFILE_EDIT)
async def profile_refill(message: Message, state: FSMContext) -> None:
    await _start_profile(message, state)


async def _start_profile(message: Message, state: FSMContext) -> None:
    with SessionLocal() as s:
        profile = s.query(Profile).filter_by(telegram_id=message.from_user.id).first()
        existing = crypto.decrypt(profile.data_enc) if profile else {}
    await state.update_data(_person=existing, _target="profile")
    await wizard.start(message, state, "person", intro="Заполняем профиль.")


# ------------------------------------------------------------------ новая сделка
@router.message(Command("new"))
@router.message(F.text == BTN_NEW)
async def new_deal(message: Message, state: FSMContext) -> None:
    await state.clear()
    with SessionLocal() as s:
        profile = s.query(Profile).filter_by(telegram_id=message.from_user.id).first()
        me = crypto.decrypt(profile.data_enc) if profile else None

    await state.update_data(_me=me)
    if me:
        await message.answer("Вы в этой сделке:", reply_markup=roles_kb())
    else:
        await message.answer(
            "Профиль не заполнен — это не помешает.\n\n"
            "Выберите свою сторону, и я спрошу ваши данные один раз, "
            "<b>ничего не сохраняя</b>. Для разовой сделки этого достаточно.",
            reply_markup=roles_kb(no_profile=True),
        )


@router.callback_query(F.data == "deal:noop")
async def noop(cb: CallbackQuery) -> None:
    await cb.answer("Просто выберите «Я покупатель» или «Я продавец» — "
                    "ваши данные спрошу в процессе.", show_alert=True)


@router.callback_query(F.data.startswith("deal:role:"))
async def choose_role(cb: CallbackQuery, state: FSMContext) -> None:
    role = cb.data.split(":")[-1]
    d = await state.get_data()
    me = d.get("_me")

    if me:
        await state.update_data(role=role, _cp={}, _first_person="cp")
        label = "покупатель" if role == "buyer" else "продавец"
        await cb.message.edit_text(f"Вы — {label}.\nТеперь данные второй стороны.")
        await wizard.start(cb.message, state, "person", intro="Данные второй стороны.")
    else:
        await state.update_data(role=role, _cp={}, _first_person="me")
        label = "покупатель" if role == "buyer" else "продавец"
        await cb.message.edit_text(
            f"Вы — {label}.\nСначала ваши данные в этой сделке. "
            "Они не сохранятся — используются только для этого договора."
        )
        await wizard.start(cb.message, state, "person", intro="Ваши данные в сделке.")
    await cb.answer()


# ------------------------------------------------------------------ визард: общий вход
@router.message(StateFilter(wizard.PersonForm, wizard.CarForm, wizard.TermsForm))
async def wizard_input(message: Message, state: FSMContext) -> None:
    result = await wizard.handle(message, state)

    if result == "cancelled":
        await message.answer("Отменено. Возврат в меню.", reply_markup=main_menu())
        return
    if not result:
        return
    if result.startswith("done:"):
        await _on_form_done(message, state, result.split(":")[1])


async def _on_form_done(message: Message, state: FSMContext, form: str) -> None:
    data = await state.get_data()
    edit_mode = data.get("_edit")

    if form == "person":
        person = data.get("_person", {})
        if not person_complete(person):
            await message.answer("Не все обязательные данные заполнены. Начнём заново.")
            await wizard.start(message, state, "person")
            return

        if data.get("_target") == "profile":
            _save_profile(message.from_user.id, person)
            await message.answer(
                "✅ Профиль сохранён. Теперь данные будут подставляться автоматически.\n\n"
                "Нажмите «🚗 Новая сделка», чтобы оформить первую сделку.",
                reply_markup=main_menu(),
            )
            await state.clear()
            return

        first = data.get("_first_person", "cp")
        if first == "me":
            await state.update_data(_me=person, _person={}, _first_person="cp")
            await message.answer("✅ Ваши данные приняты. Теперь вторая сторона.")
            await wizard.start(message, state, "person", intro="Данные второй стороны.")
            return

        await state.update_data(_cp=person, _first_person=None)
        if edit_mode == "cp":
            await state.update_data(_edit=None)
            await _show_review(message, state)
            return

        await wizard.start(message, state, "car", intro="Теперь автомобиль.")
        return

    if form == "car":
        await state.update_data(_car=data.get("_car", {}))
        if edit_mode == "car":
            await state.update_data(_edit=None)
            await _show_review(message, state)
            return
        await wizard.start(message, state, "terms", intro="Условия сделки.")
        return

    if form == "terms":
        await state.update_data(_edit=None)
        await _show_review(message, state)
        return


def _save_profile(telegram_id: int, person: dict) -> None:
    with SessionLocal() as s:
        profile = s.query(Profile).filter_by(telegram_id=telegram_id).first()
        enc = crypto.encrypt(person)
        if profile:
            profile.data_enc = enc
        else:
            s.add(Profile(telegram_id=telegram_id, data_enc=enc))
        s.commit()


# ------------------------------------------------------------------ проверка и генерация
def _review_text(data: dict) -> str:
    d = data
    me, other = d["_me"], d["_cp"]
    seller, buyer = (me, other) if d["role"] == "seller" else (other, me)
    car, terms = d["_car"], d["_terms"]
    price = rubles_to_words(terms["price"])

    def person_block(title: str, p: dict) -> str:
        return (f"<b>{title}</b>\n{p['full_name']}\n"
                f"паспорт {p['passport_series']} № {p['passport_number']}, "
                f"выдан {p['passport_issued_by']} {p['passport_issue_date']}\n"
                f"{p['registration_address']}")

    return "\n\n".join([
        "🔍 <b>Проверьте данные перед формированием</b>",
        person_block("Продавец", seller),
        person_block("Покупатель", buyer),
        "<b>Автомобиль</b>\n"
        f"{car['brand']} {car['model']}, {car['year']} г.\n"
        f"VIN: <code>{car['vin']}</code>\n"
        f"Кузов: {car.get('body_no') or 'отсутствует'}\n"
        f"Цвет: {car['color']}\n"
        f"ПТС: {car['pts_series_no']} от {car['pts_date']}\n"
        f"СТС: {car['sts_series_no']} от {car['sts_date']}",
        f"<b>Условия</b>\nЦена: {terms['price'] / 100:,.0f} ₽ ({price})\n"
        f"Город: {terms['city']}\nДата: {terms.get('deal_date') or 'сегодня'}",
        "<b>Чек-лист</b>\n"
        "• VIN одинаков в договоре, ПТС и СТС?\n"
        "• Сумма прописью верна?\n"
        "• Обе стороны распишутся на всех экземплярах?",
    ])


async def _show_review(message: Message, state: FSMContext) -> None:
    data = await state.get_data()
    if not data.get("_terms", {}).get("deal_date"):
        from datetime import datetime
        terms = data["_terms"]
        terms["deal_date"] = datetime.now().strftime("%d.%m.%Y")
        await state.update_data(_terms=terms)
    await message.answer(_review_text(await state.get_data()), reply_markup=confirm_kb())


@router.callback_query(F.data == "deal:review")
async def back_to_review(cb: CallbackQuery, state: FSMContext) -> None:
    await _show_review(cb.message, state)
    await cb.answer()


@router.callback_query(F.data == "deal:build")
async def do_build(cb: CallbackQuery, state: FSMContext, bot: Bot) -> None:
    await cb.message.edit_reply_markup(reply_markup=None)
    await cb.message.answer(
        "⏳ Формирую документы...\n"
        "<i>Отправка может занять до минуты при медленном интернете — не закрывайте окно.</i>"
    )
    try:
        deal_id, failed = await build_and_send(bot, cb.message.chat.id, state, cb.from_user.id)
    except Exception:
        log.exception("Ошибка генерации документов")
        await cb.message.answer(
            "Не удалось сформировать документы.\n\n"
            "Проверьте интернет и нажмите «Сформировать» ещё раз — данные сделки сохранены.",
            reply_markup=main_menu(),
        )
        await cb.answer()
        return

    titles = {"contract": "договор", "act": "акт", "receipt": "расписку"}
    text = (
        f"✅ Готово! Сделка №{deal_id} сохранена в архиве.\n\n"
        "Распечатайте документы и подпишите каждый экземпляр вручную. "
        "Договор — 3 экземпляра: продавцу, покупателю и для ГИБДД."
    )
    if failed:
        missing = ", ".join(titles.get(k, k) for k in failed)
        text += (f"\n\n⚠️ Не удалось отправить: {missing}. "
                 "Сделка сохранена — документы можно перекачать из «📁 Мои договоры».")
    await cb.message.answer(text, reply_markup=main_menu())
    await state.clear()
    await cb.answer()


@router.callback_query(F.data == "deal:edit")
async def edit_menu(cb: CallbackQuery) -> None:
    await cb.message.edit_text(
        "Что изменить?\n\n"
        "<i>Можно поправить одно конкретное поле или заполнить блок целиком.</i>",
        reply_markup=edit_fields_kb(),
    )
    await cb.answer()


@router.callback_query(F.data == "deal:block")
async def edit_block_menu(cb: CallbackQuery) -> None:
    """Старый режим: перезаполнить весь блок (сторона / авто / условия)."""
    await cb.message.edit_text(
        "Какой блок заполнить заново?",
        reply_markup=edit_kb(),
    )
    await cb.answer()


@router.callback_query(F.data.startswith("fld:"))
async def quick_edit_start(cb: CallbackQuery, state: FSMContext) -> None:
    field_key = cb.data[4:]
    if field_key not in quickedit.FIELDS:
        await cb.answer("Неизвестное поле", show_alert=True)
        return

    data = await state.get_data()
    if not data.get("_car") or not data.get("_terms"):
        await cb.answer("Сначала заполните сделку", show_alert=True)
        return

    await cb.message.edit_reply_markup(reply_markup=None)
    await state.set_state(QuickEdit.waiting)
    await state.update_data(_qfield=field_key)
    await cb.message.answer(quickedit.prompt_text(data, field_key),
                            reply_markup=skip_kb(False))
    await cb.answer()


@router.message(QuickEdit.waiting)
async def quick_edit_input(message: Message, state: FSMContext) -> None:
    text = (message.text or "").strip()
    if text == BTN_CANCEL:
        await state.set_state(None)
        await state.update_data(_qfield=None)
        await message.answer("Отменено.", reply_markup=main_menu())
        return

    data = await state.get_data()
    field_key = data.get("_qfield")

    if text in (".", BTN_SKIP):
        # оставить как есть
        await state.set_state(None)
        await state.update_data(_qfield=None)
        await _show_review(message, state)
        return

    try:
        updated = quickedit.apply(data, field_key, text)
    except ValueError as exc:
        await message.answer(f"⚠️ {exc}\n\nПопробуйте ещё раз.",
                             reply_markup=skip_kb(False))
        return

    await state.set_data(updated)
    await state.set_state(None)
    await state.update_data(_qfield=None)
    await message.answer("✅ Изменено.")
    await _show_review(message, state)


@router.callback_query(F.data == "deal:edit:cp")
async def edit_counterparty(cb: CallbackQuery, state: FSMContext) -> None:
    await cb.message.edit_reply_markup(reply_markup=None)
    data = await state.get_data()
    await state.update_data(_person=data.get("_cp", {}), _edit="cp")
    await wizard.start(cb.message, state, "person", intro="Правим вторую сторону.")
    await cb.answer()


@router.callback_query(F.data == "deal:edit:car")
async def edit_car(cb: CallbackQuery, state: FSMContext) -> None:
    await cb.message.edit_reply_markup(reply_markup=None)
    data = await state.get_data()
    await state.update_data(_car=data.get("_car", {}), _edit="car")
    await wizard.start(cb.message, state, "car", intro="Правим автомобиль.")
    await cb.answer()


@router.callback_query(F.data == "deal:edit:terms")
async def edit_terms(cb: CallbackQuery, state: FSMContext) -> None:
    await cb.message.edit_reply_markup(reply_markup=None)
    data = await state.get_data()
    await state.update_data(_terms=data.get("_terms", {}), _edit="terms")
    await wizard.start(cb.message, state, "terms", intro="Правим условия.")
    await cb.answer()


# ------------------------------------------------------------------ архив
@router.message(Command("archive"))
@router.message(F.text == BTN_ARCHIVE)
async def archive(message: Message, state: FSMContext, bot: Bot) -> None:
    await state.clear()
    with SessionLocal() as s:
        deals = (s.query(Deal).filter_by(owner_telegram_id=message.from_user.id)
                 .order_by(Deal.id.desc()).limit(10).all())
        rows = [(d.id, d.deal_date, d.car_data, d.price, d.pdf_file_id) for d in deals]

    if not rows:
        await message.answer("Архив пуст. Оформите первую сделку — «🚗 Новая сделка».",
                             reply_markup=main_menu())
        return

    await message.answer("📁 <b>Последние сделки</b>", reply_markup=main_menu())
    for deal_id, deal_date, car, price, file_id in rows:
        caption = (f"№{deal_id} · {deal_date}\n"
                   f"{car['brand']} {car['model']}, {car['year']}\n"
                   f"VIN: <code>{car['vin']}</code>\n"
                   f"Цена: {price:,.0f} ₽")
        if file_id:
            await bot.send_document(message.chat.id, file_id, caption=caption)
        else:
            await message.answer(caption)


# ------------------------------------------------------------------ настройки
@router.message(F.text == BTN_SETTINGS)
async def settings(message: Message) -> None:
    await message.answer(
        "<b>Настройки</b>\n\n"
        "Данные хранятся в зашифрованном виде. Сканы документов не сохраняются.\n\n"
        "Чтобы удалить профиль и все данные — отправьте /delete_me",
        reply_markup=main_menu(),
    )


@router.message(Command("delete_me"))
async def delete_me(message: Message, state: FSMContext) -> None:
    tid = message.from_user.id
    with SessionLocal() as s:
        s.query(Profile).filter_by(telegram_id=tid).delete()
        s.query(Deal).filter_by(owner_telegram_id=tid).delete()
        s.query(Counterparty).filter_by(owner_telegram_id=tid).delete()
        s.commit()
    await state.clear()
    await message.answer("🗑 Все ваши данные удалены: профиль, сделки, контрагенты.",
                         reply_markup=main_menu())


# ------------------------------------------------------------------ fallback
@router.message()
async def fallback(message: Message) -> None:
    await message.answer("Не понял. Воспользуйтесь меню ниже или /help.",
                         reply_markup=main_menu())
