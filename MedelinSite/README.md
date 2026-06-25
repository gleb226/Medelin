# 🌐 Medelin Coffee — Website

<div align="center">

![Medelin Website](https://img.shields.io/badge/Medelin-Website-brown?style=for-the-badge)

**Офіційний веб-сайт кав'ярні Medelin в Ужгороді 🇺🇦**

[![HTML5](https://img.shields.io/badge/HTML5-E34F26?style=flat-square&logo=html5&logoColor=white)](https://html.spec.whatwg.org/)
[![CSS3](https://img.shields.io/badge/CSS3-1572B6?style=flat-square&logo=css3&logoColor=white)](https://www.w3.org/Style/CSS/)
[![BEM](https://img.shields.io/badge/BEM-Methodology-29BdfD?style=flat-square)](https://getbem.com/)
[![Responsive](https://img.shields.io/badge/Responsive-Mobile--First-success?style=flat-square)](https://developer.mozilla.org/en-US/docs/Learn/CSS/CSS_layout/Responsive_Design)

[Особливості](#-особливості) • [Структура](#-структура-проекту) • [Встановлення](#-встановлення) • [Сторінки](#-сторінки-сайту) • [Технології](#-технології)

</div>

---

## 📖 Зміст

- [Про проект](#-про-проект)
- [Особливості](#-особливості)
- [Структура проекту](#-структура-проекту)
- [Сторінки сайту](#-сторінки-сайту)
- [Технології](#-технології)
- [Встановлення](#-встановлення)
- [Використання](#-використання)
- [Дизайн](#-дизайн)
- [Адаптивність](#-адаптивність)
- [Roadmap](#-roadmap)
- [Контакти](#-контакти)

---

## 🎯 Про проект

**Medelin Coffee Website** — це багатосторінковий, повністю адаптивний веб-сайт для мережі кав'ярень Medelin в Ужгороді. Створений з використанням чистого HTML5 та CSS3 без фреймворків, демонструє сучасні підходи до верстки та дизайну.

### 🌟 Ключові моменти

- 📱 **100% Responsive** — працює на всіх пристроях
- 🎨 **Сучасний дизайн** — естетика та функціональність
- ⚡ **Швидкість** — оптимізовані зображення та код
- 🏗️ **БЕМ методологія** — чистий та підтримуваний код
- ♿ **Accessibility** — доступність для всіх користувачів
- 🎯 **SEO-friendly** — семантична розмітка

---

## ✨ Особливості

### 🎨 Дизайн

- **Кавова палітра**
    - Кремовий (#f7f3e9)
    - Темно-коричневий (#3c2f2f)
    - Кавовий (#8b5e3c)
    - Оливковий (#5c6447)

- **Типографіка**
    - Playfair Display — заголовки
    - Montserrat — основний текст
    - Гармонійна ієрархія

- **Анімації**
    - Smooth transitions (0.3s)
    - Hover effects
    - Transform animations
    - Fade-in при скролі

### 📐 Верстка

- **CSS Grid + Flexbox**
    - Сучасні layout техніки
    - Гнучкі сітки
    - Auto-fill columns
    - Gap spacing

- **БЕМ методологія**

    ```css
    .product-card {
    } /* Block */
    .product-card__image {
    } /* Element */
    .product-card__title {
    } /* Element */
    .product-card--featured {
    } /* Modifier */
    ```

- **CSS Variables**
    ```css
    :root {
        --cream: #f7f3e9;
        --dark-brown: #3c2f2f;
        --coffee: #8b5e3c;
        --olive: #5c6447;
        --spacing: 1.5rem;
    }
    ```

### 🎯 Оптимізація

- **Зображення**
    - Unsplash CDN
    - WebP формат
    - Lazy loading (готовий до впровадження)
    - Responsive images

- **CSS**
    - Мінімізація селекторів
    - Оптимізовані медіа-запити
    - CSS Grid замість float
    - Відсутність !important

- **HTML**
    - Семантичні теги
    - Валідна розмітка (W3C)
    - Meta теги для SEO
    - Open Graph для соцмереж

---

## 📁 Структура проекту

```
MedelinSite/
│
├── 📄 index.html                    # Головна сторінка
│
├── 📂 css/
│   ├── style.css                   # Основні стилі (~2000 рядків)
│   └── responsive.css              # Медіа-запити (10 брейкпоінтів)
│
├── 📂 js/
│   └── main.js                     # JavaScript (майбутні функції)
│
└── 📂 pages/
    ├── 📂 menu/
    │   └── menu.html               # Меню (кава, чай, десерти)
    ├── 📂 about/
    │   └── about.html              # Про кав'ярню
    ├── 📂 gallery/
    │   └── gallery.html            # Фото галерея (18 фото)
    ├── 📂 events/
    │   └── events.html             # Події та івенти
    ├── 📂 blog/
    │   └── blog.html               # Кавовий блог
    └── 📂 contact/
        └── contact.html            # Контакти + бронювання
```

### 📊 Статистика коду

```
Файли:          7 HTML сторінок
CSS:            ~3000 рядків
JavaScript:     ~100 рядків (в розробці)
Брейкпоінти:    10 responsive точок
Зображення:     25+ оптимізованих фото
Компоненти:     15+ переіспользуваних блоків
```

---

## 🌐 Сторінки сайту

### 1. 🏠 Головна (index.html)

**Секції:**

- 🎯 Hero Section з CTA кнопками
- ☕ Популярні напої (6 карток)
- 💎 Переваги (4 блоки)
- 📍 Локації (2 кав'ярні)
- ⭐ Відгуки клієнтів (3 картки)
- 📱 Footer з соцмережами

**Особливості:**

- Full-screen hero з gradient overlay
- Grid layout для карток
- Sticky navigation
- Smooth scroll до секцій



### 3. 🏢 Про нас (pages/about/about.html)

**Контент:**

- 📜 Історія кав'ярні
- 🎯 Наша місія та цінності
- 👥 Команда (3 ключові особи)
- ☕ Процес приготування кави
- 🌱 Екологічність та соціальна відповідальність
- 🏆 Досягнення та нагороди

**Елементи:**

- Timeline з історією
- Team cards з фото
- Process infographic
- Awards showcase

### 4. 📸 Галерея (pages/gallery/gallery.html)

**18 фото:**

- Інтер'єр кав'ярні (6)
- Кавові напої (6)
- Десерти та випічка (4)
- Атмосфера та гості (2)

**Технічна реалізація:**

- CSS Grid Masonry layout
- Lightbox для перегляду
- Hover overlay з описом
- Lazy loading
- Категорії з фільтрацією

### 5. 🎉 Події (pages/events/events.html)

**6 типів подій:**

- 🎓 Майстер-класи бариста (щосуботи, 11:00)
- 🎵 Жива музика (п'ятниці, 19:00)
- ☕ Кавові дегустації (щомісяця)
- 📚 Книжковий клуб (вівторки, 18:00)
- 🥐 Бранч вихідного дня (сб-нд, 10:00)
- 🎲 Настільні ігри (середи, 17:00)

**Картки подій:**

- Дата та час
- Опис
- Вартість участі
- Реєстрація

### 6. ✍️ Блог (pages/blog/blog.html)

**6 статей:**

- "Мистецтво латте-арт: від основ до шедеврів"
- "Історія кави: від Ефіопії до вашої чашки"
- "Як обрати ідеальне зерно для домашньої кави"
- "Топ-5 помилок при приготуванні еспресо"
- "Кава та здоров'я: що каже наука"
- "Сезонні напої: осінні кавові рецепти"

**Формат:**

- Featured image
- Категорія та дата
- Анонс (150 символів)
- Автор
- Час читання

### 7. 📞 Контакти (pages/contact/contact.html)

**Інформація:**

#### 📍 Локація 1 - Центр

- **Адреса:** вул. Корзо, 15, Ужгород
- **Телефон:** +380 XX XXX-XX-XX
- **Години:** Пн-Пт 8:00-22:00, Сб-Нд 9:00-23:00
- **Google Maps** інтеграція

#### 📍 Локація 2 - Поштова

- **Адреса:** вул. Поштова, 27, Ужгород
- **Телефон:** +380 XX XXX-XX-XX
- **Години:** Пн-Нд 8:00-21:00
- **Google Maps** інтеграція

**Форма бронювання:**

```html
- Ім'я та прізвище - Email - Телефон - Дата візиту (date picker) - Час візиту (time picker) - Кількість гостей (1-10) -
Локація (select) - Коментар (textarea)
```

**Соцмережі:**

- 📱 Instagram
- 👥 Facebook
- 🎵 TikTok
- 🤖 Telegram Bot

---

## 🛠 Технології

### Frontend

```
HTML5
├── Семантичні теги (header, nav, main, section, article, footer)
├── Forms з HTML5 validation
├── Meta tags для SEO
└── Open Graph для соцмереж

CSS3
├── Grid Layout
├── Flexbox
├── CSS Variables (Custom Properties)
├── Transitions & Transforms
├── Media Queries (Mobile-First)
├── Pseudo-elements (::before, ::after)
└── БЕМ методологія

JavaScript (планується)
├── Form validation
├── Smooth scroll
├── Lazy loading
├── Modal windows
└── Menu filtering
```

### Шрифти

```css
/* Заголовки */
font-family: 'Playfair Display', serif;

/* Основний текст */
font-family: 'Montserrat', sans-serif;
```

**Підключення:**

```html
<link rel="preconnect" href="https://fonts.googleapis.com" />
<link
    href="https://fonts.googleapis.com/css2?family=Playfair+Display:wght@400;700&family=Montserrat:wght@300;400;500;600&display=swap"
    rel="stylesheet"
/>
```

### Зображення

- **CDN:** Unsplash
- **Формат:** WebP з fallback на JPEG
- **Оптимізація:** Responsive images
- **Завантаження:** Lazy loading ready

---

## 🚀 Встановлення

### Швидкий старт

#### 1. Клонування репозиторію

```bash
git clone https://github.com/gleb226/MedelinSite.git
cd MedelinSite
```

#### 2. Відкриття в браузері

**Варіант A: Прямо відкрити файл**

```bash
# macOS
open index.html

# Windows
start index.html

# Linux
xdg-open index.html
```

**Варіант B: Live Server (рекомендовано)**

1. Встановіть [VS Code](https://code.visualstudio.com/)
2. Встановіть розширення [Live Server](https://marketplace.visualstudio.com/items?itemName=ritwickdey.LiveServer)
3. Правий клік на `index.html` → "Open with Live Server"
4. Сайт відкриється на `http://localhost:5500`

**Варіант C: Python HTTP Server**

```bash
# Python 3
python -m http.server 8000

# Python 2
python -m SimpleHTTPServer 8000
```

Відкрийте `http://localhost:8000` у браузері

**Варіант D: Node.js http-server**

```bash
# Встановити глобально
npm install -g http-server

# Запустити
http-server

# Відкрити http://localhost:8080
```

---

## 💻 Використання

### Навігація

```
Головна       → index.html
Меню          → pages/menu/menu.html
Про нас       → pages/about/about.html
Галерея       → pages/gallery/gallery.html
Події         → pages/events/events.html
Блог          → pages/blog/blog.html
Контакти      → pages/contact/contact.html
```

### Редагування контенту

#### Зміна кольорової схеми

```css
/* css/style.css */
:root {
    --cream: #f7f3e9; /* Змініть на свій колір */
    --dark-brown: #3c2f2f;
    --coffee: #8b5e3c;
    --olive: #5c6447;
}
```

#### Додавання нової позиції в меню

```html
<!-- pages/menu/menu.html -->
<div class="product-card">
    <img src="your-image.jpg" alt="Назва напою" class="product-card__image" />
    <h3 class="product-card__title">Назва напою</h3>
    <p class="product-card__description">Опис напою...</p>
    <p class="product-card__price">85₴</p>
    <button class="product-card__button">Замовити</button>
</div>
```

#### Зміна контактної інформації

```html
<!-- pages/contact/contact.html -->
<p class="location-card__address">вул. Ваша, 123, Місто</p>
<p class="location-card__phone">+380 XX XXX-XX-XX</p>
```

---

## 🎨 Дизайн

### Колірна палітра

```css
Кремовий:           #f7f3e9 (фон)
Темно-коричневий:   #3c2f2f (текст)
Кавовий:            #8b5e3c (акценти)
Оливковий:          #5c6447 (додатковий)
Білий:              #ffffff
Чорний:             #000000
```

### Типографічна шкала

```css
h1 → 3.5rem   (56px)
h2 → 2.5rem   (40px)
h3 → 2rem     (32px)
h4 → 1.5rem   (24px)
p  → 1rem     (16px)
small → 0.875rem (14px)
```

### Spacing система

```css
XS  → 0.5rem  (8px)
S   → 1rem    (16px)
M   → 1.5rem  (24px)
L   → 2rem    (32px)
XL  → 3rem    (48px)
XXL → 4rem    (64px)
```

### Компоненти

**Кнопки:**

```css
.btn-primary   → Основна дія (коричневий фон)
.btn-secondary → Вторинна дія (outline)
.btn-large     → Великий розмір
.btn-small     → Маленький розмір
```

**Картки:**

```css
.product-card  → Картка товару
.event-card    → Картка події
.blog-card     → Картка статті
.team-card     → Картка члена команди
```

---

## 📱 Адаптивність

### Брейкпоінти (Mobile-First)

```css
/* Дуже маленькі телефони */
@media (min-width: 320px) {
}

/* Маленькі телефони */
@media (min-width: 360px) {
}

/* Великі телефони */
@media (min-width: 480px) {
}

/* Маленькі планшети */
@media (min-width: 600px) {
}

/* Планшети */
@media (min-width: 768px) {
}

/* Великі планшети */
@media (min-width: 900px) {
}

/* Ноутбуки */
@media (min-width: 1024px) {
}

/* Десктопи */
@media (min-width: 1200px) {
}

/* Великі екрани */
@media (min-width: 1400px) {
}

/* 4K екрани */
@media (min-width: 1920px) {
}
```

### Приклади адаптації

**Grid колонки:**

```css
/* Мобільні: 1 колонка */
.products-grid {
    grid-template-columns: 1fr;
}

/* Планшети: 2 колонки */
@media (min-width: 768px) {
    .products-grid {
        grid-template-columns: repeat(2, 1fr);
    }
}

/* Десктоп: 3 колонки */
@media (min-width: 1024px) {
    .products-grid {
        grid-template-columns: repeat(3, 1fr);
    }
}
```

---

## 🔧 Налаштування

### Зміна головного зображення

```html
<!-- index.html -->
<section class="hero" style="background-image: url('your-image.jpg');"></section>
```

### Додавання Google Analytics

```html
<!-- Перед </head> -->
<script async src="https://www.googletagmanager.com/gtag/js?id=GA_MEASUREMENT_ID"></script>
<script>
    window.dataLayer = window.dataLayer || [];
    function gtag() {
        dataLayer.push(arguments);
    }
    gtag('js', new Date());
    gtag('config', 'GA_MEASUREMENT_ID');
</script>
```

### Додавання favicon

```html
<link rel="icon" type="image/png" href="favicon.png" /> <link rel="apple-touch-icon" href="apple-touch-icon.png" />
```

---

### Можливі покращення

- [ ] JavaScript для інтерактивності
- [ ] Backend інтеграція (Node.js/PHP)
- [ ] Анімації при скролі (AOS/GSAP)
- [ ] Lightbox для галереї
- [ ] Фільтри для меню та блогу
- [ ] Форма замовлення онлайн
- [ ] Інтеграція з платіжними системами
- [ ] Newsletter subscription
- [ ] Відгуки через Google Reviews API

---

## 🧪 Тестування

### Браузери

Протестовано та працює на:

- ✅ Chrome 90+
- ✅ Firefox 88+
- ✅ Safari 14+
- ✅ Edge 90+
- ✅ Opera 76+

### Пристрої

- ✅ iPhone (6/7/8/X/11/12/13)
- ✅ iPad (Air/Pro)
- ✅ Android phones (різні розміри)
- ✅ Android tablets
- ✅ Ноутбуки (13"/15"/17")
- ✅ Десктопи (Full HD/2K/4K)

### Валідація

```bash
# HTML валідація
https://validator.w3.org/

# CSS валідація
https://jigsaw.w3.org/css-validator/

# Accessibility
https://wave.webaim.org/

# Performance
https://developers.google.com/speed/pagespeed/insights/
```

---

## 📊 Статистика проекту

<div align="center">

![GitHub stars](https://img.shields.io/github/stars/gleb226/MedelinSite?style=social)
![GitHub forks](https://img.shields.io/github/forks/gleb226/MedelinSite?style=social)

![Last Commit](https://img.shields.io/github/last-commit/gleb226/MedelinSite)
![Code Size](https://img.shields.io/github/languages/code-size/gleb226/MedelinSite)
![Languages](https://img.shields.io/github/languages/count/gleb226/MedelinSite)

**Мова коду:**
![HTML](https://img.shields.io/badge/HTML-74.6%25-E34F26)
![CSS](https://img.shields.io/badge/CSS-21.0%25-1572B6)
![JavaScript](https://img.shields.io/badge/JavaScript-4.4%25-F7DF1E)

</div>

---

## 📄 Ліцензія

```
MIT License

Copyright (c) 2024 Medelin Coffee Website

Дозволяється безкоштовне використання, копіювання, модифікація
та розповсюдження цього програмного забезпечення для навчальних
та комерційних цілей з обов'язковим збереженням цього повідомлення.
```

Повна ліцензія: [LICENSE](./LICENSE)

---

## 👨‍💻 Автор

**Gleb** - _Web Developer_

- GitHub: [@gleb226](https://github.com/gleb226)
- Проект: [MedelinSite](https://github.com/gleb226/MedelinSite)

---

## 📞 Контакти

### 🏪 Кав'ярня Medelin

- 📍 **Локація 1:** вул. Корзо, 15, Ужгород
- 📍 **Локація 2:** вул. Поштова, 27, Ужгород
- 📞 **Телефон:** +380 (XX) XXX-XX-XX
- 📧 **Email:** info@medelin.cafe
- 🌐 **Сайт:** [medelin.cafe](https://medelin.cafe)

### 💬 Соціальні мережі

- 📱 **Instagram:** [@medelin.uzhhorod](https://instagram.com/medelin.uzhhorod)
- 👥 **Facebook:** [Medelin Coffee](https://facebook.com/medelincoffee)
- 🎵 **TikTok:** [@medelin.cafe](https://tiktok.com/@medelin.cafe)
- 🤖 **Telegram:** [@MedelinBot](https://t.me/MedelinBot)

### 🐛 Технічна підтримка

- 💻 **Issues:** [GitHub Issues](https://github.com/gleb226/MedelinSite/issues)
- 📖 **Wiki:** [GitHub Wiki](https://github.com/gleb226/MedelinSite/wiki)

---

## 🙏 Подяки

Особлива вдячність:

- ☕ **Команді Medelin** — за натхнення та підтримку
- 🎨 **Дизайнерській спільноті** — за ідеї та фідбек
- 📸 **Unsplash** — за якісні безкоштовні фото
- 🔤 **Google Fonts** — за чудові шрифти
- 💻 **Open Source спільноті** — за інструменти
- 🇺🇦 **Ужгороду** — за красу та атмосферу

---

## 🌟 Особливі проекти екосистеми Medelin

- 🌐 **[MedelinSite](https://github.com/gleb226/MedelinSite)** — Веб-сайт (цей репозиторій)
- 🤖 **[MedelinBot](https://github.com/gleb226/MedelinBot)** — Telegram бот

---

<div align="center">

### 🎯 Навіщо цей проект?

Цей сайт створений як:

- 📚 **Портфоліо проект** — демонстрація навичок верстки
- 🎓 **Навчальний матеріал** — приклад сучасної верстки
- 💼 **Комерційний проект** — реальний сайт для кав'ярні

---

**Зроблено з ❤️ та ☕ в Ужгороді, Україна 🇺🇦**

_Де код зустрічає дизайн, а кава — технології_

[⬆ Повернутися до початку](#-medelin-coffee--website)

---

[![Visit Website](https://img.shields.io/badge/Visit-Website-FF6B35?style=for-the-badge&logo=google-chrome&logoColor=white)](https://medelin.cafe)
[![View on GitHub](https://img.shields.io/badge/View%20on-GitHub-181717?style=for-the-badge&logo=github&logoColor=white)](https://github.com/gleb226/MedelinSite)
[![Telegram Bot](https://img.shields.io/badge/Telegram-Bot-26A5E4?style=for-the-badge&logo=telegram&logoColor=white)](https://t.me/MedelinBot)

</div>
