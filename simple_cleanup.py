
import asyncio
from motor.motor_asyncio import AsyncIOMotorClient
import os
from dotenv import load_dotenv

# Load env from parent or current dir
for p in ['.env', '../.env']:
    if os.path.exists(p):
        load_dotenv(p)

MONGO_URI = os.getenv('MONGO_URI')
MONGO_DB_NAME = os.getenv('MONGO_DB_NAME')

async def cleanup():
    if not MONGO_URI:
        print("MONGO_URI not found")
        return

    print(f"Connecting to {MONGO_URI}...")
    client = AsyncIOMotorClient(MONGO_URI)
    db = client[MONGO_DB_NAME]
    
    # Check connection
    try:
        await client.admin.command('ping')
        print("Connected successfully")
    except Exception as e:
        print(f"Connection failed: {e}")
        return

    # 1. Collections to drop
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
    colls = await db.list_collection_names()
    if 'socials' in colls:
        print("Renaming 'socials' to 'contacts'")
        await db.socials.rename('contacts')
    elif 'contacts' not in colls:
        print("Creating 'contacts' collection")
        await db.create_collection('contacts')

    # 3. Update 'coffee_beans'
    print("Cleaning up 'coffee_beans' and resetting fields")
    beans_cursor = db.coffee_beans.find({})
    beans = await beans_cursor.to_list(length=None)
    
    for bean in beans:
        name = bean.get('name', 'Unknown Bean')
        img = bean.get('image_url', '')
        
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
    
    client.close()
    print("Cleanup complete.")

if __name__ == "__main__":
    asyncio.run(cleanup())
