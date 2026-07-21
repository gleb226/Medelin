<div align="center">

# 🤖 MedelinBot

**Telegram bot and REST API for managing the Medelin Coffee Roasters business**

[![Telegram Bot](https://img.shields.io/badge/Telegram-@MedelnBot-2CA5E0?style=for-the-badge&logo=telegram&logoColor=white)](https://t.me/MedelnBot)
[![Python](https://img.shields.io/badge/Python-3.11-3776AB?style=for-the-badge&logo=python&logoColor=white)](https://python.org)
[![aiogram](https://img.shields.io/badge/aiogram-3.26-2CA5E0?style=for-the-badge)](https://docs.aiogram.dev/)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.135-009688?style=for-the-badge&logo=fastapi&logoColor=white)](https://fastapi.tiangolo.com/)
[![MongoDB](https://img.shields.io/badge/MongoDB-Motor_3.7-47A248?style=for-the-badge&logo=mongodb&logoColor=white)](https://mongodb.com)

<br/>

> *A full-featured business tool inside Telegram. Accept orders, manage your team, track sales — all from your phone, without any extra apps.*

</div>

---

## 📋 Table of Contents

- [Architecture](#-architecture)
- [File Structure](#-file-structure)
- [Roles & Access](#-roles--access)
- [Bot Features](#-bot-features)
- [REST API](#-rest-api)
- [Database](#-database)
- [Utilities & Services](#-utilities--services)
- [Configuration](#-configuration)
- [Background Tasks](#-background-tasks)
- [Running the App](#-running-the-app)

---

## 🏛️ Architecture

MedelinBot is a **monolithic async application** where the Telegram Bot and FastAPI run in the same process via a shared asyncio event loop.

```
main.py (entry point)
     │
     ├── FastAPI App (uvicorn, port 8000)
     │       ├── /api/* (REST endpoints)
     │       └── /admin-panel (protected HTML panel)
     │
     ├── aiogram Dispatcher (polling mode)
     │       ├── admin_router  (business management)
     │       ├── user_router   (customer interaction)
     │       ├── order_router  (order processing)
     │       └── error_router  (global error handling)
     │
     ├── APScheduler (background tasks)
     │       ├── cleanup_old_data    (weekly)
     │       └── send_monthly_stats  (1st of each month)
     │
     └── PublicDataCache (in-memory cache)
             ├── coffee     (coffee catalogue)
             ├── locations  (locations)
             └── socials    (contacts)
```

### Why Bot + API in a single process?

- **Render Free Tier** provides only 1 container — this is the only option
- **Shared cache** — both the bot and the API read data from the same in-memory object
- **Simplified deployment** — one `docker build`, one `docker run`
- **No race conditions** — all operations are async via asyncio

---

## 📁 File Structure

```
MedelinBot/
│
├── 📄 main.py                 # Entry point — starts Bot + API together
├── 📄 api.py                  # All FastAPI endpoints (REST API)
├── 📄 bot.py                  # Bot object initialisation
├── 📄 requirements.txt        # Python dependencies
├── 📄 .env.docker.example     # Example configuration file
│
├── 📂 app/
│   │
│   ├── 📂 common/
│   │   ├── bot_instance.py    # Single Bot instance (Singleton)
│   │   └── config.py          # Environment variable loading
│   │
│   ├── 📂 databases/          # Data access layer (Repository Pattern)
│   │   ├── mongo_client.py    # MongoDB connection (Motor)
│   │   ├── user_database.py   # CRUD for users
│   │   ├── orders_database.py # CRUD for orders
│   │   ├── active_orders_database.py  # Active orders
│   │   ├── coffee_beans_database.py   # Coffee catalogue
│   │   ├── location_database.py       # Locations
│   │   ├── admin_database.py          # Administrators & staff
│   │   ├── contacts_database.py       # Social media & contacts
│   │   └── sales_database.py          # Sales statistics
│   │
│   ├── 📂 handlers/           # Telegram Message/Callback Handlers
│   │   ├── admin_handlers.py  # LARGE file (~74 KB) — all admin functionality
│   │   ├── user_handlers.py   # Customer interaction
│   │   ├── order_handlers.py  # Processing new orders from the website
│   │   └── error_handler.py   # Global error handler
│   │
│   ├── 📂 keyboards/
│   │   ├── admin_keyboards.py # InlineKeyboardMarkup for the admin panel
│   │   └── user_keyboards.py  # Keyboards for end users
│   │
│   └── 📂 utils/
│       ├── admin_notifications.py  # Building notification messages for admins
│       ├── data_cache.py           # In-memory cache for public data
│       ├── logger.py               # Logging configuration
│       ├── message_utils.py        # Telegram message utilities
│       ├── nova_poshta.py          # Nova Poshta API integration
│       ├── paths.py                # File paths & URL utilities
│       ├── payment_refunds.py      # LiqPay refund logic
│       ├── phone_utils.py          # Phone formatting & validation
│       ├── photo_utils.py          # Photo upload & processing (Pillow)
│       ├── scheduler.py            # APScheduler — background tasks
│       └── time_utils.py           # Date/time helpers (Kyiv timezone)
│
├── 📂 cache/                  # Directory for cached data
└── 📂 fills/
    └── seed.py                # Seed database with test data
```

---

## 👥 Roles & Access

The system has 3 access levels:

| Role | Description | Capabilities |
|---|---|---|
| 👑 **Owner** | Business owner | Everything + team management, monthly statistics |
| 🔧 **Admin** | Administrator | Orders, catalogue, locations, contacts |
| 👤 **Staff** | Staff member | View and manage orders |

### How is a role determined?

```python
# On every interaction the bot checks the Telegram ID in the admins collection
admin = await admin_db.get_admin(user.id)
if admin:
    role = admin.get("role")  # "owner" | "admin" | "staff"
```

---

## 🤖 Bot Features

### 📋 Order Management (admin_handlers.py)

**How a new order arrives:**
1. Customer places an order on the website → POST `/api/orders`
2. API saves the order to MongoDB
3. API sends a notification in Telegram to all admins
4. Admin clicks **✅ Confirm** or **❌ Reject**
5. Customer sees the updated status on the website via polling

```
📩 New order #1234!

👤 Customer: Oleksiy Koval
📞 Phone: +380 67 123 45 67
📦 Delivery: Nova Poshta, Uzhhorod, branch №5

🛒 Order contents:
  • Ethiopia Yirgacheffe × 1 (250g) — 320 ₴
  • Guatemala Huehuetenango × 2 (250g) — 680 ₴

💰 Total: 1000 ₴
💳 Payment: Cash on delivery

[✅ Confirm] [❌ Reject]
```

---

### ☕ Coffee Catalogue Management

**FSM (Finite State Machine) for adding coffee:**

```
Initial state
     │
     ▼
Enter bean name
     │
     ▼
Select type (Commercial / Specialty)
     │
     ├── Commercial
     │       └── Price 250g → Description → Photo → Save
     │
     └── Specialty
             ├── Price 250g
             ├── Country of origin
             ├── Region
             ├── Variety
             ├── Altitude
             ├── Processing method
             ├── Roast level (filter / espresso)
             ├── Flavour descriptors
             ├── Harvest year
             ├── SCA quality score (quality_score)
             ├── Description
             └── Photo → Save
```

**Editing** — a paginated editor for each field individually:
- The bot shows the current value and waits for a new one
- Supports photo replacement with automatic saving

---

### 📍 Location Management

- View all locations with a summary of key info
- Edit each location:
  - Name and address
  - Opening hours
  - Phone and Google Maps link
  - Photo (via uploaded photo or URL)
  - Amenities list (tags: Wi-Fi, kitchen, kids' room…)
  - GPS coordinates (for the Leaflet map)

---

### 👥 Team Management (Owner only)

```
/team
  │
  ├── List all team members
  │       └── for each: name, role, Telegram username
  │
  ├── Add a team member
  │       ├── Search by Telegram ID, @username, or phone
  │       └── Assign a role (admin / staff)
  │
  └── Remove a team member
          └── Confirmation before removal
```

---

### 📊 Statistics (Owner only)

**The report includes:**
- Total number of orders for the period
- Total sales amount
- TOP-5 most popular items
- Breakdown by payment method
- Comparison with the previous equivalent period

**Available filters:**
- Today / Week / Month / All time

---

### 🔗 Contacts & Social Media Management

- View and edit links: Instagram, Facebook, Telegram, TikTok, phone, email
- Changes are reflected on the website immediately (via cache invalidation)

---

## 🌐 REST API

### Public endpoints (no authentication)

| Method | URL | Description |
|---|---|---|
| `GET` | `/api/coffee` | Full coffee bean catalogue |
| `GET` | `/api/locations` | List of locations |
| `GET` | `/api/socials` | Contacts and social media |
| `POST` | `/api/orders` | Create a new order |
| `GET` | `/api/orders/{order_id}` | Order details |
| `GET` | `/api/nova-poshta/cities` | Search Nova Poshta cities |
| `GET` | `/api/nova-poshta/warehouses` | Search Nova Poshta branches |
| `POST` | `/api/liqpay/form` | Generate a payment form |
| `POST` | `/api/liqpay/callback` | LiqPay callback after payment |
| `POST` | `/api/client-error` | Log errors from the frontend |

### Protected endpoints

| Method | URL | Description |
|---|---|---|
| `GET` | `/admin-panel` | HTML panel (verified via session) |
| `GET` | `/api/admin/*` | Admin API (JWT or cookie auth) |

### API response caching

```python
class PublicDataCache:
    """In-memory cache with TTL for public data"""
    
    async def get_coffee(self) -> list:
        # If cache is fresh — returns from memory
        # If stale — refreshes from MongoDB in the background
        pass
    
    async def warm_all(self, max_retries=3):
        # Pre-loads all data on startup
        pass
    
    def invalidate(self, key: str):
        # Force invalidation after changes made via the bot
        pass
```

---

## 🗃️ Database

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
  "descriptors": "Jasmine, bergamot, blackcurrant",
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
    "name": "Oleksiy Koval",
    "phone": "+380671234567"
  },
  "delivery": {
    "method": "nova_poshta",
    "city": "Uzhhorod",
    "warehouse": "Branch №5"
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
  "display_name": "Oleksiy",
  "role": "admin",
  "added_at": "2024-01-01T00:00:00Z",
  "added_by": 987654321
}
```

---

## 🛠️ Utilities & Services

### `photo_utils.py` — Image Processing

```python
# Download photo from Telegram → process via Pillow → save
async def save_photo_from_telegram(bot, photo_file_id) -> str:
    # 1. Downloads the file via bot.download()
    # 2. Converts to WebP or JPEG (Pillow)
    # 3. Resizes to maximum dimensions
    # 4. Saves to /app/uploads/
    # 5. Returns a relative URL
    pass
```

### `nova_poshta.py` — Nova Poshta Integration

```python
# Nova Poshta API v2.0
async def search_cities(query: str) -> list:
    """Search cities via searchSettlements"""
    
async def search_warehouses(city_ref: str, query: str) -> list:
    """Search branches and parcel lockers"""
```

### `scheduler.py` — Background Tasks

```python
def start_scheduler():
    scheduler = AsyncIOScheduler(timezone="Europe/Kyiv")
    
    # Every Sunday at 03:00 — clean up old orders (> 5 days)
    scheduler.add_job(cleanup_old_data, "cron", day_of_week="sun", hour=3)
    
    # 1st of every month — monthly report to the owner
    scheduler.add_job(send_monthly_stats, "cron", day=1, hour=9)
    
    scheduler.start()
```

### `data_cache.py` — Caching Strategy

```
System startup
     │
     ▼
warm_all() — loads coffee, locations, socials from MongoDB
     │
     ▼
FastAPI API → reads from cache (no DB calls!)
     │
     ▼
Admin updates data via the bot
     │
     ▼
cache.invalidate("coffee") → next request refreshes the cache
```

---

## ⚙️ Configuration

### Environment variables (`.env`)

```env
# Telegram
BOT_TOKEN=7123456789:AAFxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx

# MongoDB
MONGO_URI=mongodb+srv://user:password@cluster.mongodb.net/
MONGO_DB_NAME=medelin

# Admin Telegram IDs (owner and admins)
ADMIN_TELEGRAM_IDS=123456789,987654321
OWNER_TELEGRAM_ID=123456789

# LiqPay (online payments)
LIQPAY_PUBLIC_KEY=your_public_key
LIQPAY_PRIVATE_KEY=your_private_key

# Nova Poshta
NP_API_KEY=your_nova_poshta_api_key

# Web App
WEB_APP_URL=https://medelin.onrender.com
```

### Loading configuration

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

## ⏰ Background Tasks

| Task | Schedule | Description |
|---|---|---|
| `cleanup_old_data` | Every Sunday at 03:00 | Deletes active orders older than 5 days |
| `send_monthly_stats` | 1st of month at 09:00 | Sends the monthly report to the owner |

### Monthly report (example)

```
📊 Report for June 2024

📦 Orders: 47
💰 Total sales: 28,340 ₴

☕ TOP items:
  1. Ethiopia Yirgacheffe — 23 orders
  2. Colombia Huila — 18 orders
  3. Guatemala Huehuetenango — 15 orders

💳 Payment methods:
  • LiqPay: 34 (72%)
  • Cash: 13 (28%)
```

---

## 🚀 Running the App

### Locally (without Docker)

```bash
cd MedelinBot

# Install dependencies
pip install -r requirements.txt

# Copy configuration
cp .env.docker.example .env
# Fill in .env with your values

# Start
python main.py
```

### Locally (with Docker Compose)

```bash
# From the repository root
docker-compose up --build
```

MongoDB will be available at `localhost:27017`, the API at `localhost/api/`.

### Seed with test data

```bash
# After the system is running
python fills/seed.py
```

---

## 📦 Dependencies

```
aiogram==3.26.0        # Telegram Bot Framework (async)
fastapi==0.135.2        # Web API Framework
uvicorn==0.34.0         # ASGI Server
motor==3.7.1            # Async MongoDB Driver
pillow==11.1.0          # Image Processing
python-dotenv==1.0.1    # .env file loader
aiohttp==3.13.3         # Async HTTP Client (Nova Poshta)
aiofiles==25.1.0        # Async File I/O
aiosqlite==0.22.1       # SQLite (fallback)
asyncpg==0.31.0         # PostgreSQL (fallback)
apscheduler==3.11.2     # Background Job Scheduler
liqpay-sdk-python3==1.0.6  # LiqPay Payment SDK
python-multipart==0.0.9    # File Upload Support
```

---

## 🔄 Error Handling Flow

```python
# error_handler.py — global handler
@error_router.errors(ExceptionHandler)
async def handle_error(update: Update, exception: Exception):
    logger.error(f"Unhandled exception: {exception}", exc_info=True)
    
    # Notify the owner of a critical error
    if isinstance(exception, CriticalError):
        await bot.send_message(OWNER_ID, f"🚨 Critical error: {exception}")
    
    # Friendly message to the user
    await update.message.answer("An error occurred. Please try again.")
```

---

<div align="center">

**🤖 [Open the bot](https://t.me/MedelnBot)** · **[⬆️ Main README](../README.md)**

☕ *Made with love for coffee and clean code*

© 2026 Medelin

</div>
