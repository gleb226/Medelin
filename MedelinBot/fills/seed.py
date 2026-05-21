import asyncio
import sys
from pathlib import Path
ROOT_DIR = Path(__file__).resolve().parents[1]
if str(ROOT_DIR) not in sys.path:
    sys.path.append(str(ROOT_DIR))
from app.databases.menu_database import menu_db
from app.databases.coffee_beans_database import coffee_beans_db
from app.databases.location_database import location_db
from app.databases.socials_database import socials_db
from app.databases.mongo_client import close_client
PHOTO_URL_MENU = 'https://images.unsplash.com/photo-1630040995437-80b01c5dd52d?q=80&w=687&auto=format&fit=crop'
PHOTO_URL_BEANS = 'https://images.pexels.com/photos/1695052/pexels-photo-1695052.jpeg?auto=compress&cs=tinysrgb&w=800'
PHOTO_URL_LOCATION = 'https://images.pexels.com/photos/2615323/pexels-photo-2615323.jpeg?auto=compress&cs=tinysrgb&w=800'
STR_MAP = {'0': 0, '1': 1, '2': 2, '3': 3, '4': 4, '5': 5}
SWEET_MAP = {'відсутня': 0, 'низька': 1, 'середня': 3, 'висока': 5}
MILK_OPTIONS: list[dict] = []
CAFFEINE_OPTIONS = [{'type': 'caffeine', 'name': 'Звичайна', 'add_price': 0}, {'type': 'caffeine', 'name': 'Декаф', 'add_price': 10}]
ADDON_OPTIONS = [{'type': 'addon', 'name': 'Молоко 70мл', 'add_price': 10}, {'type': 'addon', 'name': 'Вершки 70мл', 'add_price': 10}, {'type': 'addon', 'name': 'Мед', 'add_price': 10}, {'type': 'addon', 'name': 'Згущене молоко', 'add_price': 15}, {'type': 'addon', 'name': 'Карамель', 'add_price': 15}]
MENU_OVERRIDES = [('Кава', 'Американо', '43', "Класична чорна кава з м'яким смаком для бадьорого ранку.", '150 мл', '5 ккал', '2', 'низька', '100% арабіка', False, True, ('Індія', '900-1200м', 'Арабіка', 'Монсунінг', 'Середнє', 'Мускатний горіх, земляні ноти')), ('Кава', 'Глясе', '73', 'Прохолодна кава з великою кулькою ніжного ванільного морозива.', '250 мл', '180 ккал', '2', 'висока', '100% арабіка + морозиво', True, True, ('Бразилія', '1100м', 'Арабіка', 'Натуральна', 'Середнє', 'Горіх, шоколад')), ('Кава', 'Еспресо', '42', 'Основа основ — концентрований напій з щільним тілом та стійкою пінкою.', '30 мл', '5 ккал', '3', 'відсутня', '100% арабіка', False, True, ('Індія', '900-1200м', 'Арабіка', 'Монсунінг', 'Середнє', 'Земляні ноти')), ('Кава', 'Капучино', '57', 'Класичне співвідношення еспресо та ніжно збитого молока.', '200 мл', '120 ккал', '2', 'низька', '100% арабіка + молоко', True, True, ('Ефіопія', '1800-2100м', 'Арабіка', 'Мита', 'Світле', 'Жасмин, цитрус')), ('Кава', 'Лате', '63', 'Найніжніший кавовий напій з великою кількістю молока.', '300 мл', '150 ккал', '1', 'низька', '100% арабіка + молоко', True, True, ('Бразилія', '1100м', 'Арабіка', 'Натуральна', 'Середнє', 'Карамель, молочний шоколад')), ('Кава', 'Раф', '76', 'Вершковий десертний напій, збитий разом з ванільним цукром.', '250 мл', '250 ккал', '1', 'висока', '100% арабіка + вершки + ваніль', True, True, ('Колумбія', '1400-1600м', 'Арабіка', 'Мита', 'Середнє', 'Ваніль, вершки')), ('Кава', 'Фільтр кава', '60', 'Чиста кава, приготована методом прокапування через паперовий фільтр.', '250 мл', '2 ккал', '2', 'відсутня', '100% Specialty Арабіка', False, False, ('Ефіопія', '2000м', 'Арабіка', 'Натуральна', 'Світле', 'Ягоди, бергамот')), ('Кава', 'Флет Вайт', '94', 'Насичений смак подвійного рістрето з тонким шаром еластичного молока.', '200 мл', '130 ккал', '3', 'низька', '100% арабіка + молоко', True, True, ('Бразилія', '1100м', 'Арабіка', 'Натуральна', 'Середнє', 'Горіх, карамель')), ('Десерти', 'Вишневий Чізкейк', '110', 'Легкий чізкейк з кислинкою вишні та ніжною текстурою.', '150 г', '380 ккал', '0', 'середня', 'Вершковий сир, вишня, пісочна основа', False, False, None), ('Десерти', 'Горішки зі згущенкою', '30', 'Ті самі легендарні горішки зі справжнім згущеним молоком.', '50 г', '250 ккал', '0', 'висока', 'Згущене молоко, волоський горіх, пісочне тісто', False, False, None), ('Десерти', 'Еклер Карамельний', '80', 'Ніжне заварне тісто з оксамитовим карамельним кремом.', '70 г', '290 ккал', '0', 'висока', 'Заварний крем, карамель, бельгійський шоколад', False, False, None), ('Десерти', 'Макаронс (набір)', '140', 'Набір з двох французьких мигдалевих тістечок з різними смаками.', '70 г', '240 ккал', '0', 'висока', 'Мигдалеве борошно, білок, фруктовий ганаш', False, False, None), ('Десерти', 'Чізкейк Сан-Себастьян', '110', 'Насичений сирний десерт з характерною карамельною скоринкою.', '150 г', '450 ккал', '0', 'середня', 'Вершковий сир, вершки 33%, цукор, яйця', False, False, None), ('Напої', 'Еспресо Тонік', '85', 'Освіжаючий та ігристий мікс подвійного еспресо, тоніку та льоду.', '250 мл', '90 ккал', '2', 'середня', 'Еспресо, тонік Schweppes, лід, лимон', False, True, None), ('Напої', 'Лимонад Класичний', '90', 'Натуральний авторський лимонад з цитрусових.', '300 мл', '120 ккал', '0', 'середня', 'Сік лимона, сік апельсина, цукровий сироп, газована вода', False, False, None), ('Напої', 'Джміль (Bumble)', '105', 'Тришаровий напій з карамельного сиропу, апельсинового соку та еспресо.', '300 мл', '180 ккал', '2', 'середня', 'Еспресо, апельсиновий сік, карамельний сироп, лід', False, True, None), ('Чай', 'Чай Масала', '90', 'Пряний індійський чай на молочній основі з секретними спеціями.', '250 мл', '160 ккал', '1', 'середня', 'Чорний чай, молоко, імбир, кориця, кардамон, гвоздика', True, False, None), ('Чай', 'Зелений (Сенча)', '70', "Класичний японський зелений чай з м'яким трав'яним смаком.", '400 мл', '2 ккал', '0', 'відсутня', 'Листовий зелений чай сорту Сенча', False, False, None), ('Чай', 'Карпатський збір', '70', 'Ароматний збір гірських трав, зібраних власноруч.', '400 мл', '2 ккал', '0', 'відсутня', "М'ята, чебрець, материнка, липа, шипшина", False, False, None), ('Матча', 'Матча Лате', '90', 'Традиційний японський церемоніальний чай матча з молоком.', '250 мл', '140 ккал', '1', 'середня', 'Пудра матча, збите молоко', True, False, None), ('Какао', 'Какао з маршмелоу', '65', 'Насичений шоколадний напій з солодкими хмаринками маршмелоу.', '250 мл', '220 ккал', '0', 'середня', 'Какао-порошок Barry Callebaut, молоко, маршмелоу', True, False, None)]
MENU_SECTIONS = [('Кава', [('Американо', 43), ('Глясе', 73), ('Допіо', 84), ('Еспресо', 42), ('Еспресо Макіато', 45), ('Еспресо тонік', 85), ('Капучіно на подвійному', 75), ('Капучино', 57), ('Кортадо', 52), ('Лате', 63), ('Лате на подвійному', 85), ('Раф', 76), ('Фільтр', 60), ('Флет вайт', 94), ('Рістрето', 42), ('Айс лате', 63)]), ('Десерти', [('Вишневий чіз', 110), ('Горіх-лате чіз', 110), ('Горішки', 30), ('Десерт в асортименті', 110), ('Еклер карамель', 80), ('Шу малиновий', 95), ('Брауні', 65), ('Веган малиновий байт', 125), ('Веган тарт снікерс', 125), ('Еклер фісташка', 80), ('Кремова картопля', 75), ('Макаронс', 70), ('Наполеон', 110), ('Чізкейк бакський', 110), ('Трубочка фісташкова', 78), ('Цукерки веган', 52), ('Батончик фундук-кава', 90), ('Канелє', 45)]), ('Напої', [('Бейбічіно', 30), ('Вода з лимоном', 15), ('Джміль', 105), ('Лимонад', 90), ('Сік коник', 60), ('Сік березовий', 60), ('Деренівська газ', 60), ('Деренівська не газ', 60), ('Вода з лимоном 0,5л', 30)]), ('Масала', [('Масала', 90)]), ('Фреш', [('Апельсиновий фреш', 100), ('Апельсиново-грейпфрутовий фреш', 100), ('Яблучний фреш', 70), ('Яблучно-морквяний фреш', 70)]), ('Чай', [('Зелений чай', 70), ("Трав'яний чай", 70), ('Фруктовий чай', 70), ('Чай лохина', 70), ('Чорний чай', 70)]), ('Мілк', [('Банановий мілкшейк', 85), ('Класичний мілкшейк', 80), ('Полуничний мілкшейк', 85), ('Шоколадний мілкшейк', 85), ('Фрапе', 93)]), ('Какао', [('Какао', 52), ('Какао з маршмелоу', 65)])]

