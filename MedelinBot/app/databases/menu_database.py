
import re

from bson import ObjectId

from typing import Any

from app.databases.mongo_client import get_db

_GRAM_RE = re.compile('(?P<num>\\d+(?:[.,]\\d+)?)\\s*(?P<unit>г|гр|g|грам|грамм|кг|kg)', re.IGNORECASE | re.VERBOSE)

def parse_grams(value: Any) -> int | None:

    if not value:

        return None

    s = str(value).replace(',', '.').strip()

    m = _GRAM_RE.search(s)

    if not m:

        return None

    try:

        num = float(m.group('num'))

    except ValueError:

        return None

    unit = (m.group('unit') or '').lower()

    grams = int(round(num * 1000)) if unit in ('кг', 'kg') else int(round(num))

    return grams if grams > 0 else None

def parse_gramovka_grams(value):

    return parse_grams(value)

def clean_coffee_name(name: str) -> str:

    if not name:

        return ''

    return re.sub('\\d+\\s*(г|гр|кг|g|kg)', '', name, flags=re.IGNORECASE).strip()

def strip_gramovka(name: str) -> str:

    return clean_coffee_name(name)

def _doc_id(doc: dict[str, Any]) -> str:

    oid = doc.get('_id')

    if isinstance(oid, ObjectId):

        return str(oid)

    return str(oid) if oid is not None else ''

class MenuDatabase:

    async def connect(self):

        await get_db()

    async def close(self):

        return

    async def clear_menu(self):

        db = await get_db()

        await db.menu.delete_many({})

        from app.utils.data_cache import public_data_cache

        await public_data_cache.refresh_menu()

    async def add_item(self, category, name, price, description='', volume='', calories='', image_url='', composition='', strength=0, sweetness=0, options=None, country='', altitude='', sort='', processing='', roast='', taste='', **extra):

        db = await get_db()

        res = await db.menu.insert_one({'category': category, 'name': name, 'price': price, 'description': description or '', 'volume': volume or '', 'calories': calories or '', 'image_url': image_url or '', 'composition': composition or '', 'strength': strength or 0, 'sweetness': sweetness or 0, 'options': options or [], 'country': country or '', 'altitude': altitude or '', 'sort': sort or '', 'processing': processing or '', 'roast': roast or '', 'taste': taste or '', 'extra': extra or {}})

        inserted_id = str(res.inserted_id)

        from app.utils.data_cache import public_data_cache

        await public_data_cache.refresh_menu()

        return inserted_id

    async def get_menu_structured(self):

        db = await get_db()

        categories = await self.get_categories()

        result = []

        for cat in categories:

            items = await self.get_items_by_category(cat)

            structured_items = []

            for item in items:

                structured_items.append({'id': item[0], 'name': item[1], 'price': item[2], 'description': item[3], 'volume': item[4], 'calories': item[5], 'image_url': item[6], 'composition': item[7], 'strength': item[8], 'sweetness': item[9], 'options': item[10]})

            result.append({'category': cat, 'items': structured_items, 'simple': cat in ['➕ До Кави', '🍃 Декаф', 'Молоко', 'Додатки', 'Сиропи']})

        return result

    async def get_categories(self):

        db = await get_db()

        explicit_cats = await db.categories.find().to_list(length=None)

        cat_names = [c.get('name') for c in explicit_cats if c.get('name')]

        distinct_cats = await db.menu.distinct('category')

        for dc in distinct_cats:

            if dc not in cat_names:

                cat_names.append(dc)

        # Purge "Матча" if present (fixed categories)
        filtered: list[str] = []
        for c in cat_names:
            s = str(c or '').strip()
            if s and s.casefold() == 'матча':
                try:
                    await self.delete_category(s)
                except Exception:
                    pass
                continue
            filtered.append(s)

        return [c for c in filtered if c]

    async def add_category(self, name: str):

        db = await get_db()

        if not await db.categories.find_one({'name': name}):

            await db.categories.insert_one({'name': name})

            from app.utils.data_cache import public_data_cache

            await public_data_cache.refresh_menu()

        return True

    async def delete_category(self, name: str):

        db = await get_db()

        await db.categories.delete_one({'name': name})

        await db.menu.delete_many({'category': name})

        from app.utils.data_cache import public_data_cache

        await public_data_cache.refresh_menu()

        return True

    async def update_category(self, old_name: str, new_name: str):

        db = await get_db()

        await db.categories.update_one({'name': old_name}, {'$set': {'name': new_name}}, upsert=True)

        await db.menu.update_many({'category': old_name}, {'$set': {'category': new_name}})

        from app.utils.data_cache import public_data_cache

        await public_data_cache.refresh_menu()

        return True

    async def get_items_by_category(self, category):

        db = await get_db()

        cursor = db.menu.find({'category': category})

        items = await cursor.to_list(length=None)

        return [(str(i['_id']), i.get('name', ''), i.get('price', 0), i.get('description', ''), i.get('volume', ''), i.get('calories', ''), i.get('image_url', ''), i.get('composition', ''), i.get('strength', 0), i.get('sweetness', 0), i.get('options', [])) for i in items]

    async def get_items_by_category_id(self, category_id):

        return await self.get_items_by_category(category_id)

    async def get_item_by_id(self, item_id):

        db = await get_db()

        try:

            item = await db.menu.find_one({'_id': ObjectId(item_id)})

            if not item:

                return None

            return (str(item['_id']), item.get('category', ''), item.get('name', ''), item.get('price', 0), item.get('description', ''), item.get('volume', ''), item.get('calories', ''), item.get('image_url', ''), item.get('composition', ''), item.get('strength', 0), item.get('sweetness', 0), item.get('options', []))

        except:

            return None

    async def get_item_by_name(self, name: str):

        db = await get_db()

        item = await db.menu.find_one({'name': name})

        if not item:

            return None

        return (str(item['_id']), item.get('category', ''), item.get('name', ''), item.get('price', 0), item.get('description', ''), item.get('volume', ''), item.get('calories', ''), item.get('image_url', ''), item.get('composition', ''), item.get('strength', 0), item.get('sweetness', 0), item.get('options', []))

    async def delete_item(self, item_id):

        db = await get_db()

        try:

            res = await db.menu.delete_one({'_id': ObjectId(item_id)})

            success = bool(res.deleted_count)

            if success:

                from app.utils.data_cache import public_data_cache

                await public_data_cache.refresh_menu()

            return success

        except:

            return False

    async def update_item(self, item_id, update_data):

        db = await get_db()

        try:

            res = await db.menu.update_one({'_id': ObjectId(item_id)}, {'$set': update_data})

            success = bool(res.matched_count)

            if success:

                from app.utils.data_cache import public_data_cache

                await public_data_cache.refresh_menu()

            return success

        except:

            return False

menu_db = MenuDatabase()
