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

PHOTO_URL_BEANS = 'https://images.unsplash.com/photo-1685798830559-c116586a0d33?q=80&w=687&auto=format&fit=crop&ixlib=rb-4.1.0&ixid=M3wxMjA3fDB8MHxwaG90by1wYWdlfHx8fGVufDB8fHx8fA%3D%3D'
PHOTO_URL_LOCATION = 'https://images.unsplash.com/photo-1555396273-367ea4eb4db5?q=80&w=1074&auto=format&fit=crop&ixlib=rb-4.1.0&ixid=M3wxMjA3fDB8MHxwaG90by1wYWdlfHx8fGVufDB8fHx8fA%3D%3D'

def _norm(s: str) -> str:
    return ' '.join(str(s or '').strip().split()).casefold()

BEANS_DATA = [

    {
        'name': 'Бразилія Сантос',
        'price_250': 235,
        'species': 'Арабіка 100%',
        'roast': 'Espresso',
        'taste': 'Горіх, молочний шоколад, карамель',
        'description': 'Класична бразильська кава з м\'яким горіховим смаком та низькою кислотністю.',
        'altitude': '1100м',
        'processing': 'Natural',
        'descriptors': 'Горіх, шоколад, карамель',
        'variety': 'Bourbon, Catuai',
        'quality_score': '',
        'harvest': '2023/24'
    },
    {
        'name': 'Ефіопія Джимма',
        'price_250': 245,
        'species': 'Арабіка 100%',
        'roast': 'Espresso',
        'taste': 'Винні ноти, чорний шоколад, прянощі',
        'description': 'Традиційна ефіопська кава сухої обробки з диким, насиченим профілем.',
        'altitude': '1400-1800м',
        'processing': 'Natural',
        'descriptors': 'Вино, шоколад, спеції',
        'variety': 'Heirloom',
        'quality_score': '',
        'harvest': '2023/24'
    },
    {
        'name': 'Колумбія Супремо',
        'price_250': 260,
        'species': 'Арабіка 100%',
        'roast': 'Espresso',
        'taste': 'Червоне яблуко, тростинний цукор, какао',
        'description': 'Збалансована кава з великим зерном та приємною фруктовою солодкістю.',
        'altitude': '1500-1800м',
        'processing': 'Washed',
        'descriptors': 'Яблуко, карамель, какао',
        'variety': 'Caturra, Typica',
        'quality_score': '',
        'harvest': '2024'
    },
    {
        'name': 'Гватемала Антигуа',
        'price_250': 275,
        'species': 'Арабіка 100%',
        'roast': 'Espresso',
        'taste': 'Дика роза, молочний шоколад, димні ноти',
        'description': 'Вулканічний грунт Антигуа надає цій каві неповторну глибину та складність.',
        'altitude': '1500-1700м',
        'processing': 'Washed',
        'descriptors': 'Шоколад, дим, квіти',
        'variety': 'Bourbon, Catuai',
        'quality_score': '',
        'harvest': '2024'
    },
    {
        'name': 'Гондурас Маркала',
        'price_250': 240,
        'species': 'Арабіка 100%',
        'roast': 'Espresso',
        'taste': 'Фундук, карамель, темні ягоди',
        'description': 'М\'яка кава з вираженою солодкістю та легким ягідним післясмаком.',
        'altitude': '1300-1700м',
        'processing': 'Washed',
        'descriptors': 'Горіх, ягоди, карамель',
        'variety': 'Catuai, Pacas',
        'quality_score': '',
        'harvest': '2023'
    },
    {
        'name': 'Сальвадор SHG',
        'price_250': 255,
        'species': 'Арабіка 100%',
        'roast': 'Espresso',
        'taste': 'Мед, мигдаль, молочний шоколад',
        'description': 'Кава з високогірних плантацій Сальвадору, дуже солодка та чиста.',
        'altitude': '1350м',
        'processing': 'Washed',
        'descriptors': 'Мед, мигдаль, шоколад',
        'variety': 'Bourbon',
        'quality_score': '',
        'harvest': '2024'
    },
    {
        'name': 'Індія Монсун Малабар',
        'price_250': 270,
        'species': 'Арабіка 100%',
        'roast': 'Espresso',
        'taste': 'Мускатний горіх, спеції, шоколад',
        'description': 'Унікальна кава з низькою кислотністю та мусонною обробкою.',
        'altitude': '1100-1200м',
        'processing': 'Monsooned',
        'descriptors': 'Спеції, горіх, тютюн',
        'variety': 'Kents',
        'quality_score': '',
        'harvest': '2023'
    },
    {
        'name': 'В\'єтнам Далат',
        'price_250': 225,
        'species': 'Арабіка 100%',
        'roast': 'Espresso',
        'taste': 'Прянощі, темний шоколад, кедр',
        'description': 'Насичена в\'єтнамська арабіка з гірського району Далат.',
        'altitude': '1400-1600м',
        'processing': 'Washed',
        'descriptors': 'Шоколад, прянощі, дерево',
        'variety': 'Catimor',
        'quality_score': '',
        'harvest': '2024'
    },
    {
        'name': 'Уганда Другар',
        'price_250': 215,
        'species': 'Арабіка 100%',
        'roast': 'Espresso',
        'taste': 'Сухофрукти, какао, житній хліб',
        'description': 'Тілиста та міцна кава з природною обробкою з передгір\'я Рувензорі.',
        'altitude': '1300-1600м',
        'processing': 'Natural',
        'descriptors': 'Какао, сухофрукти, хліб',
        'variety': 'Heirloom SL14, SL28',
        'quality_score': '',
        'harvest': '2023/24'
    },
    {
        'name': 'Перу HB',
        'price_250': 250,
        'species': 'Арабіка 100%',
        'roast': 'Espresso',
        'taste': 'Грецький горіх, чорний чай, карамель',
        'description': 'Класичний перуанський профіль: м\'який, солодкий та збалансований.',
        'altitude': '1200-1500м',
        'processing': 'Washed',
        'descriptors': 'Горіх, чай, карамель',
        'variety': 'Typica, Bourbon',
        'quality_score': '',
        'harvest': '2024'
    },
    {
        'name': 'Мексика SHG',
        'price_250': 245,
        'species': 'Арабіка 100%',
        'roast': 'Espresso',
        'taste': 'Кориця, коричневий цукор, яблуко',
        'description': 'Легка та солодка кава з м\'яким тілом та делікатним смаком.',
        'altitude': '1200-1400м',
        'processing': 'Washed',
        'descriptors': 'Кориця, цукор, яблуко',
        'variety': 'Caturra, Typica',
        'quality_score': '',
        'harvest': '2024'
    },
    {
        'name': 'Італьяно (Blend)',
        'price_250': 210,
        'species': '80% Арабіка / 20% Робуста',
        'roast': 'Espresso',
        'taste': 'Темний шоколад, підсмажений тост, горіх',
        'description': 'Фірмовий купаж для тих, хто любить міцну та ароматну каву з густою пінкою.',
        'altitude': 'Mixed',
        'processing': 'Mixed',
        'descriptors': 'Шоколад, тост, міцність',
        'variety': 'Blend',
        'quality_score': '',
        'harvest': '2024'
    },
    {
        'name': 'Ранкова Свіжість (Blend)',
        'price_250': 200,
        'species': '50% Арабіка / 50% Робуста',
        'roast': 'Espresso',
        'taste': 'Спеції, гіркий шоколад, карамель',
        'description': 'Дуже міцна кава з високим вмістом кофеїну. Ідеальний початок дня.',
        'altitude': 'Mixed',
        'processing': 'Mixed',
        'descriptors': 'Шоколад, спеції, енергія',
        'variety': 'Blend',
        'quality_score': '',
        'harvest': '2024'
    },
    {
        'name': 'Коста-Ріка Таразу',
        'price_250': 280,
        'species': 'Арабіка 100%',
        'roast': 'Espresso',
        'taste': 'Цитрусові, молочний шоколад, тростинний цукор',
        'description': 'Яскрава кава з високим рівнем кислотності та чистим смаком.',
        'altitude': '1400-1700м',
        'processing': 'Washed',
        'descriptors': 'Цитрус, шоколад, цукор',
        'variety': 'Caturra, Catuai',
        'quality_score': '',
        'harvest': '2024'
    },
    {
        'name': 'Нікарагуа SHG',
        'price_250': 250,
        'species': 'Арабіка 100%',
        'roast': 'Espresso',
        'taste': 'Чорний шоколад, ваніль, лісовий горіх',
        'description': 'Класична нікарагуанська кава з щільним тілом та солодким фінішем.',
        'altitude': '1200-1400м',
        'processing': 'Washed',
        'descriptors': 'Шоколад, ваніль, горіх',
        'variety': 'Caturra, Bourbon',
        'quality_score': '',
        'harvest': '2024'
    },

    {
        'name': 'Ефіопія Гуджі (Specialty)',
        'price_250': 340,
        'species': 'Арабіка 100%',
        'roast': 'Espresso',
        'taste': 'Суниця, бергамот, молочний шоколад',
        'description': 'Светла спешелті кава з яскравим фруктовим профілем та квітковим ароматом.',
        'altitude': '1900-2100м',
        'processing': 'Natural',
        'descriptors': 'Суниця, бергамот, шоколад',
        'variety': 'Heirloom',
        'quality_score': '86.5',
        'harvest': '2024'
    },
    {
        'name': 'Колумбія Піко Крістобаль',
        'price_250': 320,
        'species': 'Арабіка 100%',
        'roast': 'Espresso',
        'taste': 'Червоні ягоди, карамель, темний шоколад',
        'description': 'Високогірна Колумбія з глибоким смаком та соковитою кислотністю.',
        'altitude': '1700-1900м',
        'processing': 'Washed',
        'descriptors': 'Ягоди, карамель, шоколад',
        'variety': 'Caturra, Castillo',
        'quality_score': '85',
        'harvest': '2024'
    },
    {
        'name': 'Кенія АА (Specialty)',
        'price_250': 380,
        'species': 'Арабіка 100%',
        'roast': 'Espresso',
        'taste': 'Чорна смородина, грейпфрут, червоне вино',
        'description': 'Найвищий грейд кенійської кави. Потужна кислотність та надзвичайна складність.',
        'altitude': '1700-1900м',
        'processing': 'Washed',
        'descriptors': 'Смородина, грейпфрут, вино',
        'variety': 'SL28, SL34',
        'quality_score': '88',
        'harvest': '2024'
    },
    {
        'name': 'Панама Букете',
        'price_250': 350,
        'species': 'Арабіка 100%',
        'roast': 'Espresso',
        'taste': 'Жасмин, мандарин, зелений чай',
        'description': 'Елегантна та легка кава з витонченими квітковими нотами.',
        'altitude': '1600-1800м',
        'processing': 'Washed',
        'descriptors': 'Жасмин, мандарин, чай',
        'variety': 'Caturra, Typica',
        'quality_score': '86',
        'harvest': '2024'
    },
    {
        'name': 'Руанда Мусаса',
        'price_250': 330,
        'species': 'Арабіка 100%',
        'roast': 'Espresso',
        'taste': 'Меліса, червоне яблуко, карамель',
        'description': 'Чиста та солодка кава з цікавим трав\'янистим відтінком.',
        'altitude': '1800-2000м',
        'processing': 'Washed',
        'descriptors': 'Меліса, яблуко, карамель',
        'variety': 'Bourbon',
        'quality_score': '84.5',
        'harvest': '2024'
    },
    {
        'name': 'Ель-Сальвадор Пакамара',
        'price_250': 410,
        'species': 'Арабіка 100%',
        'roast': 'Espresso',
        'taste': 'Тропічні фрукти, мед, какао',
        'description': 'Крупне зерно різновиду Пакамара дає неймовірний букет тропічних смаків.',
        'altitude': '1500-1700м',
        'processing': 'Honey',
        'descriptors': 'Фрукти, мед, какао',
        'variety': 'Pacamara',
        'quality_score': '87',
        'harvest': '2024'
    },

    {
        'name': 'Ефіопія Йергачіф (Filter)',
        'price_250': 360,
        'species': 'Арабіка 100%',
        'roast': 'Filter',
        'taste': 'Лимонна цедра, жасмин, чайні ноти',
        'description': 'Класичний представник митої Ефіопії. Дуже чайна, ароматна та легка.',
        'altitude': '1800-2100м',
        'processing': 'Washed',
        'descriptors': 'Цитрус, квіти, чай',
        'variety': 'Heirloom',
        'quality_score': '87.5',
        'harvest': '2023/24'
    },
    {
        'name': 'Колумбія Анаеробна (Filter)',
        'price_250': 450,
        'species': 'Арабіка 100%',
        'roast': 'Filter',
        'taste': 'Маракуйя, манго, йогурт, спеції',
        'description': 'Кава з 72-годинною анаеробною ферментацією. Вибух смаку!',
        'altitude': '1800м',
        'processing': 'Anaerobic',
        'descriptors': 'Маракуйя, манго, фермент',
        'variety': 'Castillo',
        'quality_score': '89',
        'harvest': '2024'
    },
    {
        'name': 'Кенія Тіріку (Filter)',
        'price_250': 390,
        'species': 'Арабіка 100%',
        'roast': 'Filter',
        'taste': 'Томати, ревінь, журавлина',
        'description': 'Типова кенійська кислотність з незвичайними овочевими та ягідними нотами.',
        'altitude': '1850м',
        'processing': 'Washed',
        'descriptors': 'Томати, ревінь, ягоди',
        'variety': 'SL28',
        'quality_score': '86.5',
        'harvest': '2024'
    },
    {
        'name': 'Бурунді Кайанза',
        'price_250': 340,
        'species': 'Арабіка 100%',
        'roast': 'Filter',
        'taste': 'Апельсин, чорний чай, спеції',
        'description': 'Збалансована африканська кава з приємною цитрусовою солодкістю.',
        'altitude': '1700-1900м',
        'processing': 'Washed',
        'descriptors': 'Апельсин, чай, спеції',
        'variety': 'Red Bourbon',
        'quality_score': '85.5',
        'harvest': '2024'
    },
    {
        'name': 'Коста-Ріка Канела',
        'price_250': 420,
        'species': 'Арабіка 100%',
        'roast': 'Filter',
        'taste': 'Кориця, яблучний пиріг, карамель',
        'description': 'Обробка, що підкреслює пряні ноти кориці в смаку. Дуже затишна кава.',
        'altitude': '1600м',
        'processing': 'Cinnamon Process',
        'descriptors': 'Кориця, яблуко, карамель',
        'variety': 'Caturra',
        'quality_score': '87',
        'harvest': '2024'
    },
    {
        'name': 'Ефіопія Сидамо (Filter)',
        'price_250': 330,
        'species': 'Арабіка 100%',
        'roast': 'Filter',
        'taste': 'Персик, чорниця, молочний шоколад',
        'description': 'М\'яка та солодка кава натуральної обробки з ягідним профілем.',
        'altitude': '1700-1900м',
        'processing': 'Natural',
        'descriptors': 'Персик, чорниця, шоколад',
        'variety': 'Heirloom',
        'quality_score': '85.5',
        'harvest': '2024'
    },
]

