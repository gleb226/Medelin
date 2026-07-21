
import os

import uuid

import pathlib

import io

import logging

from aiogram import Bot

from aiogram.types import Message

from app.common.bot_instance import bot as global_bot

logger = logging.getLogger(__name__)

from app.utils.paths import get_uploads_dir

async def process_photo(message: Message, bot: Bot = None) -> str | None:
    """
    Processes a photo from a message (either PhotoSize or Document).
    Returns a URL-friendly path starting with /uploads/.
    Returns None if the user explicitly sent '-' to skip/remove.
    """
    target_bot = bot or global_bot
    file_id = None
    original_ext = ".jpg"

    if message.photo:
        file_id = message.photo[-1].file_id
    elif message.document and (
        (message.document.mime_type or '').startswith('image/')
        or pathlib.Path(message.document.file_name or '').suffix.lower() in ('.jpg', '.jpeg', '.png', '.webp', '.gif', '.heic', '.heif')
    ):
        file_id = message.document.file_id
        if message.document.file_name:
            original_ext = pathlib.Path(message.document.file_name).suffix.lower()

    if not file_id:
        val = (message.text or '').strip()
        if val == '-':
            return None
        return val

    try:
        file_bytes_io = io.BytesIO()

        # Download file
        f = await target_bot.get_file(file_id)
        await target_bot.download_file(f.file_path, destination=file_bytes_io)
        file_bytes_io.seek(0)
        
        file_bytes = file_bytes_io.getvalue()
        if not file_bytes:
            return ''

        uploads_dir = get_uploads_dir()
        stem = uuid.uuid4().hex[:10]
        
        logger.info(f"Processing photo. Target directory: {uploads_dir}")

        # Try to convert to WEBP for efficiency
        try:
            from PIL import Image
            img = Image.open(io.BytesIO(file_bytes))

            # Handle orientation if present
            try:
                from PIL import ImageOps
                img = ImageOps.exif_transpose(img)
            except: pass

            if img.mode in ('RGBA', 'LA') or (img.mode == 'P' and 'transparency' in img.info):
                img = img.convert('RGBA')
            else:
                img = img.convert('RGB')

            filename = f'{stem}.webp'
            filepath = uploads_dir / filename
            
            img.save(str(filepath), 'WEBP', quality=85, method=4)
            logger.info(f"Saved processed photo: {filepath}")
            return f'/uploads/{filename}'
        except Exception as e:
            logger.warning(f"Pillow conversion failed, saving raw: {e}")
            renderable_exts = ('.jpg', '.jpeg', '.png', '.webp', '.gif')
            ext = original_ext if original_ext in renderable_exts else '.jpg'
            
            filename = f'{stem}{ext}'
            filepath = uploads_dir / filename
            filepath.write_bytes(file_bytes)
            logger.info(f"Saved raw photo: {filepath}")
            return f'/uploads/{filename}'

    except Exception as e:
        logger.error(f"Error processing photo: {e}")
        return ''