def _norm(s: str) -> str:
    return ' '.join(str(s or '').strip().split()).casefold()

def _guess_volume(category: str, name: str) -> str:
    n = _norm(name)
    c = _norm(category)
    if c == 'десерти':
        if 'макарон' in n:
            return '70 г'
        if 'горіш' in n:
            return '50 г'
        return '150 г'
    if c == 'кава':
        if 'рістр' in n or 'еспресо' in n:
            return '30 мл'
        if 'допіо' in n:
            return '60 мл'
        if 'америк' in n:
            return '150 мл'
        if 'капуч' in n or 'флет' in n or 'корт' in n:
            return '200 мл'
        if 'лате' in n:
            return '300 мл'
        if 'глясе' in n:
            return '250 мл'
        return '250 мл'
    if c in {'чай', 'фреш'}:
        return '400 мл' if c == 'чай' else '300 мл'
    if c in {'матча', 'какао', 'мілк', 'масала'}:
        return '250 мл'
    return '300 мл'

def _guess_calories(category: str, name: str) -> str:
    n = _norm(name)
    c = _norm(category)
    if c == 'кава':
        if 'рістр' in n or ('еспресо' in n and 'тонік' not in n):
            return '5 ккал'
        if 'америк' in n or 'фільтр' in n:
            return '5 ккал'
        if 'глясе' in n:
            return '180 ккал'
        if 'лате' in n:
            return '150 ккал'
        if 'капуч' in n or 'флет' in n or 'корт' in n:
            return '120 ккал'
        if 'раф' in n:
            return '250 ккал'
        if 'тонік' in n:
            return '90 ккал'
        return '120 ккал'
    if c == 'десерти':
        if 'браун' in n:
            return '420 ккал'
        if 'еклер' in n:
            return '290 ккал'
        if 'чіз' in n or 'чізкейк' in n:
            return '380 ккал'
        return '320 ккал'
    if c in {'матча', 'какао', 'мілк', 'масала'}:
        return '200 ккал'
    if c in {'фреш', 'напої'}:
        return '120 ккал'
    if c == 'чай':
        return '2 ккал'
    return '100 ккал'

