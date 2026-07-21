<div align="center">

# 🤖 MedelinBot

**Telegram-бот та REST API для управління бізнесом Medelin Coffee Roasters**

[![Telegram Bot](https://img.shields.io/badge/Telegram-@MedelnBot-2CA5E0?style=for-the-badge&logo=telegram&logoColor=white)](https://t.me/MedelnBot)
[![Python](https://img.shields.io/badge/Python-3.11-3776AB?style=for-the-badge&logo=python&logoColor=white)](https://python.org)
[![aiogram](https://img.shields.io/badge/aiogram-3.26-2CA5E0?style=for-the-badge)](https://docs.aiogram.dev/)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.135-009688?style=for-the-badge&logo=fastapi&logoColor=white)](https://fastapi.tiangolo.com/)
[![MongoDB](https://img.shields.io/badge/MongoDB-Motor_3.7-47A248?style=for-the-badge&logo=mongodb&logoColor=white)](https://mongodb.com)

<br/>

> *Повноцінний бізнес-інструмент у Telegram. Приймай замовлення, керуй командою, слідкуй за продажами — все з телефону, без жодного зайвого додатку.*

</div>

---

## 📋 Зміст

- [Архітектура](#-архітектура)
- [Структура файлів](#-структура-файлів)
- [Ролі та доступ](#-ролі-та-доступ)
- [Функціонал бота](#-функціонал-бота)
- [REST API](#-rest-api)
- [База даних](#-база-даних)
- [Утиліти та сервіси](#-утиліти-та-сервіси)
- [Конфігурація](#-конфігурація)
- [Фонові задачі](#-фонові-задачі)
- [Запуск](#-запуск)

---

## 🏛️ Архітектура

MedelinBot — це **монолітний асинхронний додаток**, де Telegram Bot і FastAPI API запускаються в одному процесі через спільний asyncio event loop.

```
main.py (точка входу)
     │
     ├── FastAPI App (uvicorn, port 8000)
     │       ├── /api/* (REST endpoints)
     │       └── /admin-panel (захищена HTML-панель)
     │
     ├── aiogram Dispatcher (polling mode)
     │       ├── admin_router  (управління бізнесом)
     │       ├── user_router   (взаємодія з клієнтом)
     │       ├── order_router  (обробка замовлень)
     │       └── error_router  (глобальна обробка помилок)
     │
     ├── APScheduler (фонові задачі)
     │       ├── cleanup_old_data    (щотижня)
     │       └── send_monthly_stats  (1-го числа місяця)
     │
     └── PublicDataCache (in-memory кеш)
             ├── coffee     (каталог кави)
             ├── locations  (локації)
             └── socials    (контакти)
```

### Чому Bot + API в одному процесі?

- **Render Free Tier** дає лише 1 контейнер — це єдиний варіант
- **Спільний кеш** — бот та API читають дані з одного об'єкту в пам'яті
- **Спрощений деплой** — один `docker build`, один `docker run`
- **Без race conditions** — всі операції асинхронні через asyncio

---

## 📁 Структура файлів

```
MedelinBot/
│
├── 📄 main.py                 # Точка входу — запуск Bot + API разом
├── 📄 api.py                  # Всі FastAPI endpoints (REST API)
├── 📄 bot.py                  # Ініціалізація об'єкту бота
├── 📄 requirements.txt        # Python-залежності
├── 📄 .env.docker.example     # Приклад файлу конфігурації
│
├── 📂 app/
│   │
│   ├── 📂 common/
│   │   ├── bot_instance.py    # Єдиний екземпляр Bot (Singleton)
│   │   └── config.py          # Завантаження змінних середовища
│   │
│   ├── 📂 databases/          # Шар доступу до даних (Repository Pattern)
│   │   ├── mongo_client.py    # Підключення до MongoDB (Motor)
│   │   ├── user_database.py   # CRUD для користувачів
│   │   ├── orders_database.py # CRUD для замовлень
│   │   ├── active_orders_database.py  # Активні замовлення
│   │   ├── coffee_beans_database.py   # Каталог кави
│   │   ├── location_database.py       # Локації
│   │   ├── admin_database.py          # Адміністратори та персонал
│   │   ├── contacts_database.py       # Соцмережі та контакти
│   │   └── sales_database.py          # Статистика продажів
│   │
│   ├── 📂 handlers/           # Telegram Message/Callback Handlers
│   │   ├── admin_handlers.py  # ВЕЛИКИЙ файл (~74KB) — весь адмін-функціонал
│   │   ├── user_handlers.py   # Взаємодія з клієнтом
│   │   ├── order_handlers.py  # Обробка нових замовлень з сайту
│   │   └── error_handler.py   # Глобальний обробник помилок
│   │
│   ├── 📂 keyboards/
│   │   ├── admin_keyboards.py # InlineKeyboardMarkup для адмін-панелі
│   │   └── user_keyboards.py  # Клавіатури для кінцевих користувачів
│   │
│   └── 📂 utils/
│       ├── admin_notifications.py  # Формування повідомлень для адмінів
│       ├── data_cache.py           # In-memory кеш публічних даних
│       ├── logger.py               # Налаштування логування
│       ├── message_utils.py        # Утиліти для Telegram-повідомлень
│       ├── nova_poshta.py          # Інтеграція з API Нової Пошти
│       ├── paths.py                # Шляхи до файлів та URL-утиліти
│       ├── payment_refunds.py      # Логіка повернення коштів LiqPay
│       ├── phone_utils.py          # Форматування та валідація телефонів
│       ├── photo_utils.py          # Завантаження та обробка фото (Pillow)
│       ├── scheduler.py            # APScheduler — фонові задачі
│       └── time_utils.py           # Робота з датами (Kyiv timezone)
│
├── 📂 cache/                  # Директорія для кешованих даних
└── 📂 fills/
    └── seed.py                # Наповнення БД тестовими даними
```

---

## 👥 Ролі та доступ

Система має 3 рівні доступу:

| Роль | Опис | Можливості |
|---|---|---|
| 👑 **Owner** | Власник бізнесу | Все + управління командою, місячна статистика |
| 🔧 **Admin** | Адміністратор | Замовлення, каталог, локації, контакти |
| 👤 **Staff** | Персонал | Перегляд та управління замовленнями |

### Як визначається роль?

```python
# При кожній взаємодії бот перевіряє Telegram ID у колекції admins
admin = await admin_db.get_admin(user.id)
if admin:
    role = admin.get("role")  # "owner" | "admin" | "staff"
```

---

## 🤖 Функціонал бота

### 📋 Управління замовленнями (admin_handlers.py)

**Нове замовлення надходить так:**
1. Клієнт на сайті оформлює замовлення → POST `/api/orders`
2. API зберігає замовлення в MongoDB
3. API відправляє сповіщення в Telegram усім адмінам
4. Адмін натискає **✅ Підтвердити** або **❌ Відхилити**
5. Клієнт бачить оновлений статус на сайті через polling

```
📩 Нове замовлення #1234!

👤 Клієнт: Олексій Коваль
📞 Телефон: +380 67 123 45 67
📦 Спосіб: Нова Пошта, м. Ужгород, відд. №5

🛒 Склад замовлення:
  • Ethiopia Yirgacheffe × 1 (250г) — 320 ₴
  • Guatemala Huehuetenango × 2 (250г) — 680 ₴

💰 Сума: 1000 ₴
💳 Оплата: Готівка при отриманні

[✅ Підтвердити] [❌ Відхилити]
```

---

### ☕ Управління каталогом кави

**FSM (Finite State Machine) для додавання кави:**

```
Стартовий стан
     │
     ▼
Введення назви зерна
     │
     ▼
Вибір типу (Комерційна / Спешелті)
     │
     ├── Комерційна
     │       └── Ціна 250г → Опис → Фото → Збереження
     │
     └── Спешелті
             ├── Ціна 250г
             ├── Країна походження
             ├── Регіон
             ├── Сорт (variety)
             ├── Висота (altitude)
             ├── Метод обробки (processing)
             ├── Ступінь обсмаження (filter / espresso)
             ├── Дескриптори смаку
             ├── Врожай (harvest year)
             ├── Оцінка якості SCA (quality_score)
             ├── Опис
             └── Фото → Збереження
```

**Редагування** — посторінковий редактор для кожного поля окремо:
- Бот пропонує поточне значення та чекає нове
- Підтримка зміни фото з автоматичним збереженням

---

### 📍 Управління локаціями

- Перегляд усіх локацій зі скороченою інформацією
- Редагування кожної локації:
  - Назва та адреса
  - Графік роботи
  - Телефон та Google Maps посилання
  - Фотографія (через фото або URL)
  - Список зручностей (теги: Wi-Fi, кухня, дитяча кімната...)
  - GPS-координати (для карти Leaflet)

---

### 👥 Управління командою (тільки Owner)

```
/team
  │
  ├── Список всіх членів команди
  │       └── для кожного: ім'я, роль, Telegram username
  │
  ├── Додати члена команди
  │       ├── Пошук за Telegram ID, @username або телефоном
  │       └── Призначення ролі (admin / staff)
  │
  └── Видалити члена команди
          └── Підтвердження перед видаленням
```

---

### 📊 Статистика (тільки Owner)

**Звіт включає:**
- Загальна кількість замовлень за період
- Загальна сума продажів
- ТОП-5 найпопулярніших позицій
- Розбивка по способах оплати
- Порівняння з попереднім аналогічним періодом

**Доступні фільтри:**
- Сьогодні / Тиждень / Місяць / Все за всі часи

---

### 🔗 Управління контактами та соцмережами

- Перегляд та редагування посилань: Instagram, Facebook, Telegram, TikTok, телефон, email
- Зміни одразу відображаються на сайті (через кеш-інвалідацію)

---

## 🌐 REST API

### Публічні ендпоінти (без авторизації)

| Метод | URL | Опис |
|---|---|---|
| `GET` | `/api/coffee` | Весь каталог кавових зерен |
| `GET` | `/api/locations` | Список локацій |
| `GET` | `/api/socials` | Контакти та соціальні мережі |
| `POST` | `/api/orders` | Створення нового замовлення |
| `GET` | `/api/orders/{order_id}` | Деталі замовлення |
| `GET` | `/api/nova-poshta/cities` | Пошук міст НП |
| `GET` | `/api/nova-poshta/warehouses` | Пошук відділень НП |
| `POST` | `/api/liqpay/form` | Генерація форми оплати |
| `POST` | `/api/liqpay/callback` | Callback від LiqPay після оплати |
| `POST` | `/api/client-error` | Логування помилок з фронтенду |

### Захищені ендпоінти

| Метод | URL | Опис |
|---|---|---|
| `GET` | `/admin-panel` | HTML-панель (перевірка через сесію) |
| `GET` | `/api/admin/*` | Admin API (JWT або cookie авторизація) |

### Кешування API-відповідей

```python
class PublicDataCache:
    """In-memory кеш з TTL для публічних даних"""
    
    async def get_coffee(self) -> list:
        # Якщо кеш свіжий — повертає з пам'яті
        # Якщо застарів — оновлює з MongoDB у фоні
        pass
    
    async def warm_all(self, max_retries=3):
        # Попереднє завантаження всіх даних при старті
        pass
    
    def invalidate(self, key: str):
        # Примусова інвалідація після змін через бота
        pass
```

---

## 🗃️ База даних

### MongoDB Collections Schema

**`coffee_beans`**
```json
{
  "_id": "ObjectId",
  "name": "Ethiopia Yirgacheffe",
  "type": "specialty",
  "roast": "filter",
  "price_250": 340,
  "quality_score": "87.5",
  "processing": "Washed",
  "variety": "Heirloom",
  "altitude": "1800-2200m",
  "harvest": "2024",
  "descriptors": "Жасмин, бергамот, чорна смородина",
  "description": "...",
  "image_url": "/uploads/coffee/abc123.jpg",
  "created_at": "2024-01-15T10:30:00Z"
}
```

**`orders`**
```json
{
  "_id": "ObjectId",
  "order_id": "ORD-2024-001",
  "status": "confirmed",
  "client": {
    "name": "Олексій Коваль",
    "phone": "+380671234567"
  },
  "delivery": {
    "method": "nova_poshta",
    "city": "Ужгород",
    "warehouse": "Відділення №5"
  },
  "items": [
    {"id": "...", "name": "Ethiopia", "quantity": 1, "weight": 250, "price": 340}
  ],
  "payment": {
    "method": "liqpay",
    "status": "paid",
    "total": 340
  },
  "created_at": "2024-07-21T12:30:00Z"
}
```

**`admins`**
```json
{
  "user_id": 123456789,
  "username": "john_doe",
  "display_name": "Олексій",
  "role": "admin",
  "added_at": "2024-01-01T00:00:00Z",
  "added_by": 987654321
}
```

---

## 🛠️ Утиліти та сервіси

### `photo_utils.py` — Обробка зображень

```python
# Завантаження фото з Telegram → обробка через Pillow → збереження
async def save_photo_from_telegram(bot, photo_file_id) -> str:
    # 1. Завантажує файл через bot.download()
    # 2. Конвертує в WebP або JPEG (Pillow)
    # 3. Зменшує до максимального розміру
    # 4. Зберігає в /app/uploads/
    # 5. Повертає відносний URL
    pass
```

### `nova_poshta.py` — Інтеграція з НП

```python
# API Нової Пошти v2.0
async def search_cities(query: str) -> list:
    """Пошук міст через searchSettlements"""
    
async def search_warehouses(city_ref: str, query: str) -> list:
    """Пошук відділень та поштоматів"""
```

### `scheduler.py` — Фонові задачі

```python
def start_scheduler():
    scheduler = AsyncIOScheduler(timezone="Europe/Kyiv")
    
    # Щонеділі о 03:00 — очищення старих замовлень (> 5 днів)
    scheduler.add_job(cleanup_old_data, "cron", day_of_week="sun", hour=3)
    
    # 1-го числа кожного місяця — місячний звіт власнику
    scheduler.add_job(send_monthly_stats, "cron", day=1, hour=9)
    
    scheduler.start()
```

### `data_cache.py` — Стратегія кешування

```
Старт системи
     │
     ▼
warm_all() — завантажує coffee, locations, socials з MongoDB
     │
     ▼
FastAPI API → читає з кешу (без звернення до БД!)
     │
     ▼
Адмін змінює дані через бота
     │
     ▼
cache.invalidate("coffee") → наступний запит оновить кеш
```

---

## ⚙️ Конфігурація

### Змінні середовища (`.env`)

```env
# Telegram
BOT_TOKEN=7123456789:AAFxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx

# MongoDB
MONGO_URI=mongodb+srv://user:password@cluster.mongodb.net/
MONGO_DB_NAME=medelin

# Admin Telegram IDs (власник та адміни)
ADMIN_TELEGRAM_IDS=123456789,987654321
OWNER_TELEGRAM_ID=123456789

# LiqPay (онлайн-оплата)
LIQPAY_PUBLIC_KEY=your_public_key
LIQPAY_PRIVATE_KEY=your_private_key

# Nova Poshta
NP_API_KEY=your_nova_poshta_api_key

# Web App
WEB_APP_URL=https://medelin.onrender.com
```

### Завантаження конфігурації

```python
# app/common/config.py
from dotenv import load_dotenv
import os

load_dotenv()

BOT_TOKEN = os.getenv("BOT_TOKEN")
MONGO_URI = os.getenv("MONGO_URI")
ADMIN_IDS = [int(i) for i in os.getenv("ADMIN_TELEGRAM_IDS", "").split(",") if i]
```

---

## ⏰ Фонові задачі

| Задача | Розклад | Опис |
|---|---|---|
| `cleanup_old_data` | Щонеділі о 03:00 | Видаляє активні замовлення старіше 5 днів |
| `send_monthly_stats` | 1-го числа о 09:00 | Надсилає місячний звіт власнику |

### Місячний звіт (приклад)

```
📊 Звіт за Червень 2024

📦 Замовлень: 47
💰 Сума продажів: 28,340 ₴

☕ ТОП позиції:
  1. Ethiopia Yirgacheffe — 23 замовлення
  2. Colombia Huila — 18 замовлень
  3. Guatemala Huehuetenango — 15 замовлень

💳 Способи оплати:
  • LiqPay: 34 (72%)
  • Готівка: 13 (28%)
```

---

## 🚀 Запуск

### Локально (без Docker)

```bash
cd MedelinBot

# Встановлення залежностей
pip install -r requirements.txt

# Копіювання конфігурації
cp .env.docker.example .env
# Заповніть .env своїми значеннями

# Запуск
python main.py
```

### Локально (з Docker Compose)

```bash
# З кореня репозиторію
docker-compose up --build
```

MongoDB буде доступна на `localhost:27017`, API — на `localhost/api/`.

### Наповнення тестовими даними

```bash
# Після запуску системи
python fills/seed.py
```

---

## 📦 Залежності

```
aiogram==3.26.0        # Telegram Bot Framework (async)
fastapi==0.135.2        # Web API Framework
uvicorn==0.34.0         # ASGI Server
motor==3.7.1            # Async MongoDB Driver
pillow==11.1.0          # Image Processing
python-dotenv==1.0.1    # .env file loader
aiohttp==3.13.3         # Async HTTP Client (Nova Poshta)
aiofiles==25.1.0        # Async File I/O
aiosqlite==0.22.1       # SQLite (резерв)
asyncpg==0.31.0         # PostgreSQL (резерв)
apscheduler==3.11.2     # Background Job Scheduler
liqpay-sdk-python3==1.0.6  # LiqPay Payment SDK
python-multipart==0.0.9    # File Upload Support
```

---

## 🔄 Потік обробки помилок

```python
# error_handler.py — глобальний обробник
@error_router.errors(ExceptionHandler)
async def handle_error(update: Update, exception: Exception):
    logger.error(f"Unhandled exception: {exception}", exc_info=True)
    
    # Сповіщення власника про критичну помилку
    if isinstance(exception, CriticalError):
        await bot.send_message(OWNER_ID, f"🚨 Критична помилка: {exception}")
    
    # Коректне повідомлення користувачу
    await update.message.answer("Сталася помилка. Спробуйте ще раз.")
```

---

<div align="center">

**🤖 [Відкрити бота](https://t.me/MedelnBot)** · **[⬆️ Загальний README](../README.md)**

☕ *Зроблено з любов'ю до кави та чистого коду*

</div>
