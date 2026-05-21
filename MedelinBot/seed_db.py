from __future__ import annotations

import argparse
import asyncio
from typing import Any

from app.databases.mongo_client import get_db

import re


def _to_int(value: Any) -> int:
    if value is None:
        return 0
    if isinstance(value, int):
        return value
    s = str(value).strip()
    if not s:
        return 0
    m = re.search(r"-?\d+", s)
    if not m:
        return 0
    try:
        return int(m.group(0))
    except Exception:
        return 0


def _to_float(value: Any) -> float:
    if value is None:
        return 0.0
    if isinstance(value, (int, float)):
        return float(value)
    s = str(value).strip().replace(",", ".")
    if not s:
        return 0.0
    try:
        return float(s)
    except Exception:
        m = re.search(r"-?\d+(\.\d+)?", s)
        return float(m.group(0)) if m else 0.0


async def seed(*, drop: bool) -> None:
    from fills.seed import MENU_DATA, BEANS_DATA

    db = await get_db()

    if drop:
        await db.menu.delete_many({})
        await db.coffee_beans.delete_many({})

    # Menu: upsert by (category, name)
    for row in MENU_DATA:
        (
            category,
            name,
            price,
            description,
            volume,
            calories,
            strength,
            sweetness,
            composition,
            _is_hidden,
            _is_coffee,
            _coffee_info,
        ) = row

        doc: dict[str, Any] = {
            "category": str(category),
            "name": str(name),
            "price": _to_float(price),
            "description": str(description or ""),
            "volume": str(volume or ""),
            "calories": str(calories or ""),
            "composition": str(composition or ""),
            "strength": _to_int(strength),
            "sweetness": _to_int(sweetness),
        }

        await db.menu.update_one({"category": doc["category"], "name": doc["name"]}, {"$set": doc}, upsert=True)

    # Beans: upsert by name
    for b in BEANS_DATA:
        name = str(b.get("name") or "").strip()
        if not name:
            continue
        await db.coffee_beans.update_one({"name": name}, {"$set": dict(b)}, upsert=True)

    # Hard delete Matcha category if present
    await db.menu.delete_many({"category": {"$in": ["Матча", "🍵 Матча", "Матча "]}})


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--drop", action="store_true", help="Drop menu and beans before seeding")
    args = ap.parse_args()

    asyncio.run(seed(drop=bool(args.drop)))


if __name__ == "__main__":
    main()