def _guess_strength(category: str, name: str) -> str:
    n = _norm(name)
    c = _norm(category)
    if c == 'кава':
        if 'рістр' in n or 'допіо' in n:
            return '5'
        if 'еспресо' in n:
            return '4'
        if 'америк' in n or 'фільтр' in n:
            return '3'
        if 'флет' in n:
            return '4'
        if 'капуч' in n or 'корт' in n:
            return '3'
        if 'лате' in n or 'глясе' in n or 'раф' in n:
            return '2'
        return '3'
    if c == 'чай':
        return '2'
    if c in {'матча', 'масала'}:
        return '2'
    return '1'

def _guess_sweetness(category: str, name: str) -> str:
    n = _norm(name)
    c = _norm(category)
    if c == 'кава':
        if 'глясе' in n or 'раф' in n:
            return 'середня'
        return 'низька'
    if c == 'десерти':
        return 'висока'
    if c in {'матча', 'какао', 'мілк', 'масала'}:
        return 'середня'
    if c in {'фреш'}:
        return 'середня'
    if c == 'чай':
        return 'відсутня'
    return 'середня'

def _guess_composition(category: str, name: str) -> str:
    n = _norm(name)
    c = _norm(category)
    if c == 'кава':
        if 'тонік' in n:
            return 'Еспресо, тонік, лід, лимон'
        if 'америк' in n:
            return 'Еспресо, вода'
        if 'еспресо' in n or 'рістр' in n or 'допіо' in n:
            return 'Еспресо'
        if 'фільтр' in n:
            return 'Фільтр-кава'
        if 'глясе' in n:
            return 'Еспресо, морозиво, лід'
        return 'Еспресо, молоко'
    if c == 'десерти':
        return 'Фірмовий десерт'
    if c == 'чай':
        return "Листовий чай / трав'яний збір"
    if c == 'фреш':
        return 'Натуральний фреш'
    if c == 'какао':
        return 'Какао-порошок, молоко'
    if c == 'матча':
        return 'Матча, молоко'
    if c == 'мілк':
        return 'Молоко, наповнювач'
    if c == 'масала':
        return 'Чай, молоко, спеції'
    return 'Фірмовий напій'

