
import os

import uuid

import pathlib

import io

import logging

from aiogram import Bot

from aiogram.types import Message

from app.common.bot_instance import bot as global_bot

logger = logging.getLogger(__name__)

def _get_uploads_dir() -> pathlib.Path:
    """
    Determines the directory for photo uploads based on the environment.
    """
    # 1. Manual override
    env_dir = (os.getenv('UPLOADS_DIR') or '').strip()
    if env_dir:
        return pathlib.Path(env_dir)

    # 2. Docker / Unified environment (Nginx + Bot)
    # Common path for shared volume between Nginx and Bot
    paths_to_try = [
        pathlib.Path('/usr/share/nginx/html/images/uploads'),
        pathlib.Path('/app/uploads'),
        pathlib.Path('/app/MedelinSite/images/uploads'),
    ]
    
    for p in paths_to_try:
        if p.exists() or p.parent.exists():
            try:
                p.mkdir(parents=True, exist_ok=True)
                return p
            except:
                continue

    # 3. Local development (fallback)
    try:
        repo_root = pathlib.Path(__file__).resolve().parents[3]
        dev_path = repo_root / 'MedelinSite' / 'images' / 'uploads'
        dev_path.mkdir(parents=True, exist_ok=True)
        return dev_path
    except Exception:
        pass
        
    return pathlib.Path('uploads')

async def process_photo(message: Message, bot: Bot = None) -> str:
    """
    Processes a photo from a message (either PhotoSize or Document).
    Returns a URL-friendly path starting with /uploads/.
    """
    target_bot = bot or global_bot
    file_id = None
    original_ext = ".jpg"

    if message.photo:
        file_id = message.photo[-1].file_id
    elif message.document and message.document.mime_type and message.document.mime_type.startswith('image/'):
        file_id = message.document.file_id
        if message.document.file_name:
            original_ext = pathlib.Path(message.document.file_name).suffix.lower()

    if not file_id:
        val = (message.text or '').strip()
        return '' if val == '-' else val

    try:
        file_bytes_io = io.BytesIO()

        # Download file
        try:
            f = await target_bot.get_file(file_id)
            await target_bot.download_file(f.file_path, destination=file_bytes_io)
            if f.file_path:
                original_ext = pathlib.Path(f.file_path).suffix.lower()
        except Exception as e:
            logger.warning(f"Failed to get_file, trying direct download: {e}")
            await target_bot.download(file_id, destination=file_bytes_io)
        
        file_bytes = file_bytes_io.getvalue()
        if not file_bytes:
            return ''

        uploads_dir = _get_uploads_dir()
        stem = uuid.uuid4().hex[:10]

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
            
            img.save(str(filepath), 'WEBP', quality=85, method=6)
            logger.info(f"Saved processed photo: {filename}")
            return f'/uploads/{filename}'
        except Exception as e:
            logger.warning(f"Pillow conversion failed, saving raw: {e}")
            renderable_exts = ('.jpg', '.jpeg', '.png', '.webp', '.gif')
            ext = original_ext if original_ext in renderable_exts else '.jpg'
            
            filename = f'{stem}{ext}'
            filepath = uploads_dir / filename
            filepath.write_bytes(file_bytes)
            return f'/uploads/{filename}'

    except Exception as e:
        logger.error(f"Error processing photo: {e}")
        return ''
