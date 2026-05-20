import asyncio
import sys
import os
import json
from pathlib import Path

# Add the project root to sys.path
sys.path.append(os.getcwd())

from app.utils.data_cache import public_data_cache

async def main():
    print("Warming cache...")
    await public_data_cache.warm_all()
    
    menu = public_data_cache.get('menu')
    if not menu:
        print("Menu is empty!")
        return
        
    print(f"Categories found: {[s['category'] for s in menu]}")
    
    for section in menu:
        cat = section['category']
        print(f"\n--- Category: {cat} ---")
        for item in section['items']:
            opts = item.get('options', [])
            milk_opts = [o['name'] for o in opts if o.get('type') == 'milk']
            print(f"Item: {item['name']} | Milk Options: {milk_opts}")

if __name__ == "__main__":
    asyncio.run(main())
