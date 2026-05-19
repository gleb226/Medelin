
import os

import uuid

import pathlib

from aiogram import Bot

from aiogram.types import Message

_site_dir = pathlib.Path(__file__).resolve().parent.parent.parent.parent / 'MedelinSite' / 'images' / 'uploads'

async def process_photo(message: Message, bot: Bot) -> str:

    file_id = None

    if message.photo:

        file_id = message.photo[-1].file_id

    elif message.document and message.document.mime_type and message.document.mime_type.startswith('image/'):

        file_id = message.document.file_id

    if file_id:

        try:

            from PIL import Image

            import io

            file_bytes = io.BytesIO()

            await bot.download(file_id, destination=file_bytes)

            file_bytes.seek(0)

            img = Image.open(file_bytes)

            img = img.convert('RGB')

            _site_dir.mkdir(parents=True, exist_ok=True)

            filename = f'{uuid.uuid4().hex[:10]}.webp'

            filepath = _site_dir / filename

            img.save(str(filepath), 'WEBP', quality=85, method=6)

            return f'/uploads/{filename}'

        except ImportError:

            return file_id

        except Exception as e:

            print('photo_utils error:', e)

            return file_id

    else:

        val = (message.text or '').strip()

        if val == '-':

            val = ''

        return val
