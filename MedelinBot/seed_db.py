
import asyncio
import logging
import re
from typing import Any
from app.databases.mongo_client import get_db

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# --- Realistic Seed Data ---

LOCATIONS = [
    {
        "name": "Medelin Central",
        "address": "вул. Корятовича, 5",
        "schedule": "08:00 - 22:00",
        "phone": "+380501234567",
        "google_maps_url": "https://maps.app.goo.gl/central",
        "image_url": "https://images.unsplash.com/photo-1554118811-1e0d58224f24?q=80&w=1000&auto=format&fit=crop",
        "amenities": ["Wi-Fi", "Тераса", "Pet-friendly"],
        "atmosphere": "Затишна кав'ярня в самому серці міста з видом на площу.",
        "coordinates": {"lat": 48.6217, "lon": 22.2875}
    },
    {
        "name": "Medelin Terrace",
        "address": "вул. Собранецька, 12",
        "schedule": "09:00 - 21:00",
        "phone": "+380507654321",
        "google_maps_url": "https://maps.app.goo.gl/terrace",
        "image_url": "https://images.unsplash.com/photo-1559925373-2f8421b51d6c?q=80&w=1000&auto=format&fit=crop",
        "amenities": ["Wi-Fi", "Парковка", "Дитяча зона"],
        "atmosphere": "Простора локація з великою літньою терасою та смачними десертами.",
        "coordinates": {"lat": 48.6250, "lon": 22.2800}
    }
]

SOCIALS = [
    {"name": "Instagram Central", "url": "https://instagram.com/medelin_central"},
    {"name": "Instagram Terrace", "url": "https://instagram.com/medelin_terrace"},
    {"name": "Facebook", "url": "https://facebook.com/medelin.uzh"},
    {"name": "TikTok", "url": "https://tiktok.com/@medelin_coffee"},
    {"name": "Telegram", "url": "https://t.me/MedelinBot"}
]

BEANS = [
    {
        "name": "Ethiopia Yirgacheffe",
        "description": "Класична ефіопська кава з яскравими квітковими нотами та цитрусовою кислинкою.",
        "price_250": 380,
        "price_500": 720,
        "price_1000": 1350,
        "image_url": "https://images.unsplash.com/photo-1559056199-641a0ac8b55e?q=80&w=1000&auto=format&fit=crop",
        "sort": "100% Арабіка",
        "taste": "Жасмин, лимон, бергамот",
        "roast": "Світле",
        "acidity": 5,
        "bitterness": 2,
        "body": 3
    },
    {
        "name": "Brazil Mogiana",
        "description": "Збалансована кава з низькою кислотністю та вираженими нотами горіхів і шоколаду.",
        "price_250": 320,
        "price_500": 600,
        "price_1000": 1100,
        "image_url": "https://images.unsplash.com/photo-1580915411954-282cb1b0d780?q=80&w=1000&auto=format&fit=crop",
        "sort": "100% Арабіка",
        "taste": "Фундук, молочний шоколад, карамель",
        "roast": "Середнє",
        "acidity": 2,
        "bitterness": 3,
        "body": 4
    },
    {
        "name": "Colombia Supremo",
        "description": "Класика Південної Америки. Насичений смак з фруктовим відтінком.",
        "price_250": 350,
        "price_500": 670,
        "price_1000": 1250,
        "image_url": "https://images.unsplash.com/photo-1611854779393-1b2da9d400fe?q=80&w=1000&auto=format&fit=crop",
        "sort": "100% Арабіка",
        "taste": "Червоне яблуко, карамель, какао",
        "roast": "Середнє",
        "acidity": 3,
        "bitterness": 2,
        "body": 4
    }
]

