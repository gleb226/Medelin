# ☕ Medelin — Coffee Shop Digital Ecosystem

[![Python](https://img.shields.io/badge/Python-3.11+-blue.svg)](https://www.python.org/)
[![Aiogram](https://img.shields.io/badge/Aiogram-3.x-orange.svg)](https://docs.aiogram.dev/)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.1xx-green.svg)](https://fastapi.tiangolo.com/)
[![Nginx](https://img.shields.io/badge/Nginx-Latest-brightgreen.svg)](https://nginx.org/)
[![Docker](https://img.shields.io/badge/Docker-Ready-blue.svg)](https://www.docker.com/)

**Medelin** — це комплексна цифрова екосистема для сучасної кав'ярні, яка поєднує в собі високопродуктивний веб-сайт, інтелектуального Telegram-бота для замовлень та надійну інфраструктуру.

## 🌟 Ключові особливості

### 🖥️ MedelinSite (Frontend)
- **Ultra-fast Static Delivery**: Веб-сайт розроблений як статична сторінка для миттєвого завантаження.
- **Modern UI/UX**: Елегантний дизайн, що передає атмосферу кав'ярні, з повною адаптивністю під мобільні пристрої.
- **Dynamic Menu**: Меню автоматично оновлюється через кеш-файли, що генеруються ботом.
- **SEO Optimized**: Повна підтримка мета-тегів, OpenGraph та sitemap для високих позицій у пошуку.

### 🤖 MedelinBot (Backend & Management)
- **Order Management**: Автоматизований прийом замовлень з підтримкою опцій (молоко, сиропи, тип кави).
- **Admin Panel**: Керування меню, локаціями та контентом сайту безпосередньо через інтерфейс Telegram.
- **Photo Processing**: Розумна обробка зображень (автоматична конвертація у WebP для оптимізації швидкості сайту).
- **Payments Integration**: Підтримка платіжних систем для онлайн-оплати замовлень.

### 🛡️ Infrastructure & Security
- **Nginx Hardening**: Конфігурація з посиленим захистом (CSP, HSTS, security headers).
- **Dockerized**: Повна контейнеризація для легкого розгортання в будь-якому середовищі.
- **Secure by Design**: Жодних секретів у коді, використання змінних середовища та захищених проксі-шляхів.

## 🛠️ Технологічний стек

- **Backend**: Python 3.11, Aiogram 3.x (Bot), FastAPI (API).
- **Frontend**: HTML5, Vanilla CSS (Modern CSS variables), Pure JavaScript.
- **Database**: MongoDB (через Motor для асинхронності).
- **Image Processing**: Pillow (оптимізація та конвертація).
- **Server**: Nginx (Static hosting & Reverse Proxy).
- **Deployment**: Docker, Docker Compose.

## 📂 Структура проекту

```text
.
├── MedelinBot/          # Бекенд: Telegram-бот та API
│   ├── app/             # Основна логіка (handlers, utils, databases)
│   ├── main.py          # Точка входу (запуск бота та API)
│   └── Dockerfile       # Контейнеризація бота
├── MedelinSite/         # Фронтенд: веб-сайт
│   ├── css/             # Стилі (modern CSS)
│   ├── js/              # Інтерактив та логіка меню
│   ├── images/uploads/  # Динамічні завантаження (фото товарів)
│   └── index.html       # Головна сторінка
├── nginx.conf           # Конфігурація Nginx для продакшну
├── docker-compose.yml   # Оркестрація сервісів
└── Dockerfile           # Уніфікований Dockerfile (Bot + Nginx)
```

## 🚀 Швидкий старт (Development)

1. **Налаштуйте змінні середовища**:
   Створіть `.env` у папці `MedelinBot/` на основі `.env.docker.example`.

2. **Запустіть через Docker Compose**:
   ```bash
   docker-compose up --build
   ```

3. **Доступ до сервісів**:
   - Сайт: `http://localhost`
   - API: `http://localhost/api/`
   - Бот: Почне працювати автоматично після встановлення токена.

## 🔧 Конфігурація завантаження фото

Проект використовує інтелектуальну систему збереження фото. При додаванні товару через бота:
1. Фото завантажується з серверів Telegram.
2. Автоматично конвертується у формат **WebP** (85% якості) для мінімальної ваги.
3. Зберігається у папку, яка монтується як спільний об'єм між ботом та Nginx.
4. Шлях до фото автоматично стає доступним на сайті через `/uploads/`.

## 🔒 Безпека (Hardening)

Nginx налаштований з наступними політиками:
- **CSP**: Обмеження виконання сторонніх скриптів.
- **Anti-Clickjacking**: Заборона вбудовування сайту у iframe.
- **MIME Sniffing Prevention**: Примусове використання типів контенту.
- **Proxy Isolation**: Бекенд доступний лише через внутрішній проксі на `/api/`.

---
*Developed with ❤️ for Medelin Coffee Shop.*
