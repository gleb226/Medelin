<div align="center">

# ☕ Medelin Coffee Roasters

**A complete digital ecosystem for a coffee shop — from ordering to delivery**

[![Live Site](https://img.shields.io/badge/🌐_Site-medelin.onrender.com-6F4E37?style=for-the-badge)](https://medelin.onrender.com)
[![Bot](https://img.shields.io/badge/🤖_Telegram-@MedelnBot-2CA5E0?style=for-the-badge)](https://t.me/MedelnBot)
[![Python](https://img.shields.io/badge/Python-3.11-3776AB?style=for-the-badge&logo=python&logoColor=white)](https://python.org)
[![Docker](https://img.shields.io/badge/Docker-Containerized-2496ED?style=for-the-badge&logo=docker&logoColor=white)](https://docker.com)
[![MongoDB](https://img.shields.io/badge/MongoDB-Database-47A248?style=for-the-badge&logo=mongodb&logoColor=white)](https://mongodb.com)
[![Render](https://img.shields.io/badge/Hosted_on-Render-46E3B7?style=for-the-badge)](https://render.com)

<br/>

> *Medelin is more than just a coffee shop. It's an experience. And this system is built so that every interaction — from browsing the menu to receiving your order — is flawless.*

</div>

---

## 📖 What is this?

**Medelin Coffee Roasters** is a monorepo containing the complete digital infrastructure for a coffee shop chain in Uzhhorod. The project consists of two interconnected components that together form a single, cohesive production system:

| Component | Description |
|---|---|
| 🌐 **MedelinSite** | Public website with a coffee catalogue, location information, shopping cart, and order checkout |
| 🤖 **MedelinBot** | Telegram bot for business management: orders, inventory, staff, statistics, finances |

Both components live in a single Docker container and are deployed with one command on [Render](https://render.com).

---

## 🏛️ System Architecture

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

## 🚀 Technology Stack

### Backend
| Technology | Version | Purpose |
|---|---|---|
| Python | 3.11 | Primary language |
| FastAPI | 0.135 | REST API for the website |
| aiogram | 3.26 | Telegram Bot Framework |
| Uvicorn | 0.34 | ASGI server |
| Motor | 3.7 | Async MongoDB driver |
| APScheduler | 3.11 | Background job scheduler |
| LiqPay SDK | 1.0.6 | Online payments |
| Pillow | 11.1 | Image processing |
| aiohttp | 3.13 | HTTP client (Nova Poshta API) |

### Frontend
| Technology | Purpose |
|---|---|
| Vanilla HTML/CSS/JS | No frameworks — clean and fast |
| BEM Methodology | Structured CSS architecture |
| Font Awesome 6.5 | Icons |
| Google Fonts | Montserrat, Manrope, Oswald, Jost |
| Leaflet.js | Interactive location map |

### Infrastructure
| Technology | Purpose |
|---|---|
| Docker | Containerisation of the entire stack |
| Nginx | Static files + Reverse Proxy |
| MongoDB | Primary database |
| Render | Hosting (PaaS) |
| GitHub | Version control (`releases` branch) |

---

## 📁 Repository Structure

```
Medelin/
├── 📄 Dockerfile              # Single image for the entire stack
├── 📄 docker-compose.yml      # Local environment (+ MongoDB)
├── 📄 nginx.conf              # Nginx configuration
├── 📄 start.sh                # Container entry point
├── 📄 .gitignore              # Ignored files (including .env)
│
├── 📂 MedelinBot/             # Telegram bot and REST API
│   ├── main.py                # Entry point (Bot + API together)
│   ├── api.py                 # FastAPI routes
│   ├── bot.py                 # Bot initialisation
│   ├── requirements.txt       # Python dependencies
│   └── app/
│       ├── common/            # Shared instances (bot, config)
│       ├── databases/         # MongoDB repositories
│       ├── handlers/          # Telegram handlers
│       ├── keyboards/         # Inline and Reply keyboards
│       └── utils/             # Utilities (cache, scheduler, NP)
│
└── 📂 MedelinSite/            # Static website
    ├── index.html             # Home page
    ├── 404.html               # Custom error page
    ├── admin-panel.html       # Web admin panel
    ├── robots.txt             # SEO directives
    ├── sitemap.xml            # Site map
    ├── pages/
    │   ├── beans.html         # Whole-bean coffee catalogue
    │   └── contact.html       # Locations and contacts
    └── assets/
        ├── css/               # BEM styles (style.css, responsive.css, pages/)
        └── js/                # Logic (main.js, coffee.js, locations.js)
```

---

## 🌟 Key System Features

### 🛒 For the Customer (website)
- **Whole-bean coffee catalogue** — commercial and specialty varieties with detailed cards
- **Filtering** — by type (commercial / specialty) and roast level
- **Detailed bean card** — descriptors, processing, harvest, altitude, quality score
- **Shopping cart** — with persistence via localStorage
- **Order checkout** — choose delivery method: pick-up, courier, or Nova Poshta
- **Online payment** via LiqPay (card, Apple Pay, Google Pay)
- **Order tracking** — live status updates without page reload
- **Location map** — interactive Leaflet map with all locations
- **Responsive design** — looks great on any device

### 🤖 For the Administrator (bot)
- **Order management** — accept, confirm, reject, fulfil
- **Catalogue management** — add / edit / delete coffee items
- **Location management** — update coffee shop information
- **Staff management** — add / remove team members and their roles
- **Contact and social media management** — real-time updates
- **Financial statistics** — sales for the day, week, and month with a detailed breakdown
- **Automated reports** — monthly statistics sent to the owner automatically
- **Notifications** — instant message for every new order

---

## ⚙️ Quick Start

### Requirements
- Docker + Docker Compose
- MongoDB Atlas or local MongoDB
- Telegram Bot Token (from [@BotFather](https://t.me/BotFather))
- LiqPay keys (if payment is required)
- Nova Poshta API key (if delivery is required)

### 1. Clone the repository
```bash
git clone https://github.com/gleb226/Medelin.git
cd Medelin
```

### 2. Configure environment variables
```bash
cp MedelinBot/.env.docker.example MedelinBot/.env
# Fill in all values in .env
```

Example `.env`:
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

### 3. Run locally (with Docker Compose)
```bash
docker-compose up --build
```

After startup:
- 🌐 Site: `http://localhost`
- 🔧 API: `http://localhost/api/`
- 🗄️ MongoDB: `mongodb://localhost:27017`

### 4. Deploy to Render
1. Connect the repository to Render
2. Choose service type: **Web Service**
3. Runtime: **Docker**
4. Branch: `releases`
5. Add all environment variables via the Render Dashboard
6. Click **Deploy**

---

## 🔐 Security

- The `.env` file is included in `.gitignore` — no secrets in the repository
- Nginx blocks access to hidden files (`.env`, `.sql`, `.bak`, etc.)
- The admin panel (`/admin-panel`) is protected via FastAPI server-side logic
- Search engines (robots.txt) do not index `/admin-panel`
- All secret keys are passed exclusively through environment variables

---

## 🗃️ MongoDB Database

| Collection | Purpose |
|---|---|
| `users` | Telegram users and their data |
| `orders` | All orders (archive) |
| `active_orders` | Currently active orders |
| `coffee_beans` | Coffee bean catalogue |
| `locations` | Coffee shop locations |
| `admins` | List of administrators and the owner |
| `contacts` | Social media and contact details |
| `sales` | Financial sales statistics |

---

## 📊 Order Flow

```
Customer on the website
     │
     ▼
Selects coffee → Adds to cart → Proceeds to checkout
     │
     ▼
Chooses delivery method (pick-up / courier / Nova Poshta)
     │
     ▼
Chooses payment method (LiqPay / cash)
     │
     ├─── LiqPay → Online payment → Auto-confirmation
     │
     └─── Cash → Order placed in "awaiting confirmation" state
                         │
                         ▼
              Admin receives a notification in Telegram
                         │
                         ▼
              Confirms / rejects the order
                         │
                         ▼
              Customer sees the updated status on the website
```

---

## 🤝 Development

### Branches
| Branch | Purpose |
|---|---|
| `releases` | Production branch, tracked by Render |
| `backup_before_cleanup` | Backup snapshot before the major refactor |

### Running the bot in dev mode
```bash
cd MedelinBot
pip install -r requirements.txt
python main.py
```

---

## 📄 License & Authorship

This project was developed for **Medelin Coffee Roasters** (Uzhhorod, Ukraine).  
All rights reserved © 2026 Medelin.

---

<div align="center">

☕ *Made with love for coffee and clean code*

**[Website](https://medelin.onrender.com)** · **[Telegram Bot](https://t.me/MedelnBot)** · **[GitHub](https://github.com/gleb226/Medelin)**

</div>