LOCATIONS_DATA = [
    {'name': 'Medelin на Корятовича', 'address': 'пл. Корятовича, 5, Ужгород', 'schedule': 'Пн–Нд: 08:00 – 19:00',
     'coords': (48.62538364323062, 22.298050477352465), 'url': 'https://maps.app.goo.gl/9XpWHWgnYnUHt4348',
     'img': PHOTO_URL_LOCATION,
     'amenities': ['Безкоштовний Wi‑Fi', 'Багато розеток', 'Зручна робоча зона', 'Pet-friendly', 'Оплата карткою'],
     'atmosphere': 'Класична локація Medelin з комфортною посадкою та швидким сервісом. Добре підходить для роботи й зустрічей.'},
    {'name': 'Medelin на Закарпатській', 'address': 'вул. Закарпатська, 44, Ужгород',
     'schedule': 'Пн–Нд: 08:00 – 20:00',
     'coords': (48.633559654109824, 22.277708453416906), 'url': 'https://maps.app.goo.gl/CwpbgANPg8wVCFUU8',
     'img': PHOTO_URL_LOCATION,
     'amenities': ['Безкоштовний Wi‑Fi', 'Багато розеток', 'Зручна робоча зона', 'Pet-friendly', 'Оплата карткою'],
     'atmosphere': 'Класична локація Medelin з комфортною посадкою та швидким сервісом. Добре підходить для роботи й зустрічей.'},
    {'name': 'Medelin "Кабінет', 'address': 'вул. Гойди, 10, Ужгород', 'schedule': 'Пн–Нд: 08:00 – 19:00',
     'coords': (48.629018203803916, 22.287751077097603),
     'url': 'https://maps.app.goo.gl/BE2cRUdy3DE2FNBP7', 'img': PHOTO_URL_LOCATION,
     'amenities': ['Безкоштовний Wi‑Fi', 'Багато розеток', 'Зручна робоча зона', 'Pet-friendly', 'Оплата карткою'],
     'atmosphere': 'Класична локація Medelin з комфортною посадкою та швидким сервісом. Добре підходить для роботи й зустрічей.'},
    {'name': 'Medelin на Слов\'янській набережній', 'address': 'Слов\'янська набережна, Ужгород',
     'schedule': 'Пн–Нд: 08:00 – 20:00',
     'coords': (48.6186250051158, 22.263607041534797),
     'url': 'https://maps.app.goo.gl/Pr29moHWRyQEAzxo7', 'img': PHOTO_URL_LOCATION,
     'amenities': ['Безкоштовний Wi‑Fi', 'Багато розеток', 'Зручна робоча зона', 'Pet-friendly', 'Оплата карткою'],
     'atmosphere': 'Класична локація Medelin з комфортною посадкою та швидким сервісом. Добре підходить для роботи й зустрічей.'},
    {'name': 'Medelin на просп. Свободи', 'address': 'просп. Свободи, 55, Ужгород',
     'schedule': 'Пн–Нд: 08:00 – 19:00',
     'coords': (48.61389881661599, 22.295518001230366),
     'url': 'https://maps.app.goo.gl/bMyoKZ61CW158JGA8', 'img': PHOTO_URL_LOCATION,
     'amenities': ['Безкоштовний Wi‑Fi', 'Багато розеток', 'Зручна робоча зона', 'Pet-friendly', 'Оплата карткою'],
     'atmosphere': 'Класична локація Medelin з комфортною посадкою та швидким сервісом. Добре підходить для роботи й зустрічей.'},
    {'name': 'Medelin & Chiken Hut', 'address': 'вул. Новака 2, Ужгород', 'schedule': 'Пн–Нд: 08:00 – 19:00',
     'coords': (48.619107667735875, 22.296194690456993),
     'url': 'https://maps.app.goo.gl/XwbnzY4sDYxrfVjz9', 'img': PHOTO_URL_LOCATION,
     'amenities': ['Безкоштовний Wi‑Fi', 'Багато розеток', 'Зручна робоча зона', 'Pet-friendly', 'Оплата карткою'],
     'atmosphere': 'Класична локація Medelin з комфортною посадкою та швидким сервісом. Добре підходить для роботи й зустрічей.'},
    {'name': 'Medelin в Мукачево', 'address': 'пл. Кирила і Мефодія, 10\\12, Мукачево',
     'schedule': 'Пн–Нд: 08:00 – 20:00',
     'coords': (48.46811474382326, 22.718511803587017),
     'url': 'https://maps.app.goo.gl/otFGHBk8xjwymZUj6', 'img': PHOTO_URL_LOCATION,
     'amenities': ['Безкоштовний Wi‑Fi', 'Багато розеток', 'Зручна робоча зона', 'Pet-friendly', 'Оплата карткою'],
     'atmosphere': 'Класична локація Medelin з комфортною посадкою та швидким сервісом. Добре підходить для роботи й зустрічей.'},
    {'name': 'Medelin в Сваляві', 'address': 'вул. Головна, 21, Свалява', 'schedule': 'Пн–Нд: 08:00 – 20:00',
     'coords': (48.54870355834456, 22.98317680000477),
     'url': 'https://maps.app.goo.gl/xMNcsZf5yxoX4ZGV8', 'img': PHOTO_URL_LOCATION,
     'amenities': ['Безкоштовний Wi‑Fi', 'Багато розеток', 'Зручна робоча зона', 'Pet-friendly', 'Оплата карткою'],
     'atmosphere': 'Класична локація Medelin з комфортною посадкою та швидким сервісом. Добре підходить для роботи й зустрічей.'},

]

