import asyncio
import sys
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parents[1]
if str(ROOT_DIR) not in sys.path:
    sys.path.append(str(ROOT_DIR))

from app.databases.coffee_beans_database import coffee_beans_db
from app.databases.location_database import location_db
from app.databases.contacts_database import contacts_db
from app.databases.mongo_client import close_client

PHOTO_URL_BEANS = 'https://images.pexels.com/photos/1695052/pexels-photo-1695052.jpeg?auto=compress&cs=tinysrgb&w=800'
PHOTO_URL_LOCATION = 'https://images.pexels.com/photos/2615323/pexels-photo-2615323.jpeg?auto=compress&cs=tinysrgb&w=800'

def _norm(s: str) -> str:
    return ' '.join(str(s or '').strip().split()).casefold()

BEANS_DATA = [
    {
        'name': 'Індія Монсун Малабар',
        'price_250': 271,
        'species': 'Арабіка 100%',
        'roast': 'Середнє',
        'taste': 'Мускатний горіх, спеції, шоколад, тютюнові ноти',
        'description': 'Унікальна кава, що проходить обробку мусонними вітрами на узбережжі Індії. Має низьку кислотність та густе тіло.',
        'country': 'Індія',
        'altitude': '900-1200м',
        'processing': 'Monsooned',
        'descriptors': 'Спеції, горіх, тютюн',
        'acidity': 1, 'bitterness': 3, 'body': 5,
        'variety': 'Kents, S.795',
        'cup_score': '82',
        'harvest': 'Жовтень - Лютий',
        'recommendation': 'Ідеально для джезви та гейзерної кавоварки.',
        'region': 'Malabar Coast',
        'station': 'Local smallholders'
    },
    {
        'name': 'Ефіопія Йергачіф',
        'price_250': 281,
        'species': 'Арабіка 100% (Specialty)',
        'roast': 'Світло-середнє',
        'taste': 'Бергамот, лимонна цедра, жасмин, чайні ноти',
        'description': 'Класика африканської кави з яскравим квітковим ароматом та витонченою цитрусовою кислинкою.',
        'country': 'Ефіопія',
        'altitude': '1800-2100м',
        'processing': 'Washed',
        'descriptors': 'Цитрус, квіти, бергамот',
        'acidity': 4, 'bitterness': 1, 'body': 2,
        'variety': 'Heirloom',
        'cup_score': '86.5',
        'harvest': 'Листопад - Січень',
        'recommendation': 'Найкраще розкривається у фільтрі та пуровері.',
        'region': 'Yirgacheffe',
        'station': 'Koke station'
    },
    {
        'name': 'Бразилія Сантос',
        'price_250': 235,
        'species': 'Арабіка 100%',
        'roast': 'Середнє',
        'taste': 'Смажений горіх, молочний шоколад, карамель',
        'description': 'Найпопулярніша бразильська кава. Ідеально збалансований смак без зайвої кислотності.',
        'country': 'Бразилія',
        'altitude': '1100м',
        'processing': 'Natural',
        'descriptors': 'Горіх, шоколад, карамель',
        'acidity': 2, 'bitterness': 2, 'body': 3,
        'variety': 'Bourbon, Catuai',
        'cup_score': '81',
        'harvest': 'Травень - Вересень',
        'recommendation': 'Універсальний вибір для еспресо-машин.',
        'region': 'Sul de Minas',
        'station': 'Santos port'
    },
    {
        'name': 'Колумбія Ексельсо',
        'price_250': 265,
        'species': 'Арабіка 100%',
        'roast': 'Середнє',
        'taste': 'Червоне яблуко, тростинний цукор, какао',
        'description': 'Класична колумбійська кава з приємною фруктовою кислинкою та солодким післясмаком.',
        'country': 'Колумбія',
        'altitude': '1400-1600м',
        'processing': 'Washed',
        'descriptors': 'Яблуко, карамель, какао',
        'acidity': 3, 'bitterness': 2, 'body': 3,
        'variety': 'Caturra, Typica',
        'cup_score': '83.5',
        'harvest': 'Березень - Червень',
        'recommendation': 'Чудово підходить для автоматичних кавомашин.',
        'region': 'Huila',
        'station': 'Cooperative'
    },
    {
        'name': 'Італьяно (Купаж)',
        'price_250': 210,
        'species': '80% Арабіка / 20% Робуста',
        'roast': 'Темне',
        'taste': 'Темний шоколад, підсмажений тост, стійка пінка',
        'description': 'Авторська суміш для ідеального еспресо. Міцна, насичена та надзвичайно бадьора.',
        'country': 'Blend',
        'altitude': 'Різна',
        'processing': 'Mixed',
        'descriptors': 'Шоколад, тост, міцність',
        'acidity': 1, 'bitterness': 4, 'body': 5,
        'variety': 'Blend',
        'cup_score': '78',
        'harvest': 'Круглий рік',
        'recommendation': 'Для тих, хто любить міцну каву з густою пінкою.',
        'region': 'Global',
        'station': 'Medelin Roastery'
    },
    {
        'name': 'Ефіопія Сідамо',
        'price_250': 282,
        'species': 'Арабіка 100%',
        'roast': 'Середнє',
        'taste': 'Чорний чай, лимон, абрикос',
        'description': 'М’яка африканська кава з приємним фруктовим профілем та чайним тілом.',
        'country': 'Ефіопія',
        'altitude': '1500-1800м',
        'processing': 'Washed',
        'descriptors': 'Чай, лимон, абрикос',
        'acidity': 3, 'bitterness': 1, 'body': 2,
        'variety': 'Heirloom',
        'cup_score': '84',
        'harvest': 'Листопад - Січень',
        'recommendation': 'Для любителів м’якої кави.',
        'region': 'Sidamo',
        'station': 'Local'
    },
    {
        'name': 'Кенія Кіліманджаро',
        'price_250': 322,
        'species': 'Арабіка 100%',
        'roast': 'Світло-середнє',
        'taste': 'Чорна смородина, виноград, висока кислотність',
        'description': 'Яскрава та соковита кава з Кенії. Висока кислотність та складний смаковий профіль.',
        'country': 'Кенія',
        'altitude': '1700-1900м',
        'processing': 'Washed',
        'descriptors': 'Смородина, виноград',
        'acidity': 5, 'bitterness': 1, 'body': 3,
        'variety': 'SL28, SL34',
        'cup_score': '87',
        'harvest': 'Жовтень - Грудень',
        'recommendation': 'Тільки для справжніх цінителів кислотності.',
        'region': 'Mount Kenya',
        'station': 'Processing Station'
    },
    {
        'name': 'Мексика Марагоджип',
        'price_250': 348,
        'species': 'Арабіка 100% (Марагоджип)',
        'roast': 'Середнє',
        'taste': 'Шоколад, прянощі, велике зерно',
        'description': 'Легендарні "слонові зерна". Величезний розмір та м’який, збалансований шоколадний смак.',
        'country': 'Мексика',
        'altitude': '1200-1500м',
        'processing': 'Washed',
        'descriptors': 'Шоколад, прянощі',
        'acidity': 2, 'bitterness': 2, 'body': 3,
        'variety': 'Maragogype',
        'cup_score': '83',
        'harvest': 'Грудень - Березень',
        'recommendation': 'Ідеально на подарунок через розмір зерен.',
        'region': 'Chiapas',
        'station': 'Finca'
    },
    {
        'name': 'Нікарагуа',
        'price_250': 253,
        'species': 'Арабіка 100%',
        'roast': 'Середнє',
        'taste': 'Тропічні фрукти, карамель, горіх',
        'description': 'Солодка кава з Нікарагуа. Має приємні фруктові ноти та довгий горіховий післясмак.',
        'country': 'Нікарагуа',
        'altitude': '1100-1400м',
        'processing': 'Natural',
        'descriptors': 'Фрукти, карамель',
        'acidity': 3, 'bitterness': 2, 'body': 3,
        'variety': 'Caturra',
        'cup_score': '82.5',
        'harvest': 'Січень - Березень',
        'recommendation': 'Добре смакує як з молоком, так і без.',
        'region': 'Jinotega',
        'station': 'Coop'
    }
]

