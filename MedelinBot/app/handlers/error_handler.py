
import traceback
import html
from datetime import datetime

from aiogram import Router, Bot

from aiogram.types import ErrorEvent

from aiogram.exceptions import TelegramBadRequest

from app.common.config import DEVELOPER_IDS

from app.databases.mongo_client import get_db

error_router = Router()

async def log_error_to_db(user_id, username, command, error_message, traceback_text):

    try:

        db = await get_db()

        await db.errors.insert_one({'user_id': int(user_id) if user_id is not None else None, 'username': username, 'command': command, 'error_message': error_message, 'traceback_text': traceback_text, 'created_at': datetime.utcnow()})

    except Exception as e:

        print(f'CRITICAL: Failed to log error to DB: {e}')

@error_router.error()

async def global_error_handler(event: ErrorEvent, bot: Bot):

    error = event.exception

    if isinstance(error, TelegramBadRequest) and 'message is not modified' in str(error).lower():

        return True

    etype = type(error).__name__

    emsg = str(error)

    tb = ''.join(traceback.format_exception(type(error), error, error.__traceback__))

    user_id = None

    username = None

    command = 'Unknown'

    if event.update.message:

        user_id = event.update.message.from_user.id

        username = event.update.message.from_user.username

        command = event.update.message.text or 'NonTextMessage'

    elif event.update.callback_query:

        user_id = event.update.callback_query.from_user.id

        username = event.update.callback_query.from_user.username

        command = event.update.callback_query.data or 'EmptyCallbackData'

    await log_error_to_db(user_id, username, command, f'{etype}: {emsg}', tb)

    error_text = '⚠️ Вибачте, виникла помилка. Ми вже працюємо над її виправленням!'

    try:

        if event.update.message:

            await event.update.message.answer(error_text)

        elif event.update.callback_query:

            await event.update.callback_query.message.answer(error_text)

    except:

        pass

    from app.utils.admin_notifications import send_developer_error

    uname = html.escape(f"@{username}") if username else "N/A"

    e_command = html.escape(str(command))
    e_type = html.escape(str(etype))
    e_msg = html.escape(str(emsg))
    e_tb = html.escape(tb[-500:])

    alert_text = f"🚨 <b>ERROR REPORT</b>\nUser: <code>{user_id}</code> ({uname})\nCommand: <code>{e_command}</code>\nType: <code>{e_type}</code>\nMsg: <code>{e_msg}</code>\n\n<pre>{e_tb}</pre>"

    await send_developer_error(alert_text)
