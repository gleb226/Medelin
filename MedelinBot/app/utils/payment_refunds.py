
from __future__ import annotations

import logging

from aiogram import Bot

from aiogram.exceptions import TelegramBadRequest

async def refund_telegram_payment(bot: Bot, user_id: int, telegram_payment_charge_id: str, provider_payment_charge_id: str | None=None) -> tuple[bool, str | None]:
    if not telegram_payment_charge_id:
        return (False, 'missing telegram_payment_charge_id')
    try:
        await bot.refund_star_payment(user_id=user_id, telegram_payment_charge_id=telegram_payment_charge_id)
        return (True, None)
    except TelegramBadRequest as e:
        logging.warning(f'Manual refund required for charge_id: {telegram_payment_charge_id}. Error: {e}')
        return (False, f'Automatic refund not supported for fiat. Please refund via provider dashboard. ({e})')
    except Exception as e:
        return (False, str(e))
