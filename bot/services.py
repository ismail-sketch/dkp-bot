"""Сборка данных сделки из FSM, сохранение в архив и отправка комплекта."""
from __future__ import annotations

import asyncio
import logging
from datetime import datetime

from aiogram import Bot
from aiogram.exceptions import TelegramNetworkError, TelegramRetryAfter
from aiogram.fsm.context import FSMContext
from aiogram.types import BufferedInputFile

from bot import crypto
from bot.db import Deal, SessionLocal
from bot.docs.pdf_generator import build_all, make_filename

log = logging.getLogger(__name__)

TITLES = {
    "contract": "📄 Договор купли-продажи — 3 экземпляра",
    "act": "📋 Акт приёма-передачи",
    "receipt": "🧾 Расписка в получении денежных средств",
}

# Медленный интернет: даём больше времени на отправку файла и повторяем попытки
UPLOAD_TIMEOUT = 300      # секунд на один файл
MAX_ATTEMPTS = 4


def person_complete(person: dict) -> bool:
    required = ("full_name", "gender", "birth_date", "passport_series", "passport_number",
                "passport_issued_by", "passport_issue_date", "passport_dept_code",
                "registration_address")
    return all(person.get(k) for k in required)


def make_deal_data(d: dict) -> dict:
    """Из «сырых» данных FSM собрать словарь для генератора документов."""
    me, other = d["_me"], d["_cp"]
    seller, buyer = (me, other) if d["role"] == "seller" else (other, me)
    terms = d["_terms"]
    return {
        "role": d["role"],
        "city": terms["city"],
        "date": terms.get("deal_date") or datetime.now().strftime("%d.%m.%Y"),
        "price_kopecks": terms["price"],
        "seller": seller,
        "buyer": buyer,
        "car": d["_car"],
    }


async def _send_with_retry(bot: Bot, chat_id: int, document, caption: str):
    """Отправка файла с повторами. Медленная сеть — не повод терять сделку."""
    last_error: Exception | None = None

    for attempt in range(1, MAX_ATTEMPTS + 1):
        try:
            return await bot.send_document(
                chat_id=chat_id,
                document=document,
                caption=caption,
                request_timeout=UPLOAD_TIMEOUT,
            )
        except TelegramRetryAfter as exc:
            wait = exc.retry_after + 1
            log.warning("Telegram просит подождать %s с (попытка %s)", wait, attempt)
            await asyncio.sleep(wait)
            last_error = exc
        except TelegramNetworkError as exc:
            last_error = exc
            if attempt < MAX_ATTEMPTS:
                wait = 2 * attempt
                log.warning("Сеть подвела (попытка %s/%s): %s. Повтор через %s с",
                            attempt, MAX_ATTEMPTS, exc, wait)
                await asyncio.sleep(wait)
            else:
                log.error("Не удалось отправить файл после %s попыток", MAX_ATTEMPTS)

    if last_error:
        raise last_error
    raise RuntimeError("Отправка не удалась")


async def build_and_send(bot: Bot, chat_id: int, state: FSMContext,
                         telegram_id: int) -> tuple[int, list[str]]:
    """Сгенерировать PDF, отправить в чат, сохранить сделку.

    Возвращает (id сделки, список типов, которые не удалось отправить).
    """
    d = await state.get_data()
    data = make_deal_data(d)
    docs = build_all(data)

    file_ids: dict[str, str] = {}
    failed: list[str] = []

    for kind, content in docs.items():
        document = BufferedInputFile(content, filename=make_filename(kind, data))
        try:
            msg = await _send_with_retry(bot, chat_id, document, TITLES[kind])
            file_ids[kind] = msg.document.file_id
        except Exception:
            log.exception("Не удалось отправить документ %s", kind)
            failed.append(kind)

    if not file_ids:
        # ни один файл не ушёл — не сохраняем пустую сделку
        raise RuntimeError("Не удалось отправить ни одного документа")

    is_buyer = d["role"] == "buyer"
    with SessionLocal() as s:
        deal = Deal(
            owner_telegram_id=telegram_id,
            role=d["role"],
            my_data_enc=crypto.encrypt(data["buyer" if is_buyer else "seller"]),
            counterparty_enc=crypto.encrypt(data["seller" if is_buyer else "buyer"]),
            car_data=data["car"],
            price=data["price_kopecks"] // 100,
            price_kopecks=data["price_kopecks"] % 100,
            city=data["city"],
            deal_date=data["date"],
            pdf_file_id=file_ids.get("contract"),
        )
        s.add(deal)
        s.commit()
        return deal.id, failed
