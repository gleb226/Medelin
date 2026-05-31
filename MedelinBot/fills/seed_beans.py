import asyncio
import html
import re
import sys
from html.parser import HTMLParser
from pathlib import Path
from urllib.parse import urljoin

import requests

ROOT_DIR = Path(__file__).resolve().parents[1]
if str(ROOT_DIR) not in sys.path:
    sys.path.append(str(ROOT_DIR))

from app.databases.coffee_beans_database import coffee_beans_db
from app.databases.mongo_client import close_client


CATALOG_URL = "https://medelin.com/kofe-v-zernakh/"
DEFAULT_TIMEOUT = 20
DEFAULT_IMAGE_URL = "https://images.pexels.com/photos/1695052/pexels-photo-1695052.jpeg?auto=compress&cs=tinysrgb&w=800"


class ProductLinkParser(HTMLParser):
    def __init__(self):
        super().__init__()
        self.links: set[str] = set()

    def handle_starttag(self, tag, attrs):
        if tag != "a":
            return

        attrs_dict = dict(attrs)
        href = attrs_dict.get("href", "")

        if not href:
            return

        full_url = urljoin(CATALOG_URL, href)

        if re.search(r"/kofe-v-zernakh/\d+/?$", full_url):
            self.links.add(full_url)


class TextExtractor(HTMLParser):
    def __init__(self):
        super().__init__()
        self.parts: list[str] = []

    def handle_data(self, data):
        value = data.strip()
        if value:
            self.parts.append(value)


class ImageParser(HTMLParser):
    def __init__(self):
        super().__init__()
        self.images: list[str] = []

    def handle_starttag(self, tag, attrs):
        if tag != "img":
            return

        attrs_dict = dict(attrs)

        for key in ("src", "data-src", "data-original"):
            src = attrs_dict.get(key)
            if src:
                self.images.append(urljoin(CATALOG_URL, src))


def fetch_html(url: str) -> str:
    response = requests.get(
        url,
        timeout=DEFAULT_TIMEOUT,
        headers={
            "User-Agent": "Mozilla/5.0 (compatible; MedelinBotParser/1.0)",
            "Accept-Language": "uk-UA,uk;q=0.9,ru;q=0.8,en;q=0.7",
        },
    )
    response.raise_for_status()
    return response.text


def clean_text(value: str) -> str:
    value = html.unescape(value or "")
    value = re.sub(r"\s+", " ", value)
    return value.strip()


def html_to_text(page_html: str) -> str:
    parser = TextExtractor()
    parser.feed(page_html)
    return clean_text("\n".join(parser.parts))


def find_product_links(catalog_html: str) -> list[str]:
    parser = ProductLinkParser()
    parser.feed(catalog_html)
    return sorted(parser.links, key=lambda x: int(re.search(r"/(\d+)/?$", x).group(1)))


def extract_meta_content(page_html: str, name: str) -> str:
    patterns = [
        rf'<meta[^>]+name=["\']{re.escape(name)}["\'][^>]+content=["\']([^"\']+)["\']',
        rf'<meta[^>]+content=["\']([^"\']+)["\'][^>]+name=["\']{re.escape(name)}["\']',
        rf'<meta[^>]+property=["\']{re.escape(name)}["\'][^>]+content=["\']([^"\']+)["\']',
        rf'<meta[^>]+content=["\']([^"\']+)["\'][^>]+property=["\']{re.escape(name)}["\']',
    ]

    for pattern in patterns:
        match = re.search(pattern, page_html, flags=re.I | re.S)
        if match:
            return clean_text(match.group(1))

    return ""


