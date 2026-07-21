
from aiogram.types import Message, InlineKeyboardMarkup

from aiogram.exceptions import TelegramBadRequest

import logging

async def safe_edit_message(message: Message, text: str, reply_markup: InlineKeyboardMarkup=None, parse_mode: str='HTML', **kwargs):
    try:
        if message.photo:

            try:
                await message.delete()
            except:
                pass
            return await message.answer(text, reply_markup=reply_markup, parse_mode=parse_mode, **kwargs)
        else:
            return await message.edit_text(text=text, reply_markup=reply_markup, parse_mode=parse_mode, **kwargs)
    except TelegramBadRequest as e:

        if 'message is not modified' in str(e).lower():

            return

        if 'message to edit not found' in str(e).lower():

            return

        raise

async def fade_out_message(message: Message, final_text: str=None):

    if not message.text:

        return

    original = message.text

    steps = [original]

    for i in range(1, 6):

        cutoff = int(len(original) * (1 - i / 5))

        steps.append(original[:cutoff] + '.' * (len(original) - cutoff))

    for step in steps[1:]:

        try:

            await message.edit_text(step, parse_mode='HTML')

            await asyncio.sleep(0.1)

        except:

            break

    if final_text:

        try:

            await message.edit_text(final_text, parse_mode='HTML')

        except:

            pass

    else:

        try:

            await message.delete()

        except:

            pass

import asyncio
