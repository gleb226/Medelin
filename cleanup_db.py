
import asyncio
import os
import sys
from pathlib import Path

# Add project root to sys.path
root_dir = Path(__file__).resolve().parent.parent
sys.path.append(str(root_dir))

from MedelinBot.app.databases.mongo_client import get_db

async def cleanup():
    db = await get_db()
    
    # 1. Collections to drop completely
    to_drop = [
        'users', 'orders', 'active_bookings', 'active_orders', 
        'guest_messages', 'sales', 'menu', 'categories', 
        'activity_logs', 'admin_auth_requests', 'admin_sessions', 
        'notifications', 'data_cache'
    ]
    
    for coll in to_drop:
        print(f"Dropping collection: {coll}")
        await db[coll].drop()
    
    # 2. Rename 'socials' to 'contacts'
    if 'socials' in await db.list_collection_names():
        print("Renaming 'socials' to 'contacts'")
        await db.socials.rename('contacts')
    
    # 3. Update 'coffee_beans'
    print("Cleaning up 'coffee_beans' and resetting fields")
    beans_cursor = db.coffee_beans.find({})
    beans = await beans_cursor.to_list(length=None)
    
    for bean in beans:
        # Keep name and image_url, reset everything else to empty strings/None
        name = bean.get('name', 'Unknown Bean')
        img = bean.get('image_url', '')
        
        # New structure
        new_bean = {
            'name': name,
            'image_url': img,
            'country': '',      # Країна
            'station': '',      # Станція обробки
            'processing': '',   # Спосіб обробки
            'descriptors': '',  # Дескриптори
            'species': '',      # Ботанічний вид
            'variety': '',      # Різновид
            'region': '',       # Регіон
            'altitude': '',      # Висота
            'roast': '',        # Спосіб приготування / Обсмаження
            'price_250': 0,     # For compatibility
            'price_500': 0,
            'price_1000': 0
        }
        
        await db.coffee_beans.replace_one({'_id': bean['_id']}, new_bean)
    
    print("Database cleanup complete.")

if __name__ == "__main__":
    asyncio.run(cleanup())