def extract_title(page_html: str, text: str) -> str:
    og_title = extract_meta_content(page_html, "og:title")
    if og_title:
        title = re.split(r"\s+[—|-]\s+", og_title)[0]
        title = re.sub(r"\s+\d+\s*(грамм|г|g|гр)\b.*$", "", title, flags=re.I)
        return clean_text(title)

    h1_match = re.search(r"<h1[^>]*>(.*?)</h1>", page_html, flags=re.I | re.S)
    if h1_match:
        title = re.sub(r"<[^>]+>", " ", h1_match.group(1))
        title = re.sub(r"\s+\d+\s*(грамм|г|g|гр)\b.*$", "", title, flags=re.I)
        return clean_text(title)

    lines = [line.strip() for line in text.splitlines() if line.strip()]
    return clean_text(lines[0] if lines else "")


def extract_description(page_html: str, text: str) -> tuple[str, str]:
    meta_description = extract_meta_content(page_html, "description")
    og_description = extract_meta_content(page_html, "og:description")

    short_description = clean_text(meta_description or og_description)

    trash_patterns = [
        r"широкий выбор качественного кофе.*",
        r"купить кофе отборных сортов.*",
        r"натуральный кофе.*",
    ]

    for pattern in trash_patterns:
        short_description = re.sub(pattern, "", short_description, flags=re.I).strip(" .—-")

    description = short_description

    text_lines = [clean_text(line) for line in text.splitlines()]
    text_lines = [line for line in text_lines if len(line) > 35]

    useful_lines = []
    ignored = (
        "корзина",
        "купить",
        "грн",
        "uah",
        "добавить",
        "наличии",
        "отзывы",
        "артикул",
        "категория",
        "главная",
        "доставка",
        "оплата",
    )

    for line in text_lines:
        line_lower = line.lower()
        if any(word in line_lower for word in ignored):
            continue
        if line == short_description:
            continue
        useful_lines.append(line)

    if useful_lines:
        description = clean_text(" ".join(useful_lines[:4]))

    return description or short_description, short_description


def extract_article(text: str) -> str:
    patterns = [
        r"(?:Артикул|Код товару|Код товара|SKU)\s*[:№#]?\s*([A-Za-zА-Яа-яІіЇїЄєҐґ0-9\-_/]+)",
        r"\bSKU\s*[:№#]?\s*([A-Za-zА-Яа-яІіЇїЄєҐґ0-9\-_/]+)",
    ]

    for pattern in patterns:
        match = re.search(pattern, text, flags=re.I)
        if match:
            return clean_text(match.group(1))

    return ""


def extract_weight(text: str, title: str) -> int:
    source = f"{title}\n{text}"

    match = re.search(r"(\d{2,4})\s*(?:грамм|г|гр|g)\b", source, flags=re.I)
    if match:
        value = int(match.group(1))
        if value in (100, 200, 250, 500, 1000):
            return value

    if re.search(r"\b1\s*(?:кг|kg)\b", source, flags=re.I):
        return 1000

    return 250


def extract_prices(text: str, weight_grams: int) -> tuple[int, int | None, int | None]:
    candidates: list[int] = []

    price_patterns = [
        r"(\d{2,6})\s*(?:грн|uah|₴)",
        r"(?:Ціна|Цена|Вартість|Стоимость)\s*[:\-]?\s*(\d{2,6})",
    ]

    for pattern in price_patterns:
        for match in re.finditer(pattern, text, flags=re.I):
            value = int(match.group(1))
            if 20 <= value <= 10000:
                candidates.append(value)

    if not candidates:
        return 0, None, None

    raw_price = candidates[0]

    if weight_grams == 1000:
        price_1000 = raw_price
        price_250 = round(price_1000 / 4)
        return price_250, None, price_1000

    if weight_grams == 500:
        price_500 = raw_price
        price_250 = round(price_500 / 2)
        return price_250, price_500, None

    return raw_price, None, None


def extract_image(page_html: str) -> str:
    og_image = extract_meta_content(page_html, "og:image")
    if og_image:
        return og_image

    parser = ImageParser()
    parser.feed(page_html)

    for image_url in parser.images:
        lower = image_url.lower()
        if any(part in lower for part in ("logo", "icon", "sprite", "placeholder")):
            continue
        return image_url

    return DEFAULT_IMAGE_URL