MENU_ITEMS = [
    # Кава
    {"category": "Кава", "name": "Еспресо", "price": 45, "description": "Класичний міцний напій.", "volume": "30 мл", "image_url": "https://images.unsplash.com/photo-1510707577719-5d6874021d47?q=80&w=1000&auto=format&fit=crop"},
    {"category": "Кава", "name": "Капучино", "price": 65, "description": "Ніжна молочна пінка та еспресо.", "volume": "250 мл", "image_url": "https://images.unsplash.com/photo-1534778101976-62847782c213?q=80&w=1000&auto=format&fit=crop"},
    {"category": "Кава", "name": "Лате", "price": 75, "description": "Більше молока, більше насолоди.", "volume": "350 мл", "image_url": "https://images.unsplash.com/photo-1570968915860-54d5c301fa9f?q=80&w=1000&auto=format&fit=crop"},
    {"category": "Кава", "name": "Флет Вайт", "price": 85, "description": "Подвійний еспресо з тонким шаром піни.", "volume": "200 мл", "image_url": "https://images.unsplash.com/photo-1593444202241-2428298242bb?q=80&w=1000&auto=format&fit=crop"},
    
    # Десерти
    {"category": "Десерти", "name": "Чізкейк Нью-Йорк", "price": 120, "description": "Класичний вершковий десерт.", "volume": "150 г", "image_url": "https://images.unsplash.com/photo-1533134242443-d4fd215305ad?q=80&w=1000&auto=format&fit=crop"},
    {"category": "Десерти", "name": "Тірамісу", "price": 110, "description": "Легкий кавовий десерт.", "volume": "140 г", "image_url": "https://images.unsplash.com/photo-1571877227200-a0d98ea607e9?q=80&w=1000&auto=format&fit=crop"},
    {"category": "Десерти", "name": "Макарон", "price": 45, "description": "Мигдалеве тістечко (смак в асортименті).", "volume": "40 г", "image_url": "https://images.unsplash.com/photo-1569864358642-9d1619702661?q=80&w=1000&auto=format&fit=crop"},
    
    # Напої
    {"category": "Напої", "name": "Лимонад Класичний", "price": 60, "description": "Освіжаючий лимон з м'ятою.", "volume": "400 мл", "image_url": "https://images.unsplash.com/photo-1513558161293-cdaf765ed2fd?q=80&w=1000&auto=format&fit=crop"},
    {"category": "Напої", "name": "Айс Лате", "price": 80, "description": "Холодна кава з льодом.", "volume": "400 мл", "image_url": "https://images.unsplash.com/photo-1517701550927-30cf4ba1dba5?q=80&w=1000&auto=format&fit=crop"},
    
    # Молоко (Опції)
    {"category": "Молоко", "name": "Звичайне", "price": 0, "description": "Включено у вартість"},
    {"category": "Молоко", "name": "Безлактозне", "price": 15},
    {"category": "Молоко", "name": "Бананове", "price": 30},
    {"category": "Молоко", "name": "Вівсяне", "price": 30},
    {"category": "Молоко", "name": "Кокосове", "price": 35},
    
    # Додатки (Опції)
    {"category": "Додатки", "name": "Вершки порційні", "price": 10},
    {"category": "Додатки", "name": "Мед", "price": 10},
    {"category": "Додатки", "name": "Карамельний сироп", "price": 15},
    {"category": "Додатки", "name": "Шоколадний сироп", "price": 15}
]

async def seed_database():
    logger.info("Starting fresh database seed...")
    db = await get_db()
    
    # 1. Clear everything
    collections_to_clear = [
        "menu", "coffee_beans", "locations", "socials", 
        "orders", "active_orders", "active_bookings", "errors", "activity_logs"
    ]
    for coll in collections_to_clear:
        count = await db[coll].delete_many({})
        logger.info(f"Cleared {count.deleted_count} documents from '{coll}'")
    
    # 2. Seed Locations
    for loc in LOCATIONS:
        await db.locations.insert_one(loc)
    logger.info(f"Seeded {len(LOCATIONS)} locations")
    
    # 3. Seed Socials
    for soc in SOCIALS:
        await db.socials.insert_one(soc)
    logger.info(f"Seeded {len(SOCIALS)} socials")
    
    # 4. Seed Beans
    for bean in BEANS:
        await db.coffee_beans.insert_one(bean)
    logger.info(f"Seeded {len(BEANS)} beans")
    
    # 5. Seed Menu Items
    for item in MENU_ITEMS:
        # Defaults for menu items
        item.setdefault("calories", "0")
        item.setdefault("composition", "")
        item.setdefault("strength", 0)
        item.setdefault("sweetness", 0)
        item.setdefault("is_hidden", False)
        await db.menu.insert_one(item)
    logger.info(f"Seeded {len(MENU_ITEMS)} menu items")
    
    logger.info("Database seeding complete! ☕🚀")

if __name__ == "__main__":
    asyncio.run(seed_database())
