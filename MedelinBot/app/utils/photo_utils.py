
import os

import uuid

import pathlib

from aiogram import Bot

from aiogram.types import Message

def _get_uploads_dir() -> pathlib.Path:
    """
    Determines the directory for photo uploads based on the environment.
    Priority:
    1. UPLOADS_DIR environment variable.
    2. /app/uploads (Docker volume mount in separate container setup).
    3. /usr/share/nginx/html/images/uploads (Unified Dockerfile setup).
    4. Local development path (MedelinSite/images/uploads).
    """
    env_dir = (os.getenv('UPLOADS_DIR') or '').strip()
    if env_dir:
        return pathlib.Path(env_dir)

    # 1. Separate containers: /app/uploads is usually mapped to MedelinSite/images/uploads
    docker_mount = pathlib.Path('/app/uploads')
    if docker_mount.exists() or os.path.exists('/.dockerenv'):
        # Even if it doesn't exist yet, if we are in Docker, this is a good candidate
        # if it's the expected volume mount point.
        if docker_mount.parent.exists(): 
             return docker_mount

    # 2. Unified container: Site is at /usr/share/nginx/html
    unified_path = pathlib.Path('/usr/share/nginx/html/images/uploads')
    if unified_path.parent.exists():
        return unified_path

    # 3. Local development (fallback)
    # Repo layout (dev): <repo>/MedelinBot/app/utils/photo_utils.py -> parents[3] == <repo>
    try:
        repo_root = pathlib.Path(__file__).resolve().parents[3]
        dev_path = repo_root / 'MedelinSite' / 'images' / 'uploads'
        return dev_path
    except Exception:
        return pathlib.Path('uploads')

async def process_photo(message: Message, bot: Bot) -> str:
    file_id = None
    original_ext = ".jpg" # Default fallback

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
        import io
        file_bytes_io = io.BytesIO()

        # Download file
        try:
            f = await bot.get_file(file_id)
            await bot.download_file(f.file_path, destination=file_bytes_io)
            if f.file_path:
                original_ext = pathlib.Path(f.file_path).suffix.lower()
        except Exception:
            await bot.download(file_id, destination=file_bytes_io)
        
        file_bytes = file_bytes_io.getvalue()
        if not file_bytes:
            return ''

        uploads_dir = _get_uploads_dir()
        uploads_dir.mkdir(parents=True, exist_ok=True)
        stem = uuid.uuid4().hex[:10]

        # Try to convert to WEBP for efficiency and stability
        try:
            from PIL import Image
            img = Image.open(io.BytesIO(file_bytes))

            # Handle transparency
            if img.mode in ('RGBA', 'LA') or (img.mode == 'P' and 'transparency' in img.info):
                img = img.convert('RGBA')
            else:
                img = img.convert('RGB')

            filename = f'{stem}.webp'
            filepath = uploads_dir / filename
            
            # Save as WEBP
            img.save(str(filepath), 'WEBP', quality=85, method=6, lossless=False)
            return f'/uploads/{filename}'
        except Exception as e:
            # Pillow failed or not installed, save raw if it's a common image format
            renderable_exts = ('.jpg', '.jpeg', '.png', '.webp', '.gif')
            ext = original_ext if original_ext in renderable_exts else '.jpg'
            
            filename = f'{stem}{ext}'
            filepath = uploads_dir / filename
            filepath.write_bytes(file_bytes)
            return f'/uploads/{filename}'

    except Exception as e:
        print(f'[PhotoUtils] Error processing photo: {e}')
        return ''
