<div align="center">

# 🌐 MedelinSite

**Публічний вебсайт Medelin Coffee Roasters — каталог кави, замовлення, локації**

[![Live](https://img.shields.io/badge/🌐_Live-medelin.onrender.com-6F4E37?style=for-the-badge)](https://medelin.onrender.com)
[![HTML5](https://img.shields.io/badge/HTML5-E34F26?style=for-the-badge&logo=html5&logoColor=white)](https://developer.mozilla.org/en-US/docs/Web/HTML)
[![CSS3](https://img.shields.io/badge/CSS3_BEM-1572B6?style=for-the-badge&logo=css3&logoColor=white)](https://getbem.com/)
[![JavaScript](https://img.shields.io/badge/JavaScript-F7DF1E?style=for-the-badge&logo=javascript&logoColor=black)](https://developer.mozilla.org/en-US/docs/Web/JavaScript)
[![SEO](https://img.shields.io/badge/SEO-Optimized-34A853?style=for-the-badge&logo=google&logoColor=white)](https://medelin.onrender.com)

<br/>

> *Красивий, швидкий, адаптивний сайт без жодного фреймворку. Чистий HTML, BEM-CSS та Vanilla JS — і цього більш ніж достатньо.*

</div>

---

## 📋 Зміст

- [Сторінки](#-сторінки)
- [Структура файлів](#-структура-файлів)
- [Дизайн-система](#-дизайн-система)
- [Компоненти та логіка](#-компоненти-та-логіка)
- [API-інтеграція](#-api-інтеграція)
- [Система замовлень](#-система-замовлень)
- [SEO та продуктивність](#-seo-та-продуктивність)
- [Адаптивний дизайн](#-адаптивний-дизайн)
- [Адмін-панель](#-адмін-панель)

---

## 📄 Сторінки

| URL | Файл | Призначення |
|---|---|---|
| `/` | `index.html` | Головна: лендінг, секції про нас, локації |
| `/pages/beans.html` | `pages/beans.html` | Каталог кави в зернах з кошиком |
| `/pages/contact.html` | `pages/contact.html` | Наші кав'ярні та контакти |
| `/404.html` | `404.html` | Кастомна сторінка помилки 404 |
| `/admin-panel` | `admin-panel.html` | Захищена панель адміністратора |

---

## 📁 Структура файлів

```
MedelinSite/
│
├── 📄 index.html              # Головна сторінка
├── 📄 404.html                # Сторінка "Не знайдено"
├── 📄 admin-panel.html        # Адмін-панель (захищена)
├── 📄 robots.txt              # Директиви для пошукових роботів
├── 📄 sitemap.xml             # XML-карта сайту для SEO
│
├── 📂 pages/
│   ├── beans.html             # Каталог кавових зерен
│   └── contact.html           # Локації та контакти
│
└── 📂 assets/
    ├── 📂 css/
    │   ├── style.css          # Головні стилі (BEM-блоки)
    │   ├── responsive.css     # Медіа-запити та адаптивність
    │   ├── 📂 components/
    │   │   └── mobile-menu.css    # Мобільне меню
    │   ├── 📂 pages/
    │   │   ├── 404.css            # Стилі сторінки 404
    │   │   ├── beans.css          # Стилі сторінки кави
    │   │   └── admin-panel.css    # Стилі адмін-панелі
    │   └── 📂 blocks/
    │       └── ...                # BEM-блоки (окремі компоненти)
    │
    └── 📂 js/
        ├── main.js            # Головна логіка (кошик, оплата, NP, анімації)
        ├── coffee.js          # Каталог кави та детальний перегляд
        ├── locations.js       # Карта Leaflet та карточки локацій
        └── 📂 components/
            └── mobile-menu.js # Логіка мобільного меню
```

---

## 🎨 Дизайн-система

### Кольорова палітра

```css
--color-coffee:       #6F4E37  /* Основний — кавовий коричневий */
--color-coffee-dark:  #4A3728  /* Темний акцент */
--color-coffee-light: #8B6347  /* Світлий акцент */
--color-cream:        #FDF6EC  /* Кремовий фон */
--color-warm-white:   #FAFAF8  /* Теплий білий */
--color-muted:        #9E8A7A  /* Приглушений текст */
--color-text:         #2C1810  /* Основний текст */
```

### Типографіка

| Шрифт | Ваги | Застосування |
|---|---|---|
| **Montserrat** | 400–800 | Заголовки, акцентний текст |
| **Manrope** | 300–800 | Основний текст, описи |
| **Oswald** | 400–700 | Великі дисплейні заголовки |
| **Jost** | 300–700 | Кнопки, теги, мітки |

### BEM-методологія

Всі стилі дотримуються суворої BEM-архітектури:

```html
<!-- Приклад: картка товару -->
<article class="product-card">
  <div class="product-card__image product-card__image--bean"></div>
  <div class="product-card__content">
    <h3 class="product-card__title">Ethiopia Yirgacheffe</h3>
    <div class="product-card__price-row">
      <span class="product-card__price">320 ₴ / 250г</span>
      <button class="btn-add-plus">+</button>
    </div>
  </div>
</article>
```

```
.block {}                  ← Блок (незалежний компонент)
.block__element {}         ← Елемент (частина блоку)
.block--modifier {}        ← Модифікатор (варіація стану)
```

---

## ⚡ Компоненти та логіка

### `main.js` — Серце сайту

Центральний JavaScript-файл відповідає за:

**1. Завантаження даних із API**
```javascript
// Стале-while-revalidate кешування
// Спочатку показує кешовані дані, паралельно оновлює з API
const data = cache.get(key) || await fetch(endpoint);
```

**2. Кошик покупок**
- Персистентність через `localStorage`
- Підтримка різних вагових варіацій (250г)
- Анімований лічильник з badge
- Модальне вікно кошика з повним управлінням

**3. Оформлення замовлення**
- Крок 1: Вибір способу отримання (самовивіз / кур'єр / Нова Пошта)
- Крок 2: Заповнення контактних даних
- Крок 3: Вибір способу оплати та підтвердження

**4. Інтеграція з Новою Поштою**
- Пошук міст у реальному часі
- Пошук відділень та поштоматів
- Автозаповнення з API Нової Пошти

**5. Онлайн-оплата LiqPay**
- Генерація форми оплати
- Callback після успішної оплати
- Автоматичне оновлення статусу замовлення

**6. Polling статусу замовлення**
```javascript
// Кожні 15 секунд перевіряє статус останніх 3 замовлень
setInterval(pollStatuses, 15000);
```

---

### `coffee.js` — Каталог кави

```
Завантаження 27+ позицій кави з API
     │
     ▼
Категоризація за quality_score:
     ├── Комерційна (немає score або score = 0)
     ├── Спешелті Еспресо (score є, roast = espresso)
     └── Спешелті Фільтр (score є, roast = filter)
     │
     ▼
Рендеринг у 3 секції з різними кольоровими темами:
     ├── 🟢 Комерційна (#D5DEDA - сіро-зелений)
     ├── 🟡 Спешелті Еспресо (#FFF4D1 - тепло-жовтий)
     └── 🟠 Спешелті Фільтр (#FFEFE0 - персиковий)
     │
     ▼
Фільтрація (тип + ступінь обсмаження)
     │
     ▼
Детальна картка при кліці (з history.pushState)
```

**Детальна картка зерна містить:**
- Повна назва та опис
- Фотографія зерна
- Технічні параметри: обсмаження, процесинг, врожай, висота, різновид
- Дескриптори смаку
- Оцінка якості (SCA Score) — тільки для спешелті
- Кнопка "Додати в кошик" + мобільна sticky-панель

---

### `locations.js` — Карта та локації

- Рендеринг карточок локацій з фото та адресою
- Інтерактивна карта **Leaflet.js** з маркерами
- Спливаючі підказки (popup) при кліці на маркер
- Модальні вікна з детальною інформацією: фото, опис, зручності, графік роботи
- Кнопка "Прокласти маршрут" → Google Maps

---

### Мобільне меню

```
Бургер-іконка (3 лінії)
     │
     ▼
Анімована трансформація → Хрестик (CSS-анімація)
     │
     ▼
Відкриття повноекранного меню з overlay
     ├── Логотип
     ├── Навігаційні посилання
     └── Footer підказка
```

---

## 🔌 API-інтеграція

Сайт спілкується з backend через REST API:

| Endpoint | Метод | Опис |
|---|---|---|
| `/api/coffee` | GET | Весь каталог кавових зерен |
| `/api/locations` | GET | Список локацій кав'ярень |
| `/api/socials` | GET | Контакти та соціальні мережі |
| `/api/orders` | POST | Створення нового замовлення |
| `/api/orders/{id}` | GET | Деталі конкретного замовлення |
| `/api/nova-poshta/cities` | GET | Пошук міст НП |
| `/api/nova-poshta/warehouses` | GET | Пошук відділень НП |
| `/api/liqpay/form` | POST | Генерація форми оплати |
| `/api/client-error` | POST | Логування клієнтських помилок |

**Кешування запитів:**
```javascript
// Запити кешуються з timestamp-параметром для примусового оновлення
fetch(`/api/coffee?t=${Date.now()}`)
```

---

## 🛒 Система замовлень

### Способи отримання

| Спосіб | Деталі |
|---|---|
| 🏠 **Самовивіз** | Вибір локації зі списку кав'ярень |
| 🚗 **Кур'єр** | Введення адреси доставки вручну |
| 📦 **Нова Пошта** | Пошук міста + відділення / поштомату |
| 🪑 **У закладі** | Замовлення до столу (введення номера столу) |

### Способи оплати

| Спосіб | Опис |
|---|---|
| 💳 **Карта (LiqPay)** | Онлайн-оплата, автопідтвердження замовлення |
| 📱 **Apple Pay / Google Pay** | Через LiqPay |
| 💵 **Готівка при отриманні** | Ручне підтвердження адміністратором |

---

## 🔍 SEO та продуктивність

### Мета-теги (на кожній сторінці)
```html
<title>Кава в зернах - Medelin Coffee</title>
<meta name="description" content="...">
<meta name="robots" content="index, follow">
<link rel="canonical" href="https://medelin.onrender.com/...">

<!-- Open Graph -->
<meta property="og:type" content="website">
<meta property="og:title" content="...">
<meta property="og:description" content="...">
<meta property="og:locale" content="uk_UA">

<!-- Twitter Cards -->
<meta name="twitter:card" content="summary_large_image">
```

### sitemap.xml

```xml
<?xml version="1.0" encoding="UTF-8"?>
<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">
  <url>
    <loc>https://medelin.onrender.com/</loc>
    <changefreq>weekly</changefreq>
    <priority>1.0</priority>
  </url>
  <!-- + beans.html, contact.html -->
</urlset>
```

### robots.txt

```
User-agent: *
Allow: /
Disallow: /admin-panel     ← Захист адмін-панелі від індексації
Sitemap: https://medelin.onrender.com/sitemap.xml
```

### Продуктивність
- **Gzip-стиснення** через Nginx для CSS, JS, HTML, JSON
- **Кешування** статичних ресурсів (7 днів) через Cache-Control
- **Preconnect** до Google Fonts для пришвидшення завантаження шрифтів
- **Cache-busting** через `?v=3.0` параметр на CSS/JS файлах
- **Stale-While-Revalidate** — миттєве відображення кешованих даних

---

## 📱 Адаптивний дизайн

Сайт повністю адаптивний і тестований на:

| Пристрій | Ширина |
|---|---|
| 📱 Мобільний (portrait) | < 480px |
| 📱 Мобільний (landscape) | 480px – 768px |
| 💻 Планшет | 768px – 1024px |
| 🖥️ Десктоп | > 1024px |
| 🖥️ Wide | > 1440px |

**Особливості мобільного досвіду:**
- Повноекранне бургер-меню
- Sticky add-to-cart панель в картці зерна
- Touch-friendly кнопки (мін. 44px)
- Горизонтальний скролінг карток для планшетів

---

## 🔒 Адмін-панель

Доступна за `/admin-panel` — захищена серверною логікою FastAPI (не просто JS-перевірка).

**Можливості:**
- 📦 Управління каталогом кави (CRUD + фото)
- 📋 Перегляд та управління замовленнями (активні / архів)
- 📍 Управління локаціями (опис, фото, зручності, координати)
- 👥 Управління командою (ролі: owner, admin, staff)
- 🔗 Управління соцмережами та контактами
- 📊 Статистика продажів

---

<div align="center">

**🌐 [Відкрити сайт](https://medelin.onrender.com)** · **[⬆️ Загальний README](../README.md)**

☕ *Зроблено з любов'ю до кави та чистого коду*

</div>