SOCIALS_DATA = [
    {'name': 'Телефон', 'url': 'tel:+380503775906'},
    {'name': 'Email', 'url': 'mailto:medelin.social@gmail.com'},
    {'name': 'Facebook', 'url': 'https://www.facebook.com/medelin.coffee/'},
    {'name': 'Instagram', 'url': 'https://www.instagram.com/medelin_uzh/'},
    {'name': 'Instagram Кабінет', 'url': 'https://www.instagram.com/kabinet.by.medelin/'},
    {'name': 'Instagram Боздош', 'url': 'https://www.instagram.com/medelincoffee.bozdosh/'},
    {'name': 'Instagram Швабська', 'url': 'https://www.instagram.com/medelin.shvabska.uzh/'},
    {'name': 'Instagram Свалява', 'url': 'https://www.instagram.com/medelin.svaliava/'},
]

async def seed():
    await coffee_beans_db.connect()
    await location_db.connect()
    await contacts_db.connect()

    await coffee_beans_db.clear_beans()
    await location_db.clear_locations()
    await contacts_db.clear_contacts()

    for b in BEANS_DATA:
        score = 0
        try:
            score = float(b.get('quality_score') or 0)
        except:
            pass
        roast = (b.get('roast') or '').lower()

        if not b.get('quality_score') or score < 80:
            img_url = '/photos/Comercial.png'
        elif roast == 'espresso':
            img_url = '/photos/Espresso.png'
        elif roast == 'filter':
            img_url = '/photos/Filter.png'
        else:
            img_url = '/photos/Comercial.png'

        await coffee_beans_db.add_bean(
            name=b['name'],
            price_250=b['price_250'],
            description=b['description'],
            species=b['species'],
            taste=b['taste'],
            roast=b['roast'],
            image_url=img_url,
            altitude=b['altitude'],
            processing=b['processing'],
            descriptors=b.get('descriptors', ''),
            variety=b['variety'],
            quality_score=b['quality_score'],
            harvest=b['harvest']
        )

    for l in LOCATIONS_DATA:
        await location_db.add_location(
            name=l['name'], address=l['address'], schedule=l['schedule'],
            google_maps_url=l['url'],
            coordinates={'lat': l['coords'][0], 'lon': l['coords'][1]},
            image_url=l['img'],
            amenities=l.get('amenities', []), atmosphere=l.get('atmosphere', '')
        )

    for s in SOCIALS_DATA:
        await contacts_db.add_contact(s['name'], s['url'])

    await close_client()

if __name__ == '__main__':
    asyncio.run(seed())
