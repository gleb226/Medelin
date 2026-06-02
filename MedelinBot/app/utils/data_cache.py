import json

import re

from pathlib import Path

from typing import Any

import logging

logger = logging.getLogger(__name__)

class PublicDataCache:

    def __init__(self) -> None:

        self._memory: dict[str, Any] = {}
        
        # Robust path detection
        # 1. Docker container path (mapped in docker-compose)
        docker_path = Path('/app/cache')
        
        # 2. Unified container (Nginx + Bot): Site is at /usr/share/nginx/html
        unified_path = Path('/usr/share/nginx/html/cache')
        
        # 3. Local development fallback
        repo_root = Path(__file__).resolve().parents[3]
        dev_path = repo_root / 'MedelinSite' / 'cache'
        
        if unified_path.parent.exists():
            self._dir = unified_path
        elif docker_path.exists() or docker_path.parent.exists():
            self._dir = docker_path
        else:
            self._dir = dev_path

        try:
            self._dir.mkdir(parents=True, exist_ok=True)
            logger.info(f"PublicDataCache initialized at: {self._dir}")
        except Exception as e:
            logger.error(f"Failed to create cache dir {self._dir}: {e}")

    def get(self, key: str) -> Any | None:

        return self._memory.get(key) or self._load_from_disk(key)

    def set(self, key: str, value: Any) -> Any:

        self._memory[key] = value

        self._write_to_disk(key, value)

        return value

    async def warm_all(self, max_retries: int = 3) -> None:

        for attempt in range(max_retries):

            try:

                await self.refresh_locations()

                await self.refresh_socials()

                await self.refresh_coffee()

                return

            except Exception:

                if attempt < max_retries - 1:

                    import asyncio

                    await asyncio.sleep(5)

    async def refresh(self, key: str) -> Any:

        if key == 'coffee':

            return await self.refresh_coffee()

        elif key == 'locations':

            return await self.refresh_locations()

        elif key == 'socials':

            return await self.refresh_socials()

        return self.get(key)

    async def refresh_coffee(self) -> list[dict[str, Any]]:

        from app.databases.coffee_beans_database import coffee_beans_db

        items = await coffee_beans_db.get_all_beans()

        formatted = []

        for i in items:

            formatted.append({
                'id': str(i.get('_id')),
                'name': i.get('name', ''),
                'description': i.get('description', ''),
                'price_250': i.get('price_250', 0),
                'image_url': i.get('image_url', ''),
                'altitude': i.get('altitude', ''),
                'species': i.get('species', ''),
                'processing': i.get('processing', ''),
                'roast': i.get('roast', ''),
                'variety': i.get('variety', ''),
                'cup_score': i.get('cup_score', ''),
                'harvest': i.get('harvest', ''),
                'taste': i.get('taste', ''),
                'country': i.get('country', ''),
                'region': i.get('region', ''),
                'station': i.get('station', ''),
                'recommendation': i.get('recommendation', ''),
                'acidity': i.get('acidity', 0),
                'bitterness': i.get('bitterness', 0),
                'body': i.get('body', 0)
            })

        return self.set('coffee', formatted)

    async def refresh_locations(self) -> list[dict[str, Any]]:

        from app.databases.location_database import location_db

        locs = await location_db.get_all_locations()

        formatted = []

        for l in locs:

            formatted.append({'id': str(l.get('_id') or l.get('id')), 'name': l.get('name', ''), 'address': l.get('address', ''), 'schedule': l.get('schedule', ''), 'phone': l.get('phone', ''), 'google_maps_url': l.get('google_maps_url', ''), 'image_url': l.get('image_url', ''), 'amenities': l.get('amenities', []), 'atmosphere': l.get('atmosphere', ''), 'coordinates': l.get('coordinates')})

        return self.set('locations', formatted)

    async def refresh_socials(self) -> list[dict[str, Any]]:

        from app.databases.contacts_database import contacts_db

        socs = await contacts_db.get_all_contacts()

        formatted = [{'id': str(s.get('_id') or s.get('id')), 'name': s.get('name', ''), 'url': s.get('url', '')} for s in socs]

        return self.set('socials', formatted)

    def _path_for(self, key: str) -> Path:

        return self._dir / f'{key}.json'

    def _load_from_disk(self, key: str) -> Any | None:

        p = self._path_for(key)

        if not p.exists():

            return None

        try:

            d = json.loads(p.read_text(encoding='utf-8'))

            self._memory[key] = d

            return d

        except:

            return None

    def _write_to_disk(self, key: str, value: Any) -> None:

        self._path_for(key).write_text(json.dumps(value, ensure_ascii=False, indent=2), encoding='utf-8')

public_data_cache = PublicDataCache()