def find_field(text: str, labels: tuple[str, ...]) -> str:
    labels_pattern = "|".join(re.escape(label) for label in labels)

    patterns = [
        rf"(?:{labels_pattern})\s*[:\-]\s*([^\n\r]+)",
        rf"(?:{labels_pattern})\s+([^\n\r]+)",
    ]

    for pattern in patterns:
        match = re.search(pattern, text, flags=re.I)
        if match:
            value = clean_text(match.group(1))
            value = re.split(r"\s{2,}", value)[0]
            return value.strip(" .;")

    return ""


def detect_country(name: str, text: str) -> str:
    source = f"{name}\n{text}".lower()

    countries = {
        "india": "Індія",
        "индия": "Індія",
        "інд": "Індія",
        "ethiopia": "Ефіопія",
        "эфиоп": "Ефіопія",
        "ефіоп": "Ефіопія",
        "kenya": "Кенія",
        "кения": "Кенія",
        "кенія": "Кенія",
        "colombia": "Колумбія",
        "колумб": "Колумбія",
        "mexico": "Мексика",
        "мексик": "Мексика",
        "nicaragua": "Нікарагуа",
        "никараг": "Нікарагуа",
        "нікараг": "Нікарагуа",
        "brazil": "Бразилія",
        "бразил": "Бразилія",
    }

    for key, value in countries.items():
        if key in source:
            return value

    return ""


def detect_processing(text: str) -> str:
    source = text.lower()

    if any(word in source for word in ("washed", "влажной обработки", "мита", "мыт")):
        return "Мита"
    if any(word in source for word in ("natural", "сухой обработки", "натураль")):
        return "Натуральна"
    if any(word in source for word in ("monsoon", "monsooned", "мусон")):
        return "Monsooned"
    if any(word in source for word in ("decaf", "без кофеина", "без кофеїну")):
        return "Декофеїнізація"

    return ""


def detect_sort(name: str, text: str) -> str:
    source = f"{name}\n{text}".lower()

    if "робуста" in source and "араб" in source:
        return "Арабіка / Робуста"
    if "робуста" in source:
        return "Робуста"
    if "араб" in source or "arabica" in source:
        return "Арабіка 100%"

    return "Арабіка 100%"


def detect_roast(text: str) -> str:
    source = text.lower()

    if any(word in source for word in ("темная", "темне", "темная обжарка", "dark")):
        return "Темне"
    if any(word in source for word in ("светлая", "світле", "light")):
        return "Світле"
    if any(word in source for word in ("средняя", "середн", "medium")):
        return "Середнє"

    return "Середнє"


def detect_taste(text: str) -> str:
    taste = find_field(text, ("Смак", "Вкус", "Taste", "Ноти", "Ноты"))
    if taste:
        return taste

    source = text.lower()
    notes = []

    note_map = {
        "шоколад": "шоколад",
        "карамел": "карамель",
        "горіх": "горіх",
        "орех": "горіх",
        "фрукт": "фрукти",
        "цвет": "квіти",
        "квіт": "квіти",
        "цитрус": "цитрус",
        "ягод": "ягоди",
        "спец": "спеції",
        "кислин": "делікатна кислинка",
        "мед": "мед",
    }

    for key, value in note_map.items():
        if key in source and value not in notes:
            notes.append(value)

    return ", ".join(notes)


def score_characteristic(text: str, positive_words: tuple[str, ...], negative_words: tuple[str, ...] = ()) -> int:
    source = text.lower()

    score = 2

    for word in positive_words:
        if word in source:
            score += 1

    for word in negative_words:
        if word in source:
            score -= 1

    return max(0, min(5, score))


