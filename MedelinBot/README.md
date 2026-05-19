# 🤖 MedelinBot - Telegram Bot

<div align="center">

![MedelinBot Logo](https://img.shields.io/badge/Medelin-Telegram%20Bot-brown?style=for-the-badge&logo=telegram)

**Telegram бот для кав'ярні Medelin в Ужгороді 🇺🇦**

[![Python](https://img.shields.io/badge/Python-3.8+-blue.svg?style=flat-square&logo=python)](https://www.python.org/)
[![Telegram Bot API](https://img.shields.io/badge/Telegram-Bot%20API-blue?style=flat-square&logo=telegram)](https://core.telegram.org/bots/api)
[![License](https://img.shields.io/badge/License-MIT-green.svg?style=flat-square)](LICENSE)
[![Uzhhorod](https://img.shields.io/badge/Made%20in-Uzhhorod-yellow.svg?style=flat-square)](https://goo.gl/maps/medelin)

[Особливості](#-особливості) • [Встановлення](#-встановлення) • [Меню](#-меню) • [Документація](#-документація) • [Внесок](#-внесок)

</div>

---

## 📋 Зміст

- [Про проект](#-про-проект)
- [Особливості](#-особливості)
- [Технології](#-технології)
- [Встановлення](#-встановлення)
- [Конфігурація](#-конфігурація)
- [Використання](#-використання)
- [Команди](#-команди)
- [Структура проекту](#-структура-проекту)
- [API Документація](#-api-документація)
- [База даних](#-база-даних)
- [Безпека](#-безпека)
- [Тестування](#-тестування)
- [Розгортання](#-розгортання)
- [Внесок у проект](#-внесок-у-проект)
- [Ліцензія](#-ліцензія)
- [Контакти](#-контакти)

---

## 🎯 Про проект

**MedelinBot** — це сучасний Telegram бот для кав'ярні **Medelin** в Ужгороді. Бот створений для зручного замовлення
кави, десертів та інших страв, бронювання столиків, відстеження програми лояльності та отримання актуальної інформації
про заклад.

### 🌟 Чому MedelinBot?

- ⚡ **Швидке замовлення**: Зроби замовлення за 30 секунд
- 🎁 **Бонуси**: Накопичуй бали та отримуй знижки
- 📍 **Зручна локація**: Ми в центрі Ужгорода
- ☕ **Якісна кава**: Лише свіжообсмажені зерна
- 🇺🇦 **Українська кав'ярня**: Підтримуй локальний бізнес

---

## ✨ Особливості

### ☕ Замовлення

- 📱 **Онлайн меню**
    - Повний каталог напоїв та їжі
    - Фото страв та детальні описи
    - Інформація про алергени
    - Калорійність та склад

- 🛒 **Кошик та оплата**
    - Швидке додавання в кошик
    - Можливість змінити розмір напою
    - Додаткові інгредієнти (сироп, вершки, молоко)
    - Онлайн оплата або готівка

- 🚀 **Доставка та самовивіз**
    - Доставка по Ужгороду
    - Самовивіз зі знижкою 10%
    - Відстеження статусу замовлення
    - Приблизний час приготування

### 🎯 Програма лояльності

- 💳 **Бонусна система**
    - Накопичуй бали за кожне замовлення
    - 1₴ = 1 бал
    - Обмінюй бали на знижки
    - Спеціальні акції для постійних клієнтів

- 🎁 **Акції та знижки**
    - Щоденна happy hour (15:00-17:00) -15%
    - Кава дня зі знижкою
    - Бонус на день народження
    - Реферальна програма

### 📅 Бронювання

- 🪑 **Резервація столиків**
    - Вибір зручного часу
    - Вказати кількість гостей
    - Побажання щодо розміщення
    - Підтвердження бронювання

- 🎉 **Заходи та івенти**
    - Кавові дегустації
    - Майстер-класи від бариста
    - Музичні вечори
    - Кінопокази

### 📢 Інформація

- 🕐 **Режим роботи**
    - Пн-Пт: 8:00 - 22:00
    - Сб-Нд: 9:00 - 23:00
    - Святкові дні

- 📍 **Локація та контакти**
    - Адреса та карта
    - Номер телефону
    - Соціальні мережі
    - Wi-Fi пароль

---

## 🛠 Технології

### Backend

```python
Python
3.8 +  # Основна мова програмування
python - telegram - bot  # Telegram Bot API
SQLAlchemy  # ORM для роботи з БД
Redis  # Кешування та черги
APScheduler  # Планувальник задач (нагадування)
Pillow  # Обробка зображень меню
```

### База даних

```sql
PostgreSQL
13+      # Основна БД
Redis 6+            # Кеш, сесії та черги замовлень
```

### Платіжні системи

```yaml
LiqPay              # Онлайн-платежі
Monobank API        # Інтеграція з Monobank
Wayforpay           # Альтернативна платіжна система
```

### Інструменти розробки

```yaml
Docker              # Контейнеризація
Docker Compose      # Оркестрація
pytest              # Тестування
pre-commit          # Git hooks
Black               # Форматування коду
Flake8              # Лінтинг
```

---


### Передумови

Переконайтеся, що у вас встановлено:

- Python 3.8 або новіша версія
- PostgreSQL 13+
- Redis 6+
- Git


```bash
# Створення таблиць
python manage.py db init
python manage.py db migrate
python manage.py db upgrade

# Заповнення меню та початковими даними
python manage.py seed_menu
```

#### 6. Запуск бота

```bash
python main.py
```

### 🐳 Встановлення через Docker

```bash
# Клонування репозиторію
git clone https://github.com/gleb226/MedelinBot.git
cd MedelinBot

# Налаштування змінних середовища
cp .env.example .env
nano .env

# Запуск через Docker Compose
docker-compose up -d

# Перевірка логів
docker-compose logs -f bot
```

---

## ⚙️ Конфігурація

### Файл .env

Створіть файл `.env` у кореневій директорії проекту:

```env
# Telegram Bot
BOT_TOKEN=your_bot_token_here

# База даних
MONGO_URI=mongodb+srv://Medelb:<07072010Hm!>@medelinbot.1bwvthp.mongodb.net/?appName=MedelinBot
MONGO_DB_NAME=medelinbot

# Redis
REDIS_URL=redis://localhost:6379/0
REDIS_CACHE_TTL=3600

# Безпека
SECRET_KEY=your_secret_key_here
ENCRYPTION_KEY=your_encryption_key_here

# Платежі
PAYMENT_TOKEN=your_payment_provider_token

# Налаштування кав'ярні
CAFE_NAME=Medelin
CAFE_ADDRESS=вул. Корзо, 15, Ужгород
CAFE_PHONE=+380123456789
CAFE_EMAIL=info@medelin.cafe

# Доставка
DELIVERY_ENABLED=true
DELIVERY_MIN_ORDER=150
DELIVERY_PRICE=50
DELIVERY_FREE_FROM=500

# Знижки
SELF_PICKUP_DISCOUNT=10
HAPPY_HOUR_START=15:00
HAPPY_HOUR_END=17:00
HAPPY_HOUR_DISCOUNT=15

# Логування
LOG_LEVEL=INFO
LOG_FILE=logs/bot.log

# Налаштування
TIMEZONE=Europe/Uzhgorod
LANGUAGE=uk
MAX_MESSAGE_LENGTH=4096
```

---

## 📱 Використання

### Початок роботи

1. **Знайдіть бота** у Telegram: `@MedelinBot`
2. **Натисніть** `/start` для початку
3. **Виберіть дію** з головного меню

### Приклади використання

#### ☕ Замовлення кави

```
Користувач: /menu
Бот: ☕ Меню Medelin

     🔥 Популярне:
     1. Капучино - 65₴
     2. Латте - 70₴
     3. Американо - 50₴
     
     Натисніть на напій для деталей →
```

#### 🛒 Додавання в кошик

```
Користувач: [обирає Капучино]
Бот: ☕ Капучино - 65₴
     
     Розмір:
     • Маленький (200ml) - 65₴
     • Середній (300ml) - 75₴
     • Великий (400ml) - 85₴
     
     Додатково:
     ☐ Карамельний сироп (+15₴)
     ☐ Вершки (+10₴)
     ☐ Соєве молоко (+10₴)
```

#### 🚀 Оформлення замовлення

```
Користувач: /cart
Бот: 🛒 Ваш кошик:
     
     1. Капучино (300ml) x1 - 75₴
     2. Круасан з шоколадом x2 - 120₴
     
     Разом: 195₴
     Бонуси: -20₴
     До сплати: 175₴
     
     Спосіб отримання:
     🚗 Доставка | 🚶 Самовивіз -10%
```

#### 💳 Бонусна карта

```
Користувач: /bonus
Бот: 💳 Ваша бонусна картка
     
     Баланс: 245 балів
     Рівень: ⭐ Срібний
     
     📊 Статистика:
     Замовлень: 23
     Витрачено: 3,450₴
     Зекономлено: 345₴
     
     До наступного рівня: 255 балів
```

---

## 📚 Команди

### Основні команди

| Команда   | Опис                        |
|-----------|-----------------------------|
| `/start`  | Запуск бота та головне меню |
| `/help`   | Довідка по командам         |
| `/menu`   | Переглянути меню            |
| `/cart`   | Мій кошик                   |
| `/orders` | Мої замовлення              |
| `/bonus`  | Бонусна картка              |

### Замовлення

| Команда       | Опис                         |
|---------------|------------------------------|
| `/order`      | Нове замовлення              |
| `/repeat`     | Повторити останнє замовлення |
| `/favorites`  | Обрані позиції               |
| `/clear_cart` | Очистити кошик               |

### Інформація

| Команда     | Опис                 |
|-------------|----------------------|
| `/location` | Адреса та карта      |
| `/contacts` | Контактна інформація |
| `/hours`    | Режим роботи         |
| `/events`   | Актуальні події      |
| `/wifi`     | Пароль Wi-Fi         |

### Бронювання

| Команда           | Опис                 |
|-------------------|----------------------|
| `/book`           | Забронювати столик   |
| `/my_bookings`    | Мої бронювання       |
| `/cancel_booking` | Скасувати бронювання |

### Налаштування

| Команда          | Опис                     |
|------------------|--------------------------|
| `/settings`      | Налаштування профілю     |
| `/language`      | Вибір мови               |
| `/notifications` | Налаштування сповіщень   |
| `/privacy`       | Налаштування приватності |

### Адміністративні команди

| Команда      | Опис                  |
|--------------|-----------------------|
| `/admin`     | Панель адміністратора |
| `/stats`     | Статистика замовлень  |
| `/broadcast` | Розсилка повідомлень  |
| `/menu_edit` | Редагування меню      |
| `/promo`     | Створити промокод     |

---

## 📁 Структура проекту

```
MedelinBot/
├── 📂 app/
│   ├── 📂 handlers/          # Обробники команд
│   │   ├── __init__.py
│   │   ├── start.py         # /start, /help
│   │   ├── menu.py          # Меню та каталог
│   │   ├── cart.py          # Кошик
│   │   ├── order.py         # Оформлення замовлень
│   │   ├── booking.py       # Бронювання столиків
│   │   ├── bonus.py         # Бонусна система
│   │   └── admin.py         # Адмін-панель
│   ├── 📂 models/           # Моделі бази даних
│   │   ├── __init__.py
│   │   ├── user.py          # Користувачі
│   │   ├── product.py       # Товари
│   │   ├── category.py      # Категорії
│   │   ├── order.py         # Замовлення
│   │   ├── cart.py          # Кошик
│   │   ├── booking.py       # Бронювання
│   │   └── bonus.py         # Бонуси
│   ├── 📂 services/         # Бізнес-логіка
│   │   ├── __init__.py
│   │   ├── menu_service.py
│   │   ├── order_service.py
│   │   ├── payment_service.py
│   │   ├── delivery_service.py
│   │   ├── bonus_service.py
│   │   └── notification_service.py
│   ├── 📂 utils/            # Допоміжні функції
│   │   ├── __init__.py
│   │   ├── validators.py
│   │   ├── formatters.py
│   │   ├── decorators.py
│   │   └── price_calculator.py
│   ├── 📂 middleware/       # Middleware
│   │   ├── __init__.py
│   │   ├── auth.py
│   │   └── logging.py
│   └── 📂 keyboards/        # Клавіатури
│       ├── __init__.py
│       ├── main_menu.py
│       ├── menu_keyboard.py
│       └── inline_buttons.py
├── 📂 database/
│   ├── migrations/          # Міграції БД
│   └── seeds/              # Початкові дані та меню
├── 📂 static/
│   ├── images/             # Фото страв та напоїв
│   └── media/              # Інші медіафайли
├── 📂 tests/               # Тести
│   ├── test_handlers/
│   ├── test_services/
│   └── test_models/
├── 📂 docker/
│   ├── Dockerfile
│   ├── docker-compose.yml
│   └── nginx.conf
├── 📂 docs/                # Документація
│   ├── API.md
│   ├── MENU.md
│   └── DEPLOYMENT.md
├── 📂 logs/                # Логи
├── 📂 scripts/             # Скрипти
│   ├── deploy.sh
│   └── backup.sh
├── .env.example            # Приклад змінних
├── .gitignore
├── requirements.txt        # Залежності Python
├── config.py              # Конфігурація
├── main.py                # Точка входу
├── manage.py              # CLI команди
├── README.md              # Цей файл
└── LICENSE                # Ліцензія
```

---

## 🔌 API Документація

### Endpoints

#### Користувачі

```http
GET /api/users/{user_id}
POST /api/users
PUT /api/users/{user_id}
GET /api/users/{user_id}/bonus
```

#### Меню

```http
GET /api/menu
GET /api/menu/categories
GET /api/menu/products/{id}
GET /api/menu/search?q={query}
```

#### Замовлення

```http
GET /api/orders
POST /api/orders
GET /api/orders/{id}
PUT /api/orders/{id}/status
DELETE /api/orders/{id}
```

#### Бронювання

```http
GET /api/bookings
POST /api/bookings
GET /api/bookings/{id}
DELETE /api/bookings/{id}
```

### Приклади запитів

#### Створення замовлення

```bash
curl -X POST https://api.medelin.cafe/orders \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -d '{
    "items": [
      {"product_id": 15, "quantity": 2, "size": "medium"},
      {"product_id": 23, "quantity": 1}
    ],
    "delivery_type": "delivery",
    "address": "вул. Корзо, 10",
    "payment_method": "online",
    "use_bonus": 50
  }'
```

#### Отримання меню

```bash
curl -X GET https://api.medelin.cafe/menu \
  -H "Authorization: Bearer YOUR_TOKEN"
```

---

## 💾 База даних

### Схема бази даних

```sql
-- Користувачі
CREATE TABLE users
(
    id           SERIAL PRIMARY KEY,
    telegram_id  BIGINT UNIQUE NOT NULL,
    username     VARCHAR(255),
    full_name    VARCHAR(255),
    phone        VARCHAR(20),
    email        VARCHAR(255),
    language     VARCHAR(10)    DEFAULT 'uk',
    bonus_points INTEGER        DEFAULT 0,
    total_orders INTEGER        DEFAULT 0,
    total_spent  DECIMAL(10, 2) DEFAULT 0,
    created_at   TIMESTAMP      DEFAULT CURRENT_TIMESTAMP,
    updated_at   TIMESTAMP      DEFAULT CURRENT_TIMESTAMP
);

-- Категорії меню
CREATE TABLE categories
(
    id          SERIAL PRIMARY KEY,
    name        VARCHAR(255) NOT NULL,
    name_en     VARCHAR(255),
    description TEXT,
    icon        VARCHAR(50),
    sort_order  INTEGER   DEFAULT 0,
    is_active   BOOLEAN   DEFAULT true,
    created_at  TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Товари (напої, їжа)
CREATE TABLE products
(
    id           SERIAL PRIMARY KEY,
    category_id  INTEGER REFERENCES categories (id),
    name         VARCHAR(255)   NOT NULL,
    name_en      VARCHAR(255),
    description  TEXT,
    price        DECIMAL(10, 2) NOT NULL,
    image_url    VARCHAR(500),
    calories     INTEGER,
    is_available BOOLEAN   DEFAULT true,
    is_popular   BOOLEAN   DEFAULT false,
    allergens    TEXT[],
    sizes        JSONB, -- {"small": 65, "medium": 75, "large": 85}
    addons       JSONB, -- [{"name": "Сироп", "price": 15}, ...]
    created_at   TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Замовлення
CREATE TABLE orders
(
    id               SERIAL PRIMARY KEY,
    user_id          INTEGER REFERENCES users (id),
    order_number     VARCHAR(50) UNIQUE NOT NULL,
    status           VARCHAR(50)    DEFAULT 'pending', -- pending, preparing, ready, delivered, cancelled
    delivery_type    VARCHAR(20),                      -- delivery, pickup
    delivery_address TEXT,
    total_price      DECIMAL(10, 2)     NOT NULL,
    discount_amount  DECIMAL(10, 2) DEFAULT 0,
    bonus_used       INTEGER        DEFAULT 0,
    payment_method   VARCHAR(50),                      -- cash, online, card
    payment_status   VARCHAR(50)    DEFAULT 'pending',
    notes            TEXT,
    estimated_time   INTEGER,                          -- в хвилинах
    created_at       TIMESTAMP      DEFAULT CURRENT_TIMESTAMP,
    updated_at       TIMESTAMP      DEFAULT CURRENT_TIMESTAMP
);

-- Позиції замовлення
CREATE TABLE order_items
(
    id           SERIAL PRIMARY KEY,
    order_id     INTEGER REFERENCES orders (id) ON DELETE CASCADE,
    product_id   INTEGER REFERENCES products (id),
    product_name VARCHAR(255), -- збережена назва
    quantity     INTEGER        NOT NULL,
    size         VARCHAR(50),
    addons       JSONB,
    price        DECIMAL(10, 2) NOT NULL,
    subtotal     DECIMAL(10, 2) NOT NULL
);

-- Бронювання столиків
CREATE TABLE bookings
(
    id           SERIAL PRIMARY KEY,
    user_id      INTEGER REFERENCES users (id),
    booking_date DATE    NOT NULL,
    booking_time TIME    NOT NULL,
    guests_count INTEGER NOT NULL,
    table_number INTEGER,
    status       VARCHAR(50) DEFAULT 'confirmed', -- confirmed, cancelled, completed
    notes        TEXT,
    created_at   TIMESTAMP   DEFAULT CURRENT_TIMESTAMP
);

-- Бонусні транзакції
CREATE TABLE bonus_transactions
(
    id          SERIAL PRIMARY KEY,
    user_id     INTEGER REFERENCES users (id),
    order_id    INTEGER REFERENCES orders (id),
    amount      INTEGER NOT NULL, -- додатне = нарахування, від'ємне = списання
    type        VARCHAR(50),      -- earned, spent, bonus_gift
    description TEXT,
    created_at  TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Промокоди
CREATE TABLE promo_codes
(
    id               SERIAL PRIMARY KEY,
    code             VARCHAR(50) UNIQUE NOT NULL,
    discount_type    VARCHAR(20), -- percent, fixed
    discount_value   DECIMAL(10, 2)     NOT NULL,
    min_order_amount DECIMAL(10, 2),
    max_uses         INTEGER,
    uses_count       INTEGER   DEFAULT 0,
    valid_from       TIMESTAMP,
    valid_to         TIMESTAMP,
    is_active        BOOLEAN   DEFAULT true,
    created_at       TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

### Міграції

```bash
# Створити нову міграцію
python manage.py db migrate -m "Опис змін"

# Застосувати міграції
python manage.py db upgrade

# Відкотити міграцію
python manage.py db downgrade
```

---

## 🔒 Безпека

### Захист даних

- 🔐 **Шифрування**: Всі персональні дані шифруються AES-256
- 🛡️ **GDPR**: Повна відповідність вимогам GDPR
- 🔑 **Токени**: JWT токени для аутентифікації
- 🚫 **Rate Limiting**: Захист від спаму та DDoS

### Рекомендації

```python
# Ніколи не зберігайте токени у коді
# ❌ НЕПРАВИЛЬНО
BOT_TOKEN = "123456:ABC-DEF"

# ✅ ПРАВИЛЬНО
import os

BOT_TOKEN = os.getenv('TELEGRAM_BOT_TOKEN')
```

### Безпечні практики

1. **Регулярно оновлюйте залежності**
   ```bash
   pip list --outdated
   pip install --upgrade package_name
   ```

2. **Використовуйте сильні паролі для БД**
3. **Обмежуйте доступ до адмін-панелі**
4. **Регулярно робіть бекапи**
5. **Моніторте логи на підозрілу активність**

---

## 🧪 Тестування

### Запуск тестів

```bash
# Всі тести
pytest

# З покриттям коду
pytest --cov=app tests/

# Конкретний тест
pytest tests/test_handlers/test_start.py

# З виводом у консоль
pytest -v

# Паралельний запуск
pytest -n auto
```

### Структура тестів

```python
# tests/test_handlers/test_start.py
import pytest
from app.handlers.start import start_command


@pytest.mark.asyncio
async def test_start_command():
    """Тест команди /start"""
    # Arrange
    mock_update = create_mock_update()

    # Act
    result = await start_command(mock_update, None)

    # Assert
    assert result is not None
    assert "Вітаємо" in result
```

### Покриття коду

```bash
# Генерація звіту покриття
coverage run -m pytest
coverage report
coverage html  # HTML звіт
```

---

#### 4. Systemd Service

Створіть `/etc/systemd/system/medelinbot.service`:

```ini
[Unit]
Description = MedelinBot Telegram Bot
After = network.target postgresql.service redis.service

[Service]
Type = simple
User = www-data
WorkingDirectory = /var/www/MedelinBot
Environment = "PATH=/var/www/MedelinBot/venv/bin"
ExecStart = /var/www/MedelinBot/venv/bin/python main.py
Restart = always

[Install]
WantedBy = multi-user.target
```

```bash
sudo systemctl daemon-reload
sudo systemctl start medelinbot
sudo systemctl enable medelinbot
```

### Docker Deployment

```yaml
# docker-compose.yml
version: '3.8'

services:
  bot:
    build: .
    container_name: medelinbot
    restart: always
    env_file: .env
    depends_on:
      - db
      - redis
    volumes:
      - ./logs:/app/logs

  db:
    image: postgres:13
    container_name: medelinbot_db
    restart: always
    environment:
      POSTGRES_DB: medelinbot
      POSTGRES_USER: botuser
      POSTGRES_PASSWORD: ${DB_PASSWORD}
    volumes:
      - postgres_data:/var/lib/postgresql/data

  redis:
    image: redis:6-alpine
    container_name: medelinbot_redis
    restart: always

volumes:
  postgres_data:
```

---

## 🤝 Внесок у проект

Ми вітаємо будь-який внесок у розвиток проекту!

### Як долучитися

1. **Fork** проекту
2. **Створіть** feature branch (`git checkout -b feature/AmazingFeature`)
3. **Commit** ваші зміни (`git commit -m 'Add some AmazingFeature'`)
4. **Push** в branch (`git push origin feature/AmazingFeature`)
5. **Відкрийте** Pull Request

### Правила коду

- Використовуйте **Black** для форматування
- Додавайте **docstrings** до функцій
- Пишіть **тести** для нового функціоналу
- Дотримуйтесь **PEP 8**

```bash
# Форматування коду
black app/

# Перевірка стилю
flake8 app/

# Сортування імпортів
isort app/
```

### Звіт про помилки

Створюйте Issue з такою інформацією:

- 📝 Опис проблеми
- 🔄 Кроки для відтворення
- ✅ Очікувана поведінка
- ❌ Фактична поведінка
- 💻 Версія Python, ОС
- 📋 Логи (якщо є)

## 📊 Статистика

<div align="center">

![GitHub stars](https://img.shields.io/github/stars/gleb226/MedelinBot?style=social)
![GitHub forks](https://img.shields.io/github/forks/gleb226/MedelinBot?style=social)
![GitHub watchers](https://img.shields.io/github/watchers/gleb226/MedelinBot?style=social)

![Commit Activity](https://img.shields.io/github/commit-activity/m/gleb226/MedelinBot)
![Last Commit](https://img.shields.io/github/last-commit/gleb226/MedelinBot)
![Code Size](https://img.shields.io/github/languages/code-size/gleb226/MedelinBot)

</div>

---

## 📄 Ліцензія

Цей проект ліцензовано під [MIT License](LICENSE).

```
MIT License

Copyright (c) 2024 Medelin Coffee Bot

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction...
```

---

## 👨‍💻 Автори

- **Gleb** - *Creator & Developer* - [@gleb226](https://github.com/gleb226)

### Contributors

<a href="https://github.com/gleb226/MedelinBot/graphs/contributors">
  <img src="https://contrib.rocks/image?repo=gleb226/MedelinBot" />
</a>

---

## 📞 Контакти

### 🏪 Кав'ярня Medelin

- 📍 Адреса: вул. Корзо, 15, Ужгород, Закарпатська область
- 📞 Телефон: [+380 (XX) XXX-XX-XX](tel:+380XXXXXXXXX)
- 📧 Email: info@medelin.cafe
- 🌐 Веб-сайт: [medelin.cafe](https://medelin.cafe)

### 💬 Соціальні мережі

- 📱 Instagram: [@medelin.uzhhorod](https://instagram.com/medelin.uzhhorod)
- 👥 Facebook: [Medelin Coffee](https://facebook.com/medelincoffee)
- 🤖 Telegram Bot: [@MedelinBot](https://t.me/MedelinBot)
- 📲 Telegram Channel: [@MedelinCafe](https://t.me/MedelinCafe)

### 🐛 Технічна підтримка

- 🔧 Issues: [GitHub Issues](https://github.com/gleb226/MedelinBot/issues)
- 📖 Wiki: [GitHub Wiki](https://github.com/gleb226/MedelinBot/wiki)
- 💬 Discussions: [GitHub Discussions](https://github.com/gleb226/MedelinBot/discussions)

---

## 🙏 Подяки

Особлива подяка всім, хто робить Medelin особливим:

- 👨‍🍳 Нашим бариста за любов до кави
- 🎨 Дизайнерам за чудовий інтерфейс
- 🧪 Тестувальникам за терпіння
- ❤️ Нашим гостям за підтримку та відгуки
- 🇺🇦 Ужгороду за натхнення
- 💻 Open Source спільноті за інструменти

---

## ⭐ Star History

[![Star History Chart](https://api.star-history.com/svg?repos=gleb226/MedelinBot&type=Date)](https://star-history.com/#gleb226/MedelinBot&Date)

---

## 🎯 Чому саме Medelin?

> *"У Medelin ми віримо, що кожна чашка кави — це маленька подорож. Наш бот створений, щоб зробити цю подорож ще
зручнішою та приємнішою."*

### Наші цінності

- ☕ **Якість**: Лише найкращі зерна
- 💚 **Екологічність**: Підтримка локальних постачальників
- 🤝 **Спільнота**: Створюємо затишний простір
- 🚀 **Інновації**: Технології на службі комфорту
- 🇺🇦 **Україна**: Горді бути українцями

---

<div align="center">





</div>

---

<div align="center">

**Зроблено з ❤️ та ☕ в Ужгороді**

[⬆ Повернутися до початку](#-medelinbot)

---

*Насолоджуйся кожною чашкою з Medelin!* 🇺🇦

</div>
