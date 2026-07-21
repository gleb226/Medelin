<div align="center">

# ☕ Medelin Coffee Roasters

**Повноцінна цифрова екосистема для кав'ярні — від замовлення до доставки**

[![Live Site](https://img.shields.io/badge/🌐_Сайт-medelin.onrender.com-6F4E37?style=for-the-badge)](https://medelin.onrender.com)
[![Bot](https://img.shields.io/badge/🤖_Telegram-@MedelnBot-2CA5E0?style=for-the-badge)](https://t.me/MedelnBot)
[![Python](https://img.shields.io/badge/Python-3.11-3776AB?style=for-the-badge&logo=python&logoColor=white)](https://python.org)
[![Docker](https://img.shields.io/badge/Docker-Containerized-2496ED?style=for-the-badge&logo=docker&logoColor=white)](https://docker.com)
[![MongoDB](https://img.shields.io/badge/MongoDB-Database-47A248?style=for-the-badge&logo=mongodb&logoColor=white)](https://mongodb.com)
[![Render](https://img.shields.io/badge/Hosted_on-Render-46E3B7?style=for-the-badge)](https://render.com)

<br/>

> *Medelin — це не просто кав'ярня. Це досвід. І ця система створена, щоб кожна взаємодія — від перегляду меню до отримання замовлення — була бездоганною.*

</div>

---

## 📖 Що це таке?

**Medelin Coffee Roasters** — це монорепозиторій, що містить повну цифрову інфраструктуру для мережі кав'ярень в Ужгороді. Проект складається з двох взаємопов'язаних компонентів, які разом утворюють єдину продуктивну систему:

| Компонент | Опис |
|---|---|
| 🌐 **MedelinSite** | Публічний вебсайт з каталогом кави, інформацією про локації, кошиком і оформленням замовлень |
| 🤖 **MedelinBot** | Telegram-бот для управління бізнесом: замовлення, склад, персонал, статистика, фінанси |

Обидва компоненти живуть в одному Docker-контейнері і деплояться одним командою на [Render](https://render.com).

---

## 🏛️ Архітектура системи

```
┌─────────────────────────────────────────────────────────────────┐
│                        Docker Container                         │
│                                                                 │
│   ┌─────────────────────────────────────────────────────────┐   │
│   │                    Nginx (Port 80)                      │   │
│   │  ┌───────────────────┐    ┌───────────────────────┐    │   │
│   │  │  Static Site      │    │   Reverse Proxy       │    │   │
│   │  │  /usr/share/nginx │    │   /api/ → :8000       │    │   │
│   │  │  /html/           │    │   /admin-panel → :8000│    │   │
│   │  └───────────────────┘    └───────────────────────┘    │   │
│   └─────────────────────────────────────────────────────────┘   │
│                              │                                  │
│   ┌───────────────────────────▼────────────────────────────┐    │
│   │            FastAPI + Uvicorn (Port 8000)               │    │
│   │                                                        │    │
│   │   ┌─────────────────┐   ┌──────────────────────────┐  │    │
│   │   │   REST API      │   │   Telegram Bot (aiogram) │  │    │
│   │   │   /api/coffee   │   │   Polling mode           │  │    │
│   │   │   /api/orders   │   │   FSM State Machine      │  │    │
│   │   │   /api/locations│   │   Admin Panel via TG     │  │    │
│   │   └────────┬────────┘   └──────────────────────────┘  │    │
│   └────────────┼───────────────────────────────────────────┘    │
│                │                                                 │
│   ┌────────────▼───────────────────────────────────────────┐    │
│   │               APScheduler (Background Jobs)            │    │
│   │    cleanup_old_data | send_monthly_stats               │    │
│   └────────────────────────────────────────────────────────┘    │
└─────────────────────────────────────────────────────────────────┘
                              │
              ┌───────────────▼────────────────┐
              │      MongoDB Atlas / Local      │
              │   Collections: users, orders,  │
              │   coffee, locations, admins,    │
              │   sales, active_orders         │
              └────────────────────────────────┘
```

---

## 🚀 Стек технологій

### Backend
| Технологія | Версія | Призначення |
|---|---|---|
| Python | 3.11 | Основна мова |
| FastAPI | 0.135 | REST API для сайту |
| aiogram | 3.26 | Telegram Bot Framework |
| Uvicorn | 0.34 | ASGI-сервер |
| Motor | 3.7 | Асинхронний MongoDB-драйвер |
| APScheduler | 3.11 | Планувальник фонових задач |
| LiqPay SDK | 1.0.6 | Онлайн-оплата |
| Pillow | 11.1 | Обробка зображень |
| aiohttp | 3.13 | HTTP-клієнт (Nova Poshta API) |

### Frontend
| Технологія | Призначення |
|---|---|
| Vanilla HTML/CSS/JS | Без фреймворків — чисто та швидко |
| BEM Methodology | Структурована CSS-архітектура |
| Font Awesome 6.5 | Іконки |
| Google Fonts | Montserrat, Manrope, Oswald, Jost |
| Leaflet.js | Інтерактивна карта локацій |

### Infrastructure
| Технологія | Призначення |
|---|---|
| Docker | Контейнеризація всього стеку |
| Nginx | Статика + Reverse Proxy |
| MongoDB | Основна база даних |
| Render | Хостинг (PaaS) |
| GitHub | Контроль версій (гілка `releases`) |

---

## 📁 Структура репозиторію

```
Medelin/
├── 📄 Dockerfile              # Єдиний образ для всього стеку
├── 📄 docker-compose.yml      # Локальне середовище (+ MongoDB)
├── 📄 nginx.conf              # Конфігурація Nginx
├── 📄 start.sh                # Точка входу контейнера
├── 📄 .gitignore              # Ігноровані файли (включаючи .env)
│
├── 📂 MedelinBot/             # Telegram-бот та REST API
│   ├── main.py                # Точка входу (Bot + API разом)
│   ├── api.py                 # FastAPI маршрути
│   ├── bot.py                 # Ініціалізація бота
│   ├── requirements.txt       # Python-залежності
│   └── app/
│       ├── common/            # Спільні інстанси (bot, config)
│       ├── databases/         # MongoDB-репозиторії
│       ├── handlers/          # Telegram-хендлери
│       ├── keyboards/         # Inline та Reply клавіатури
│       └── utils/             # Утиліти (кеш, планувальник, NP)
│
└── 📂 MedelinSite/            # Статичний вебсайт
    ├── index.html             # Головна сторінка
    ├── 404.html               # Кастомна сторінка помилки
    ├── admin-panel.html       # Веб-панель адміністратора
    ├── robots.txt             # SEO директиви
    ├── sitemap.xml            # Карта сайту
    ├── pages/
    │   ├── beans.html         # Каталог кави в зернах
    │   └── contact.html       # Локації та контакти
    └── assets/
        ├── css/               # BEM-стилі (style.css, responsive.css, pages/)
        └── js/                # Логіка (main.js, coffee.js, locations.js)
```

---

## 🌟 Ключові можливості системи

### 🛒 Для покупця (сайт)
- **Каталог кави в зернах** — комерційні та спешелті сорти з детальними картками
- **Фільтрація** — за типом (комерційна / спешелті) та ступенем обсмаження
- **Детальна карточка зерна** — дескриптори, процесинг, врожай, висота, оцінка якості
- **Кошик** — з персистентністю через localStorage
- **Оформлення замовлення** — вибір способу отримання: самовивіз, кур'єр або Нова Пошта
- **Онлайн-оплата** через LiqPay (картка, Apple Pay, Google Pay)
- **Відстеження замовлення** — живе оновлення статусу без перезавантаження сторінки
- **Карта закладів** — інтерактивна Leaflet-карта з усіма локаціями
- **Адаптивний дизайн** — ідеально на будь-якому пристрої

### 🤖 Для адміністратора (бот)
- **Управління замовленнями** — прийом, підтвердження, відхилення, виконання
- **Управління каталогом** — додавання/редагування/видалення позицій кави
- **Управління локаціями** — оновлення інформації про кав'ярні
- **Управління персоналом** — додавання/видалення членів команди та їхніх ролей
- **Управління контактами та соцмережами** — актуальне оновлення в реальному часі
- **Фінансова статистика** — продажі за день, тиждень, місяць з детальною розбивкою
- **Автоматичні звіти** — щомісячна статистика надсилається власнику автоматично
- **Сповіщення** — миттєве повідомлення при кожному новому замовленні

---

## ⚙️ Швидкий старт

### Вимоги
- Docker + Docker Compose
- MongoDB Atlas або локальний MongoDB
- Telegram Bot Token (від [@BotFather](https://t.me/BotFather))
- LiqPay ключі (якщо потрібна оплата)
- Nova Poshta API ключ (якщо потрібна доставка)

### 1. Клонування репозиторію
```bash
git clone https://github.com/gleb226/Medelin.git
cd Medelin
```

### 2. Налаштування змінних середовища
```bash
cp MedelinBot/.env.docker.example MedelinBot/.env
# Заповніть всі значення у .env
```

Приклад `.env`:
```env
BOT_TOKEN=your_telegram_bot_token
MONGO_URI=mongodb://localhost:27017/medelin
MONGO_DB_NAME=medelin
ADMIN_TELEGRAM_IDS=123456789,987654321
LIQPAY_PUBLIC_KEY=your_liqpay_public_key
LIQPAY_PRIVATE_KEY=your_liqpay_private_key
NP_API_KEY=your_nova_poshta_api_key
WEB_APP_URL=https://your-domain.com
```

### 3. Запуск локально (з Docker Compose)
```bash
docker-compose up --build
```

Після запуску:
- 🌐 Сайт: `http://localhost`
- 🔧 API: `http://localhost/api/`
- 🗄️ MongoDB: `mongodb://localhost:27017`

### 4. Деплой на Render
1. Підключіть репозиторій до Render
2. Виберіть тип сервісу: **Web Service**
3. Runtime: **Docker**
4. Branch: `releases`
5. Додайте всі змінні середовища через Render Dashboard
6. Натисніть **Deploy**

---

## 🔐 Безпека

- Файл `.env` включено до `.gitignore` — жодних секретів у репозиторії
- Nginx заблоковує доступ до прихованих файлів (`.env`, `.sql`, `.bak` тощо)
- Адмін-панель (`/admin-panel`) закрита через серверну логіку FastAPI
- Пошуковики (robots.txt) не індексують `/admin-panel`
- Усі секретні ключі передаються виключно через змінні середовища

---

## 🗃️ База даних MongoDB

| Колекція | Призначення |
|---|---|
| `users` | Telegram-користувачі та їхні дані |
| `orders` | Всі замовлення (архів) |
| `active_orders` | Поточні активні замовлення |
| `coffee_beans` | Каталог кавових зерен |
| `locations` | Локації кав'ярень |
| `admins` | Список адміністраторів та власника |
| `contacts` | Соціальні мережі та контакти |
| `sales` | Фінансова статистика продажів |

---

## 📊 Потік замовлення

```
Покупець на сайті
     │
     ▼
Обирає каву → Додає в кошик → Оформляє замовлення
     │
     ▼
Вибирає спосіб доставки (самовивіз / кур'єр / НП)
     │
     ▼
Вибирає спосіб оплати (LiqPay / готівка)
     │
     ├─── LiqPay → Оплата онлайн → Автопідтвердження
     │
     └─── Готівка → Замовлення у стані "очікує підтвердження"
                         │
                         ▼
              Адмін отримує сповіщення в Telegram
                         │
                         ▼
              Підтверджує / відхиляє замовлення
                         │
                         ▼
              Покупець бачить оновлений статус на сайті
```

---

## 🤝 Розробка

### Гілки
| Гілка | Призначення |
|---|---|
| `releases` | Production-гілка, Render відслідковує її |
| `backup_before_cleanup` | Резервна копія до великого рефакторингу |

### Підключення до бота в dev-режимі
```bash
cd MedelinBot
pip install -r requirements.txt
python main.py
```

---

## 📄 Ліцензія та авторство

Проект розроблений для **Medelin Coffee Roasters** (Ужгород, Україна).  
Всі права захищені © 2024–2026 Medelin.

---

<div align="center">

☕ *Зроблено з любов'ю до кави та чистого коду*

**[Сайт](https://medelin.onrender.com)** · **[Telegram Бот](https://t.me/MedelnBot)** · **[GitHub](https://github.com/gleb226/Medelin)**

</div>