def build_bean_from_page(url: str) -> dict:
    page_html = fetch_html(url)
    text = html_to_text(page_html)

    name = extract_title(page_html, text)
    description, short_description = extract_description(page_html, text)
    article = extract_article(text)
    weight_grams = extract_weight(text, name)

    price_250, price_500, price_1000 = extract_prices(text, weight_grams)

    country = find_field(text, ("Країна", "Страна", "Country")) or detect_country(name, text)
    altitude = find_field(text, ("Висота", "Высота", "Altitude"))
    processing = find_field(text, ("Обробка", "Обработка", "Processing")) or detect_processing(text)
    variety = find_field(text, ("Різновид", "Разновидность", "Variety", "Сорт"))
    cup_score = find_field(text, ("Cup Score", "Оцінка", "Оценка"))
    harvest = find_field(text, ("Врожай", "Урожай", "Harvest"))

    sort = detect_sort(name, text)
    roast = detect_roast(text)
    taste = detect_taste(text)

    acidity = score_characteristic(text, ("кислин", "кислотн", "цитрус", "фрукт", "ягод"), ("низкая кислотность", "низька кислотність"))
    bitterness = score_characteristic(text, ("горчин", "гірчин", "шоколад", "какао", "темн"), ("мягкий", "м'який"))
    body = score_characteristic(text, ("плотн", "щільн", "насыщ", "насич", "густ", "крепкий", "міцн"))

    recommendation = find_field(text, ("Рекомендація", "Рекомендации", "Рекомендация", "Recommendation"))
    image_url = extract_image(page_html)

    if not description:
        description = "Фірмові зерна Medelin. Деталі та наявність уточнюй у бариста."

    return {
        "name": name,
        "price_250": price_250,
        "price_500": price_500,
        "price_1000": price_1000,
        "description": description,
        "short_description": short_description,
        "article": article,
        "source_url": url,
        "weight_grams": weight_grams,
        "sort": sort,
        "taste": taste,
        "roast": roast,
        "image_url": image_url,
        "country": country,
        "altitude": altitude,
        "processing": processing,
        "recommendation": recommendation,
        "variety": variety,
        "cup_score": cup_score,
        "harvest": harvest,
        "acidity": acidity,
        "bitterness": bitterness,
        "body": body,
    }


async def seed_beans():
    await coffee_beans_db.connect()

    catalog_html = fetch_html(CATALOG_URL)
    product_links = find_product_links(catalog_html)

    if not product_links:
        raise RuntimeError("Не знайдено товарів у каталозі кави в зернах.")

    parsed_beans = []

    for product_url in product_links:
        try:
            bean = build_bean_from_page(product_url)

            if not bean["name"]:
                print(f"SKIP без назви: {product_url}")
                continue

            if not bean["price_250"]:
                print(f"SKIP без ціни: {bean['name']} | {product_url}")
                continue

            parsed_beans.append(bean)
            print(f"OK: {bean['name']} — {bean['price_250']} грн / 250г")

        except Exception as exc:
            print(f"ERROR: {product_url}: {exc}")

    if not parsed_beans:
        raise RuntimeError("Парсер не зміг підготувати жодної позиції для запису.")

    await coffee_beans_db.clear_beans()

    for bean in parsed_beans:
        await coffee_beans_db.add_bean(
            name=bean["name"],
            price_250=bean["price_250"],
            price_500=bean["price_500"],
            price_1000=bean["price_1000"],
            description=bean["description"],
            short_description=bean["short_description"],
            article=bean["article"],
            source_url=bean["source_url"],
            weight_grams=250,
            sort=bean["sort"],
            taste=bean["taste"],
            roast=bean["roast"],
            image_url=bean["image_url"],
            country=bean["country"],
            altitude=bean["altitude"],
            processing=bean["processing"],
            acidity=bean["acidity"],
            bitterness=bean["bitterness"],
            body=bean["body"],
            variety=bean["variety"],
            cup_score=bean["cup_score"],
            harvest=bean["harvest"],
            recommendation=bean["recommendation"],
        )

    print(f"Готово. Записано позицій: {len(parsed_beans)}")

    await close_client()


if __name__ == "__main__":
    asyncio.run(seed_beans())