from aiogram import Bot
from app.common.config import BOT_TOKEN

if not BOT_TOKEN:
    raise ValueError("BOT_TOKEN is not set in .env")

bot = Bot(token=BOT_TOKEN)