def _guess_description(category: str, name: str) -> str:
    c = _norm(category)
    if c == 'кава':
        return 'Фірмова кава Medelin зі свіжим обсмаженням.'
    if c == 'десерти':
        return 'Десерт з асортименту Medelin. Деталі уточнюй у бариста.'
    return 'Фірмова позиція Medelin. Деталі уточнюй у бариста.'

def _build_menu_data() -> list[tuple]:
    overrides: dict[tuple[str, str], tuple] = {}
    for item in MENU_OVERRIDES:
        cat, name = (item[0], item[1])
        if _norm(cat) == 'матча':
            continue
        overrides[str(cat), _norm(name)] = item
    aliases = {('Кава', 'фільтр'): ('Кава', 'фільтр кава'), ('Кава', 'флет вайт'): ('Кава', 'флет вайт'), ('Кава', 'глясе'): ('Кава', 'глясе'), ('Напої', 'лимонад'): ('Напої', 'лимонад класичний')}
    menu: list[tuple] = []
    for category, items in MENU_SECTIONS:
        if _norm(category) == 'матча':
            continue
        for raw_name, price in items:
            name = str(raw_name).strip()
            key = (str(category), _norm(name))
            src = overrides.get(key)
            if not src and key in aliases:
                src = overrides.get(aliases[key])
            if src:
                cat, nm, _p, desc, vol, cal, strng, sweet, comp, _has_milk, _has_decaf, c_info = src
                menu.append((cat, name, str(price), desc, vol, cal, strng, sweet, comp, False, True if str(category) == 'Кава' else False, c_info))
                continue
            menu.append((str(category), name, str(int(price)), _guess_description(str(category), name), _guess_volume(str(category), name), _guess_calories(str(category), name), _guess_strength(str(category), name), _guess_sweetness(str(category), name), _guess_composition(str(category), name), False, True if str(category) == 'Кава' else False, None))
    return menu