LOCATIONS_DATA = [
    {'name': 'Medelin (Корзо)', 'address': 'вул. Корзо, 15, Ужгород', 'schedule': 'Пн–Нд: 08:00 – 20:00', 'phone': '+38 (050) 377-59-06', 'email': 'medelin.social@gmail.com', 'coords': (48.6233102, 22.2981488), 'url': 'https://www.google.com/maps?q=48.6233102,22.2981488', 'tables': 12, 'img': PHOTO_URL_LOCATION, 'amenities': ['Безкоштовний Wi‑Fi', 'Багато розеток', 'Зручна робоча зона', 'Pet-friendly', 'Оплата карткою'], 'atmosphere': 'Затишна кавʼярня у центрі міста з фірмовою кавою та десертами. Зручно для зустрічей і роботи.'},
    {'name': 'Medelin (Корятовича)', 'address': 'пл. Корятовича, 5А, Ужгород', 'schedule': 'Пн–Нд: 08:00 – 20:00', 'phone': '+38 (050) 377-59-06', 'email': 'medelin.social@gmail.com', 'coords': (48.6244831, 22.2982141), 'url': 'https://www.google.com/maps?q=48.6244831,22.2982141', 'tables': 12, 'img': PHOTO_URL_LOCATION, 'amenities': ['Безкоштовний Wi‑Fi', 'Багато розеток', 'Зручна робоча зона', 'Pet-friendly', 'Оплата карткою'], 'atmosphere': 'Класична локація Medelin з комфортною посадкою та швидким сервісом. Добре підходить для роботи й зустрічей.'},
    {'name': 'Medelin (Петефі)', 'address': 'пл. Шандора Петефі, 5/2, Ужгород', 'schedule': 'Пн–Нд: 08:00 – 20:00', 'phone': '+38 (050) 377-59-06', 'email': 'medelin.social@gmail.com', 'coords': (48.6193363, 22.2974372), 'url': 'https://www.google.com/maps?q=48.6193363,22.2974372', 'tables': 10, 'img': PHOTO_URL_LOCATION, 'amenities': ['Безкоштовний Wi‑Fi', 'Багато розеток', 'Зручна робоча зона', 'Pet-friendly', 'Оплата карткою'], 'atmosphere': 'Світла міська кавʼярня з фірмовими напоями та десертами. Ідеально для короткої паузи в центрі.'},
    {'name': 'Medelin (Свободи)', 'address': 'просп. Свободи, 55, Ужгород', 'schedule': 'Пн–Нд: 08:00 – 20:00', 'phone': '+38 (050) 377-59-06', 'email': 'medelin.social@gmail.com', 'coords': (48.6118144, 22.2957847), 'url': 'https://www.google.com/maps?q=48.6118144,22.2957847', 'tables': 10, 'img': PHOTO_URL_LOCATION, 'amenities': ['Безкоштовний Wi‑Fi', 'Багато розеток', 'Зручна робоча зона', 'Pet-friendly', 'Оплата карткою'], 'atmosphere': 'Зручна локація для кави з собою та швидких зустрічей. Є комфортні місця для роботи.'},
    {'name': 'Medelin (Словʼянська набережна)', 'address': 'Словʼянська набережна, Ужгород', 'schedule': 'Пн–Нд: 08:00 – 20:00', 'phone': '+38 (050) 377-59-06', 'email': 'medelin.social@gmail.com', 'coords': (48.6193285, 22.2787497), 'url': 'https://www.google.com/maps?q=48.6193285,22.2787497', 'tables': 10, 'img': PHOTO_URL_LOCATION, 'amenities': ['Безкоштовний Wi‑Fi', 'Багато розеток', 'Зручна робоча зона', 'Pet-friendly', 'Оплата карткою'], 'atmosphere': 'Локація біля набережної для неспішної кави. Приємна атмосфера для відпочинку та прогулянок.'},
    {'name': 'Medelin (Закарпатська)', 'address': 'вул. Закарпатська, 44, Ужгород', 'schedule': 'Пн–Нд: 08:00 – 20:00', 'phone': '+38 (050) 377-59-06', 'email': 'medelin.social@gmail.com', 'coords': (48.6319518, 22.278365), 'url': 'https://www.google.com/maps?q=48.6319518,22.2783650', 'tables': 10, 'img': PHOTO_URL_LOCATION, 'amenities': ['Безкоштовний Wi‑Fi', 'Багато розеток', 'Зручна робоча зона', 'Pet-friendly', 'Оплата карткою'], 'atmosphere': 'Затишна кавʼярня з великим вибором кави та десертів. Комфортно для зустрічей і роботи.'},
    {'name': 'Medelin Кабінет (Гойди)', 'address': 'вул. Юрія Гойди, 10, Ужгород', 'schedule': 'Пн–Пт: 08:00 – 20:00, Сб–Нд: 09:00 – 19:00', 'phone': '+38 (050) 377-59-06', 'email': 'kabinet@medelin.ua', 'coords': (48.6272962, 22.2905275), 'url': 'https://www.google.com/maps?q=48.6272962,22.2905275', 'tables': 12, 'img': PHOTO_URL_LOCATION, 'amenities': ['Швидкий Wi‑Fi', 'Багато розеток', 'Тиха атмосфера', 'Ідеально для роботи', 'Кондиціонер'], 'atmosphere': 'Тихий простір для продуктивної роботи та зустрічей. Продумана ергономіка і спокійна атмосфера.'}
]

