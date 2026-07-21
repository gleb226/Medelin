<div align="center">

# 🌐 MedelinSite

**The public website of Medelin Coffee Roasters — coffee catalogue, orders, locations**

[![Live](https://img.shields.io/badge/🌐_Live-medelin.onrender.com-6F4E37?style=for-the-badge)](https://medelin.onrender.com)
[![HTML5](https://img.shields.io/badge/HTML5-E34F26?style=for-the-badge&logo=html5&logoColor=white)](https://developer.mozilla.org/en-US/docs/Web/HTML)
[![CSS3](https://img.shields.io/badge/CSS3_BEM-1572B6?style=for-the-badge&logo=css3&logoColor=white)](https://getbem.com/)
[![JavaScript](https://img.shields.io/badge/JavaScript-F7DF1E?style=for-the-badge&logo=javascript&logoColor=black)](https://developer.mozilla.org/en-US/docs/Web/JavaScript)
[![SEO](https://img.shields.io/badge/SEO-Optimized-34A853?style=for-the-badge&logo=google&logoColor=white)](https://medelin.onrender.com)

<br/>

> *A beautiful, fast, responsive website with no framework. Pure HTML, BEM-CSS, and Vanilla JS — and that's more than enough.*

</div>

---

## 📋 Table of Contents

- [Pages](#-pages)
- [File Structure](#-file-structure)
- [Design System](#-design-system)
- [Components & Logic](#-components--logic)
- [API Integration](#-api-integration)
- [Order System](#-order-system)
- [SEO & Performance](#-seo--performance)
- [Responsive Design](#-responsive-design)
- [Admin Panel](#-admin-panel)

---

## 📄 Pages

| URL | File | Purpose |
|---|---|---|
| `/` | `index.html` | Home: landing, about us sections, locations |
| `/pages/beans.html` | `pages/beans.html` | Coffee beans catalogue with shopping cart |
| `/pages/contact.html` | `pages/contact.html` | Our cafés and contact information |
| `/404.html` | `404.html` | Custom 404 error page |
| `/admin-panel` | `admin-panel.html` | Protected admin panel |

---

## 📁 File Structure

```
MedelinSite/
│
├── 📄 index.html              # Home page
├── 📄 404.html                # "Not Found" page
├── 📄 admin-panel.html        # Admin panel (protected)
├── 📄 robots.txt              # Search engine directives
├── 📄 sitemap.xml             # XML sitemap for SEO
│
├── 📂 pages/
│   ├── beans.html             # Coffee beans catalogue
│   └── contact.html           # Locations and contacts
│
└── 📂 assets/
    ├── 📂 css/
    │   ├── style.css          # Main styles (BEM blocks)
    │   ├── responsive.css     # Media queries and responsiveness
    │   ├── 📂 components/
    │   │   └── mobile-menu.css    # Mobile menu
    │   ├── 📂 pages/
    │   │   ├── 404.css            # 404 page styles
    │   │   ├── beans.css          # Coffee page styles
    │   │   └── admin-panel.css    # Admin panel styles
    │   └── 📂 blocks/
    │       └── ...                # BEM blocks (individual components)
    │
    └── 📂 js/
        ├── main.js            # Core logic (cart, payment, Nova Poshta, animations)
        ├── coffee.js          # Coffee catalogue and detail view
        ├── locations.js       # Leaflet map and location cards
        └── 📂 components/
            └── mobile-menu.js # Mobile menu logic
```

---

## 🎨 Design System

### Color Palette

```css
--color-coffee:       #6F4E37  /* Primary — coffee brown */
--color-coffee-dark:  #4A3728  /* Dark accent */
--color-coffee-light: #8B6347  /* Light accent */
--color-cream:        #FDF6EC  /* Cream background */
--color-warm-white:   #FAFAF8  /* Warm white */
--color-muted:        #9E8A7A  /* Muted text */
--color-text:         #2C1810  /* Main text */
```

### Typography

| Font | Weights | Usage |
|---|---|---|
| **Montserrat** | 400–800 | Headings, accent text |
| **Manrope** | 300–800 | Body text, descriptions |
| **Oswald** | 400–700 | Large display headings |
| **Jost** | 300–700 | Buttons, tags, labels |

### BEM Methodology

All styles follow strict BEM architecture:

```html
<!-- Example: product card -->
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
.block {}                  ← Block (independent component)
.block__element {}         ← Element (part of a block)
.block--modifier {}        ← Modifier (state variation)
```

---

## ⚡ Components & Logic

### `main.js` — The Heart of the Site

The central JavaScript file is responsible for:

**1. Loading data from the API**
```javascript
// Stale-while-revalidate caching
// Shows cached data first, then updates from the API in parallel
const data = cache.get(key) || await fetch(endpoint);
```

**2. Shopping Cart**
- Persistence via `localStorage`
- Support for different weight variations (250g)
- Animated counter with badge
- Cart modal with full management

**3. Checkout Flow**
- Step 1: Select delivery method (pickup / courier / Nova Poshta)
- Step 2: Fill in contact details
- Step 3: Select payment method and confirm

**4. Nova Poshta Integration**
- Real-time city search
- Branch and parcel locker search
- Auto-complete from the Nova Poshta API

**5. LiqPay Online Payment**
- Payment form generation
- Callback after successful payment
- Automatic order status update

**6. Order Status Polling**
```javascript
// Checks the status of the last 3 orders every 15 seconds
setInterval(pollStatuses, 15000);
```

---

### `coffee.js` — Coffee Catalogue

```
Load 27+ coffee items from the API
     │
     ▼
Categorise by quality_score:
     ├── Commercial (no score or score = 0)
     ├── Specialty Espresso (score present, roast = espresso)
     └── Specialty Filter (score present, roast = filter)
     │
     ▼
Render in 3 sections with different colour themes:
     ├── 🟢 Commercial (#D5DEDA - grey-green)
     ├── 🟡 Specialty Espresso (#FFF4D1 - warm yellow)
     └── 🟠 Specialty Filter (#FFEFE0 - peach)
     │
     ▼
Filtering (type + roast level)
     │
     ▼
Detail card on click (with history.pushState)
```

**The bean detail card includes:**
- Full name and description
- Bean photo
- Technical parameters: roast, processing, harvest, altitude, variety
- Flavour descriptors
- Quality score (SCA Score) — specialty only
- "Add to Cart" button + mobile sticky panel

---

### `locations.js` — Map & Locations

- Renders location cards with photos and addresses
- Interactive **Leaflet.js** map with markers
- Popups on marker click
- Modals with detailed information: photos, description, amenities, opening hours
- "Get Directions" button → Google Maps

---

### Mobile Menu

```
Burger icon (3 lines)
     │
     ▼
Animated transform → Cross (CSS animation)
     │
     ▼
Full-screen menu opens with overlay
     ├── Logo
     ├── Navigation links
     └── Footer hint
```

---

## 🔌 API Integration

The site communicates with the backend via REST API:

| Endpoint | Method | Description |
|---|---|---|
| `/api/coffee` | GET | Full coffee beans catalogue |
| `/api/locations` | GET | List of café locations |
| `/api/socials` | GET | Contacts and social media |
| `/api/orders` | POST | Create a new order |
| `/api/orders/{id}` | GET | Details of a specific order |
| `/api/nova-poshta/cities` | GET | Nova Poshta city search |
| `/api/nova-poshta/warehouses` | GET | Nova Poshta branch search |
| `/api/liqpay/form` | POST | Generate payment form |
| `/api/client-error` | POST | Client-side error logging |

**Request caching:**
```javascript
// Requests are cached with a timestamp parameter for forced refresh
fetch(`/api/coffee?t=${Date.now()}`)
```

---

## 🛒 Order System

### Delivery Methods

| Method | Details |
|---|---|
| 🏠 **Pickup** | Select a location from the list of cafés |
| 🚗 **Courier** | Enter delivery address manually |
| 📦 **Nova Poshta** | Search for city + branch / parcel locker |
| 🪑 **In-venue** | Order to the table (enter table number) |

### Payment Methods

| Method | Description |
|---|---|
| 💳 **Card (LiqPay)** | Online payment, automatic order confirmation |
| 📱 **Apple Pay / Google Pay** | Via LiqPay |
| 💵 **Cash on delivery** | Manual confirmation by administrator |

---

## 🔍 SEO & Performance

### Meta Tags (on every page)
```html
<title>Coffee Beans - Medelin Coffee</title>
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
Disallow: /admin-panel     ← Protects the admin panel from indexing
Sitemap: https://medelin.onrender.com/sitemap.xml
```

### Performance
- **Gzip compression** via Nginx for CSS, JS, HTML, JSON
- **Static asset caching** (7 days) via Cache-Control
- **Preconnect** to Google Fonts for faster font loading
- **Cache-busting** via `?v=3.0` parameter on CSS/JS files
- **Stale-While-Revalidate** — instant display of cached data

---

## 📱 Responsive Design

The site is fully responsive and tested on:

| Device | Width |
|---|---|
| 📱 Mobile (portrait) | < 480px |
| 📱 Mobile (landscape) | 480px – 768px |
| 💻 Tablet | 768px – 1024px |
| 🖥️ Desktop | > 1024px |
| 🖥️ Wide | > 1440px |

**Mobile experience highlights:**
- Full-screen burger menu
- Sticky add-to-cart panel on the bean detail card
- Touch-friendly buttons (min. 44px)
- Horizontal card scrolling on tablets

---

## 🔒 Admin Panel

Available at `/admin-panel` — protected by FastAPI server-side logic (not just a JS check).

**Features:**
- 📦 Coffee catalogue management (CRUD + photos)
- 📋 View and manage orders (active / archive)
- 📍 Location management (description, photos, amenities, coordinates)
- 👥 Team management (roles: owner, admin, staff)
- 🔗 Social media and contact management
- 📊 Sales statistics

---

<div align="center">

**🌐 [Open the site](https://medelin.onrender.com)** · **[⬆️ General README](../README.md)**

☕ *Made with love for coffee and clean code*

© 2026 Medelin

</div>