MENU_DATA = _build_menu_data()
BEANS_OVERRIDES = [{'name': 'Індія Монсун Малабар', 'price_250': 271, 'sort': 'Арабіка 100%', 'roast': 'Середнє', 'taste': 'Мускатний горіх, спеції, шоколад, тютюнові ноти', 'description': 'Унікальна кава, що проходить обробку мусонними вітрами на узбережжі Індії. Має низьку кислотність та густе тіло.', 'country': 'Індія', 'altitude': '900-1200м', 'processing': 'Monsooned', 'acidity': 1, 'bitterness': 3, 'body': 5, 'variety': 'Kents, S.795', 'cup_score': '82', 'harvest': 'Жовтень - Лютий', 'recommendation': 'Ідеально для джезви та гейзерної кавоварки.'}, {'name': 'Ефіопія Йергачіф', 'price_250': 281, 'sort': 'Арабіка 100% (Specialty)', 'roast': 'Світло-середнє', 'taste': 'Бергамот, лимонна цедра, жасмин, чайні ноти', 'description': 'Класика африканської кави з яскравим квітковим ароматом та витонченою цитрусовою кислинкою.', 'country': 'Ефіопія', 'altitude': '1800-2100м', 'processing': 'Washed', 'acidity': 4, 'bitterness': 1, 'body': 2, 'variety': 'Heirloom', 'cup_score': '86.5', 'harvest': 'Листопад - Січень', 'recommendation': 'Найкраще розкривається у фільтрі та пуровері.'}, {'name': 'Бразилія Сантос', 'price_250': 235, 'sort': 'Арабіка 100%', 'roast': 'Середнє', 'taste': 'Смажений горіх, молочний шоколад, карамель', 'description': 'Найпопулярніша бразильська кава. Ідеально збалансований смак без зайвої кислотності.', 'country': 'Бразилія', 'altitude': '1100м', 'processing': 'Natural', 'acidity': 2, 'bitterness': 2, 'body': 3, 'variety': 'Bourbon, Catuai', 'cup_score': '81', 'harvest': 'Травень - Вересень', 'recommendation': 'Універсальний вибір для еспресо-машин.'}, {'name': 'Колумбія Ексельсо', 'price_250': 265, 'sort': 'Арабіка 100%', 'roast': 'Середнє', 'taste': 'Червоне яблуко, тростинний цукор, какао', 'description': 'Класична колумбійська кава з приємною фруктовою кислинкою та солодким післясмаком.', 'country': 'Колумбія', 'altitude': '1400-1600м', 'processing': 'Washed', 'acidity': 3, 'bitterness': 2, 'body': 3, 'variety': 'Caturra, Typica', 'cup_score': '83.5', 'harvest': 'Березень - Червень', 'recommendation': 'Чудово підходить для автоматичних кавомашин.'}, {'name': 'Італьяно (Купаж)', 'price_250': 210, 'sort': '80% Арабіка / 20% Робуста', 'roast': 'Темне', 'taste': 'Темний шоколад, підсмажений тост, стійка пінка', 'description': 'Авторська суміш для ідеального еспресо. Міцна, насичена та надзвичайно бадьора.', 'country': 'Blend', 'altitude': 'Різна', 'processing': 'Mixed', 'acidity': 1, 'bitterness': 4, 'body': 5, 'variety': 'Blend', 'cup_score': '78', 'harvest': 'Круглий рік', 'recommendation': 'Для тих, хто любить міцну каву з густою пінкою.'}]
BEANS_BASE = [{'name': 'Індія монсун малабар', 'price_250': 271}, {'name': 'Індія плантейшн', 'price_250': 245, 'price_1000': 781}, {'name': 'Італьяно', 'price_250': 205}, {'name': 'Ефіопія йергачіф', 'price_250': 281}, {'name': 'Ефіопія сідамо', 'price_250': 282}, {'name': 'Кенія кіліманджаро', 'price_250': 322}, {'name': 'Колумбія супремо', 'price_250': 261}, {'name': 'Мастермікс 250g', 'price_250': 218}, {'name': 'Мексика марагоджип', 'price_250': 348}, {'name': 'Преміум', 'price_250': 228}, {'name': 'Колумбія без кофеїну 250g', 'price_250': 271}, {'name': 'Нікарагуа 250g', 'price_250': 253}]

def _build_beans_data() -> list[dict]:
    overrides: dict[str, dict] = {_norm(b.get('name', '')): b for b in BEANS_OVERRIDES or []}

    def make_default(bean_name: str, price_250: int, *, price_1000: int | None=None) -> dict:
        return {'name': bean_name, 'price_250': int(price_250), 'price_1000': int(price_1000) if price_1000 else None, 'sort': 'Арабіка 100%', 'roast': 'Середнє', 'taste': 'Шоколад, горіх, карамель', 'description': 'Фірмові зерна Medelin. Деталі та наявність уточнюй у бариста.', 'country': '', 'altitude': '', 'processing': '', 'acidity': 2, 'bitterness': 2, 'body': 3, 'variety': '', 'cup_score': '', 'harvest': '', 'recommendation': 'Підійде для еспресо та альтернативи.'}
    beans: list[dict] = []
    seen: set[str] = set()
    for b in BEANS_BASE:
        name = str(b.get('name', '')).strip()
        key = _norm(name)
        if key in overrides:
            item = dict(overrides[key])
            item['price_250'] = int(b.get('price_250') or item.get('price_250') or 0)
            if b.get('price_1000'):
                item['price_1000'] = int(b.get('price_1000'))
            beans.append(item)
            seen.add(key)
        else:
            beans.append(make_default(name, int(b.get('price_250') or 0), price_1000=b.get('price_1000')))
            seen.add(key)
    for key, item in overrides.items():
        if key in seen:
            continue
        beans.append(dict(item))
    return beans