SOCIALS_DATA = [
    {'name': 'Instagram', 'url': 'https://www.instagram.com/medelin_uzh/'},
    {'name': 'Facebook', 'url': 'https://www.facebook.com/medelin.coffee/'},
    {'name': 'Telegram', 'url': 'https://t.me/medelin_bot'},
    {'name': 'Website', 'url': 'https://medelin.com/'}
]

async def seed():
    await coffee_beans_db.connect()
    await location_db.connect()
    await contacts_db.connect()

    await coffee_beans_db.clear_beans()
    await location_db.clear_locations()
    await contacts_db.clear_contacts()

    for b in BEANS_DATA:
        await coffee_beans_db.add_bean(
            name=b['name'], 
            price_250=b['price_250'], 
            description=b['description'], 
            species=b['species'], 
            taste=b['taste'], 
            roast=b['roast'], 
            image_url=PHOTO_URL_BEANS, 
            country=b['country'], 
            altitude=b['altitude'], 
            processing=b['processing'], 
            descriptors=b.get('descriptors', ''),
            acidity=b['acidity'], 
            bitterness=b['bitterness'], 
            body=b['body'], 
            variety=b['variety'], 
            cup_score=b['cup_score'], 
            harvest=b['harvest'], 
            recommendation=b['recommendation'],
            region=b.get('region', ''),
            station=b.get('station', '')
        )

    for l in LOCATIONS_DATA:
        await location_db.add_location(
            name=l['name'], address=l['address'], schedule=l['schedule'], 
            phone=l['phone'], email=l['email'], google_maps_url=l['url'], 
            coordinates={'lat': l['coords'][0], 'lon': l['coords'][1]}, 
            max_tables=l['tables'], image_url=l['img'], 
            amenities=l.get('amenities', []), atmosphere=l.get('atmosphere', '')
        )
    
    for s in SOCIALS_DATA:
        await contacts_db.add_contact(s['name'], s['url'])
        
    await close_client()

if __name__ == '__main__':
    asyncio.run(seed())
