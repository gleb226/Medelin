import json

import re

from pathlib import Path

from typing import Any

class PublicDataCache:

    def __init__(self) -> None:

        self._memory: dict[str, Any] = {}

        self._dir = Path(__file__).resolve().parents[3] / 'MedelinSite' / 'cache'

        self._dir.mkdir(parents=True, exist_ok=True)

    def get(self, key: str) -> Any | None:

        return self._memory.get(key) or self._load_from_disk(key)

    def set(self, key: str, value: Any) -> Any:

        self._memory[key] = value

        self._write_to_disk(key, value)

        return value

    async def warm_all(self, max_retries: int = 3) -> None:

        for attempt in range(max_retries):

            try:

                await self.refresh_menu()

                await self.refresh_locations()

                await self.refresh_socials()

                await self.refresh_coffee()

                return

            except Exception:

                if attempt < max_retries - 1:

                    import asyncio

                    await asyncio.sleep(5)

    async def refresh(self, key: str) -> Any:

        if key == 'menu':

            return await self.refresh_menu()

        elif key == 'coffee':

            return await self.refresh_coffee()

        elif key == 'locations':

            return await self.refresh_locations()

        elif key == 'socials':

            return await self.refresh_socials()

        return self.get(key)

    async def refresh_coffee(self) -> list[dict[str, Any]]:

        from app.databases.coffee_beans_database import coffee_beans_db

        items = await coffee_beans_db.get_all_beans()

        formatted = []

        for i in items:

            formatted.append({'id': str(i.get('_id')), 'name': i.get('name', ''), 'description': i.get('description', ''), 'price_250': i.get('price_250', 0), 'price_500': i.get('price_500', 0), 'price_1000': i.get('price_1000', 0), 'image_url': i.get('image_url', ''), 'altitude': i.get('altitude', ''), 'sort': i.get('sort', ''), 'processing': i.get('processing', ''), 'roast': i.get('roast', ''), 'variety': i.get('variety', ''), 'cup_score': i.get('cup_score', ''), 'harvest': i.get('harvest', ''), 'taste': i.get('taste', ''), 'acidity': i.get('acidity', 0), 'bitterness': i.get('bitterness', 0), 'body': i.get('body', 0)})

        return self.set('coffee', formatted)

    async def refresh_menu(self) -> list[dict[str, Any]]:

        from app.databases.menu_database import menu_db

        def fix_encoding(s: Any) -> str:
            if not s: return ""
            s = str(s)
            if any(c in s for c in 'абвгґдеєжзиіїйклмнопрстуфхцчшщьюя'):
                return s
            try:
                return s.encode('latin1').decode('utf-8')
            except:
                try:
                    return s.encode('cp1252').decode('utf-8')
                except:
                    return s

        def normalize_category(value: Any) -> str:

            s = fix_encoding(value)

            s = re.sub('[^0-9A-Za-z\u0400-\u04FF\s]', ' ', s)

            s = re.sub('\s+', ' ', s).strip().casefold()

            return s

        hidden_categories = {'до кави', 'декаф', 'молоко', 'додатки', 'сиропи'}

        hidden_categories |= {normalize_category('До кави'), normalize_category('Декаф'), normalize_category('Молоко'), normalize_category('Додатки'), normalize_category('Сиропи')}

        categories = await menu_db.get_categories()
        addon_items: list[tuple[Any, ...]] = []
        milk_items: list[tuple[Any, ...]] = []

        for cat in categories:
            norm_cat = normalize_category(cat)
            if norm_cat == 'до кави':
                addon_items = await menu_db.get_items_by_category(cat)
            elif norm_cat == 'молоко':
                milk_items = await menu_db.get_items_by_category(cat)

        def build_default_coffee_options() -> list[dict[str, Any]]:
            options: list[dict[str, Any]] = [
                {'type': 'caffeine', 'name': 'Стандарт', 'add_price': 0},
                {'type': 'caffeine', 'name': 'Декаф', 'add_price': 10},
                {'type': 'milk', 'name': 'Звичайне', 'add_price': 0},
                {'type': 'milk', 'name': 'Безлактозне', 'add_price': 15},
                {'type': 'milk', 'name': 'Бананове', 'add_price': 30},
                {'type': 'milk', 'name': 'Ванільне', 'add_price': 30},
                {'type': 'milk', 'name': 'Кокосове', 'add_price': 30},
                {'type': 'milk', 'name': 'Мигдалеве', 'add_price': 30},
                {'type': 'milk', 'name': 'Вівсяне', 'add_price': 30}
            ]
            
            if milk_items:
                for it in milk_items:
                    name = fix_encoding(it[1] if len(it) > 1 else '')
                    price = it[2] if len(it) > 2 else 0
                    if not name or name in ['Звичайне', 'Безлактозне', 'Бананове', 'Ванільне', 'Кокосове', 'Мигдалеве', 'Вівсяне']: continue
                    options.append({'type': 'milk', 'name': name, 'add_price': int(price or 0)})

            if addon_items:
                for it in addon_items:
                    name = fix_encoding(it[1] if len(it) > 1 else '')
                    price = it[2] if len(it) > 2 else 0
                    if not name: continue
                    if 'альтернатив' in name.casefold() and 'молок' in name.casefold():
                        continue
                    options.append({'type': 'addon', 'name': name, 'add_price': int(price or 0)})
            else:
                options.extend([
                    {'type': 'addon', 'name': 'Молоко 70мл', 'add_price': 10},
                    {'type': 'addon', 'name': 'Вершки 70мл', 'add_price': 10},
                    {'type': 'addon', 'name': 'Вершки порційні', 'add_price': 10},
                    {'type': 'addon', 'name': 'Мед', 'add_price': 10},
                    {'type': 'addon', 'name': 'Згущене молоко', 'add_price': 15},
                    {'type': 'addon', 'name': 'Карамель', 'add_price': 15}
                ])

            seen: set[tuple[str, str]] = set()

            deduped: list[dict[str, Any]] = []

            for opt in options:

                key = (str(opt.get('type', '')), str(opt.get('name', '')))

                if key in seen:

                    continue

                seen.add(key)

                deduped.append(opt)

            return deduped

        default_coffee_options = build_default_coffee_options()

        full_menu = []

        for cat in categories:

            cat_f = fix_encoding(cat)
            cat_norm = normalize_category(cat)

            if cat_norm in hidden_categories:

                continue

            items = await menu_db.get_items_by_category(cat)

            formatted = []

            for i in items:

                try:

                    item_id = i[0]

                    name = fix_encoding(i[1] if len(i) > 1 else '')

                    price = i[2] if len(i) > 2 else 0

                    desc = fix_encoding(i[3] if len(i) > 3 else '')

                    vol = i[4] if len(i) > 4 else ''

                    cal = i[5] if len(i) > 5 else ''

                    img = i[6] if len(i) > 6 else ''
                    comp = fix_encoding(i[7] if len(i) > 7 else '')
                    strn = i[8] if len(i) > 8 else 0
                    swt = i[9] if len(i) > 9 else 0
                    opts = i[10] if len(i) > 10 else []
                    
                    if isinstance(opts, str): 
                        opts = []
                    
                    # Визначаємо тип напою для призначення опцій
                    name_l = name.lower()
                    cat_l = cat_f.lower()
                    
                    # ПЕРЕВІРКА: чи це саме КАВА (для декафу та додатків)
                    # Ми перевіряємо як категорію, так і назву
                    is_pure_coffee = any(x in cat_l for x in ['кава', 'декаф']) or \
                                    any(x in name_l for x in ['американо', 'еспресо', 'допіо', 'ристрето', 'латте', 'капучино', 'раф', 'флет', 'глясе'])
                    
                    # Кавовий/молочний напій взагалі?
                    is_milk_based = any(x in cat_l or x in name_l for x in [
                        'мілк', 'матча', 'какао', 'лате', 'латте', 'капуч', 'флет', 'раф', 
                        'глясе', 'айс', 'вершк', 'молок'
                    ])
                    
                    # Чи це проста категорія де не треба опцій?
                    is_simple_cat = any(x in cat_l for x in ['десерт', 'чай', 'фреш', 'напої', 'напои', 'бургер', 'салат', 'сендвіч'])

                    use_default = is_pure_coffee or is_milk_based
                    if not use_default and not is_simple_cat:
                        use_default = True

                    # Призначення опцій
                    item_options = opts or []
                    if use_default:
                        # Якщо немає молока в опціях - додаємо дефолтний набір
                        if not any(o.get('type') == 'milk' for o in item_options):
                            if is_pure_coffee:
                                # Для кави - ПОВНИЙ набір (декаф + молоко + додатки)
                                item_options = default_coffee_options
                            else:
                                # Для інших напоїв (мілкшейки, матча, какао) - ТІЛЬКИ молоко
                                item_options = [o for o in default_coffee_options if o.get('type') == 'milk']

                    formatted.append({
                        'id': str(item_id), 'name': name, 'price': price or 0, 
                        'description': desc, 'volume': vol, 'calories': cal, 
                        'image_url': img, 'composition': comp, 
                        'strength': strn or 0, 'sweetness': swt or 0, 
                        'options': item_options
                    })

                except Exception as e:

                    print(f'Error caching menu item in {cat_f}: {str(e)}')

                    continue

            full_menu.append({'category': cat_f, 'items': formatted, 'simple': cat_norm in ['➕ до кави', '🍃 декаф', 'молоко', 'додатки', 'сиропи']})

        return self.set('menu', full_menu)

    async def refresh_locations(self) -> list[dict[str, Any]]:

        from app.databases.location_database import location_db

        locs = await location_db.get_all_locations()

        formatted = []

        for l in locs:

            formatted.append({'id': str(l.get('_id') or l.get('id')), 'name': l.get('name', ''), 'address': l.get('address', ''), 'schedule': l.get('schedule', ''), 'phone': l.get('phone', ''), 'google_maps_url': l.get('google_maps_url', ''), 'image_url': l.get('image_url', ''), 'amenities': l.get('amenities', []), 'atmosphere': l.get('atmosphere', ''), 'coordinates': l.get('coordinates')})

        return self.set('locations', formatted)

    async def refresh_socials(self) -> list[dict[str, Any]]:

        from app.databases.socials_database import socials_db

        socs = await socials_db.get_all_socials()

        formatted = [{'id': str(s.get('_id') or s.get('id')), 'name': s.get('name', ''), 'url': s.get('url', '')} for s in socs]

        return self.set('socials', formatted)

    def _path_for(self, key: str) -> Path:

        return self._dir / f'{key}.json'

    def _load_from_disk(self, key: str) -> Any | None:

        p = self._path_for(key)

        if not p.exists():

            return None

        try:

            d = json.loads(p.read_text(encoding='utf-8'))

            self._memory[key] = d

            return d

        except:

            return None

    def _write_to_disk(self, key: str, value: Any) -> None:

        self._path_for(key).write_text(json.dumps(value, ensure_ascii=False, indent=2), encoding='utf-8')

public_data_cache = PublicDataCache()