BEANS_DATA = _build_beans_data()
LOCATIONS_DATA = [{'name': 'Medelin (Корзо)', 'address': 'вул. Корзо, 15, Ужгород', 'schedule': 'Пн–Нд: 08:00 – 20:00', 'phone': '+38 (050) 377-59-06', 'email': 'medelin.social@gmail.com', 'coords': (48.6233102, 22.2981488), 'url': 'https://www.google.com/maps?q=48.6233102,22.2981488', 'tables': 12, 'img': PHOTO_URL_LOCATION, 'amenities': ['Безкоштовний Wi‑Fi', 'Багато розеток', 'Зручна робоча зона', 'Pet-friendly', 'Оплата карткою'], 'atmosphere': 'Затишна кавʼярня у центрі міста з фірмовою кавою та десертами. Зручно для зустрічей і роботи.'}, {'name': 'Medelin (Корятовича)', 'address': 'пл. Корятовича, 5А, Ужгород', 'schedule': 'Пн–Нд: 08:00 – 20:00', 'phone': '+38 (050) 377-59-06', 'email': 'medelin.social@gmail.com', 'coords': (48.6244831, 22.2982141), 'url': 'https://www.google.com/maps?q=48.6244831,22.2982141', 'tables': 12, 'img': PHOTO_URL_LOCATION, 'amenities': ['Безкоштовний Wi‑Fi', 'Багато розеток', 'Зручна робоча зона', 'Pet-friendly', 'Оплата карткою'], 'atmosphere': 'Класична локація Medelin з комфортною посадкою та швидким сервісом. Добре підходить для роботи й зустрічей.'}, {'name': 'Medelin (Петефі)', 'address': 'пл. Шандора Петефі, 5/2, Ужгород', 'schedule': 'Пн–Нд: 08:00 – 20:00', 'phone': '+38 (050) 377-59-06', 'email': 'medelin.social@gmail.com', 'coords': (48.6193363, 22.2974372), 'url': 'https://www.google.com/maps?q=48.6193363,22.2974372', 'tables': 10, 'img': PHOTO_URL_LOCATION, 'amenities': ['Безкоштовний Wi‑Fi', 'Багато розеток', 'Зручна робоча зона', 'Pet-friendly', 'Оплата карткою'], 'atmosphere': 'Світла міська кавʼярня з фірмовими напоями та десертами. Ідеально для короткої паузи в центрі.'}, {'name': 'Medelin (Свободи)', 'address': 'просп. Свободи, 55, Ужгород', 'schedule': 'Пн–Нд: 08:00 – 20:00', 'phone': '+38 (050) 377-59-06', 'email': 'medelin.social@gmail.com', 'coords': (48.6118144, 22.2957847), 'url': 'https://www.google.com/maps?q=48.6118144,22.2957847', 'tables': 10, 'img': PHOTO_URL_LOCATION, 'amenities': ['Безкоштовний Wi‑Fi', 'Багато розеток', 'Зручна робоча зона', 'Pet-friendly', 'Оплата карткою'], 'atmosphere': 'Зручна локація для кави з собою та швидких зустрічей. Є комфортні місця для роботи.'}, {'name': 'Medelin (Словʼянська набережна)', 'address': 'Словʼянська набережна, Ужгород', 'schedule': 'Пн–Нд: 08:00 – 20:00', 'phone': '+38 (050) 377-59-06', 'email': 'medelin.social@gmail.com', 'coords': (48.6193285, 22.2787497), 'url': 'https://www.google.com/maps?q=48.6193285,22.2787497', 'tables': 10, 'img': PHOTO_URL_LOCATION, 'amenities': ['Безкоштовний Wi‑Fi', 'Багато розеток', 'Зручна робоча зона', 'Pet-friendly', 'Оплата карткою'], 'atmosphere': 'Локація біля набережної для неспішної кави. Приємна атмосфера для відпочинку та прогулянок.'}, {'name': 'Medelin (Закарпатська)', 'address': 'вул. Закарпатська, 44, Ужгород', 'schedule': 'Пн–Нд: 08:00 – 20:00', 'phone': '+38 (050) 377-59-06', 'email': 'medelin.social@gmail.com', 'coords': (48.6319518, 22.278365), 'url': 'https://www.google.com/maps?q=48.6319518,22.2783650', 'tables': 10, 'img': PHOTO_URL_LOCATION, 'amenities': ['Безкоштовний Wi‑Fi', 'Багато розеток', 'Зручна робоча зона', 'Pet-friendly', 'Оплата карткою'], 'atmosphere': 'Затишна кавʼярня з великим вибором кави та десертів. Комфортно для зустрічей і роботи.'}, {'name': 'Medelin Кабінет (Гойди)', 'address': 'вул. Юрія Гойди, 10, Ужгород', 'schedule': 'Пн–Пт: 08:00 – 20:00, Сб–Нд: 09:00 – 19:00', 'phone': '+38 (050) 377-59-06', 'email': 'kabinet@medelin.ua', 'coords': (48.6272962, 22.2905275), 'url': 'https://www.google.com/maps?q=48.6272962,22.2905275', 'tables': 12, 'img': PHOTO_URL_LOCATION, 'amenities': ['Швидкий Wi‑Fi', 'Багато розеток', 'Тиха атмосфера', 'Ідеально для роботи', 'Кондиціонер'], 'atmosphere': 'Тихий простір для продуктивної роботи та зустрічей. Продумана ергономіка і спокійна атмосфера.'}]
SOCIALS_DATA = [{'name': 'Instagram', 'url': 'https://www.instagram.com/medelin_uzh/'}, {'name': 'Facebook', 'url': 'https://www.facebook.com/medelin.coffee/'}, {'name': 'Telegram', 'url': 'https://t.me/medelin_bot'}, {'name': 'Website', 'url': 'https://medelin.com/'}]

