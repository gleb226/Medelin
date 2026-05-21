
import os

import uuid

import pathlib

from aiogram import Bot

from aiogram.types import Message

def _get_uploads_dir() -> pathlib.Path:
    env_dir = (os.getenv('UPLOADS_DIR') or '').strip()
    if env_dir:
        return pathlib.Path(env_dir)

    docker_mount = pathlib.Path('/app/uploads')
    if docker_mount.exists():
        return docker_mount

    # Repo layout (dev): <repo>/MedelinBot/app/utils/photo_utils.py -> parents[3] == <repo>
    repo_root = pathlib.Path(__file__).resolve().parents[3]
    return repo_root / 'MedelinSite' / 'images' / 'uploads'

async def process_photo(message: Message, bot: Bot) -> str:

    file_id = None

    if message.photo:

        file_id = message.photo[-1].file_id

    elif message.document and message.document.mime_type and message.document.mime_type.startswith('image/'):

        file_id = message.document.file_id

    if file_id:

        try:
            import io
            import re

            file_bytes = io.BytesIO()

            # aiogram v3: safest path is get_file() -> download_file()
            try:
                f = await bot.get_file(file_id)
                await bot.download_file(f.file_path, destination=file_bytes)
                file_path = f.file_path or ''
            except Exception:
                await bot.download(file_id, destination=file_bytes)
                file_path = ''

            file_bytes.seek(0)

            uploads_dir = _get_uploads_dir()
            uploads_dir.mkdir(parents=True, exist_ok=True)

            stem = uuid.uuid4().hex[:10]

            # Save original bytes first (works even if Pillow is missing/broken)
            ext = pathlib.Path(str(file_path)).suffix.lower()
            if ext not in ('.jpg', '.jpeg', '.png', '.webp'):
                # Don't lie about extension for exotic formats (heic/heif etc.)
                ext = '.bin'

            raw_name = f'{stem}{ext}'
            raw_path = uploads_dir / raw_name
            raw_path.write_bytes(file_bytes.getvalue())

            # Try to convert to WEBP/JPEG for stable rendering (optional)
            try:
                from PIL import Image
                file_bytes.seek(0)
                img = Image.open(file_bytes)

                if img.mode in ('RGBA', 'LA') or (img.mode == 'P' and 'transparency' in img.info):
                    img = img.convert('RGBA')
                else:
                    img = img.convert('RGB')

                filename = f'{stem}.webp'
                filepath = uploads_dir / filename
                try:
                    img.save(str(filepath), 'WEBP', quality=85, method=6, lossless=False)
                    return f'/uploads/{filename}'
                except Exception:
                    filename = f'{stem}.jpg'
                    filepath = uploads_dir / filename
                    img_rgb = img.convert('RGB') if img.mode != 'RGB' else img
                    img_rgb.save(str(filepath), 'JPEG', quality=88, optimize=True)
                    return f'/uploads/{filename}'
            except Exception:
                # Fall back to raw file only if it is browser-renderable
                if ext in ('.jpg', '.jpeg', '.png', '.webp'):
                    return f'/uploads/{raw_name}'
                return ''

        except ImportError:
            return ''

        except Exception as e:
            print('photo_utils error:', e)
            return ''

    else:

        val = (message.text or '').strip()

        if val == '-':

            val = ''

        return val