async def seed():
    await menu_db.connect()
    await coffee_beans_db.connect()
    await location_db.connect()
    await socials_db.connect()
    await menu_db.clear_menu()
    await coffee_beans_db.clear_beans()
    await location_db.clear_locations()
    await socials_db.clear_socials()
    for item in MENU_DATA:
        cat, name, price, desc, vol, cal, strng, sweet, comp, has_milk, has_decaf, c_info = item
        opts = []
        if has_decaf:
            opts.extend(CAFFEINE_OPTIONS)
        if has_milk:
            opts.extend(MILK_OPTIONS)
        if cat == 'Кава':
            opts.extend(ADDON_OPTIONS)
        c_country, c_altitude, c_sort, c_proc, c_roast, c_taste = ('', '', '', '', '', '')
        if c_info:
            c_country, c_altitude, c_sort, c_proc, c_roast, c_taste = c_info
        await menu_db.add_item(category=cat, name=name, price=price, description=desc, volume=vol, calories=cal, image_url=PHOTO_URL_MENU, strength=STR_MAP.get(strng, 0), sweetness=SWEET_MAP.get(sweet, 0), composition=comp, options=opts, country=c_country, altitude=c_altitude, sort=c_sort, processing=c_proc, roast=c_roast, taste=c_taste)
    for b in BEANS_DATA:
        await coffee_beans_db.add_bean(name=b['name'], price_250=b['price_250'], description=b['description'], sort=b['sort'], taste=b['taste'], roast=b['roast'], image_url=PHOTO_URL_BEANS, country=b['country'], altitude=b['altitude'], processing=b['processing'], acidity=b['acidity'], bitterness=b['bitterness'], body=b['body'], variety=b['variety'], cup_score=b['cup_score'], harvest=b['harvest'], recommendation=b['recommendation'])
    for l in LOCATIONS_DATA:
        await location_db.add_location(name=l['name'], address=l['address'], schedule=l['schedule'], phone=l['phone'], email=l['email'], google_maps_url=l['url'], coordinates={'lat': l['coords'][0], 'lon': l['coords'][1]}, max_tables=l['tables'], image_url=l['img'], amenities=l.get('amenities', []), atmosphere=l.get('atmosphere', ''))
    for s in SOCIALS_DATA:
        await socials_db.add_social(s['name'], s['url'])
    await close_client()
if __name__ == '__main__':
    asyncio.run(seed())
