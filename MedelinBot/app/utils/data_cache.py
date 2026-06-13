import json
import re
from pathlib import Path
from typing import Any
import logging
import asyncio

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
                logger.info(f"Warming up cache (attempt {attempt+1}/{max_retries})...")
                await self.refresh_locations()
                await self.refresh_socials()
                await self.refresh_coffee()
                logger.info("Cache successfully warmed up")
                return
            except Exception as e:
                logger.error(f"Cache warmup failed: {e}")
                if attempt < max_retries - 1:
                    await asyncio.sleep(5)

    async def refresh(self, key: str) -> Any:
        logger.info(f"Forced refresh for: {key}")
        if key == 'coffee':
            return await self.refresh_coffee()
        elif key == 'locations':
            return await self.refresh_locations()
        elif key == 'socials':
            return await self.refresh_socials()
        return self.get(key) or []

    async def refresh_coffee(self) -> list[dict[str, Any]]:
        try:
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
                    'quality_score': i.get('quality_score') or i.get('cup_score', ''),
                    'harvest': i.get('harvest', ''),
                    'category': i.get('category', ''),
                    'taste': i.get('taste', ''),
                    'descriptors': i.get('descriptors', '')
                })
            logger.info(f"Refreshed coffee: {len(formatted)} items")
            return self.set('coffee', formatted)
        except Exception as e:
            logger.error(f"Failed to refresh coffee: {e}")
            return self.get('coffee') or []

    async def refresh_locations(self) -> list[dict[str, Any]]:
        try:
            from app.databases.location_database import location_db        
            locs = await location_db.get_all_locations()
            formatted = []
            for l in locs:
                formatted.append({
                    'id': str(l.get('_id')),
                    'name': l.get('name', ''),
                    'address': l.get('address', ''),
                    'schedule': l.get('schedule', ''),
                    'phone': l.get('phone', ''),
                    'image_url': l.get('image_url', ''),
                    'google_maps_url': l.get('google_maps_url', ''),
                    'coordinates': l.get('coordinates', {}),
                    'amenities': l.get('amenities', []),
                    'atmosphere': l.get('atmosphere', '')
                })
            logger.info(f"Refreshed locations: {len(formatted)} items")
            return self.set('locations', formatted)
        except Exception as e:
            logger.error(f"Failed to refresh locations: {e}")
            return self.get('locations') or []

    async def refresh_socials(self) -> list[dict[str, Any]]:
        try:
            from app.databases.contacts_database import contacts_db        
            socs = await contacts_db.get_all_contacts()
            formatted = [{'id': str(s['_id']), 'name': s.get('name', ''), 'url': s.get('url', '')} for s in socs]
            logger.info(f"Refreshed socials: {len(formatted)} items")
            return self.set('socials', formatted)
        except Exception as e:
            logger.error(f"Failed to refresh socials: {e}")
            return self.get('socials') or []

    def _path_for(self, key: str) -> Path:
        return self._dir / f'{key}.json'

    def _load_from_disk(self, key: str) -> Any | None:
        p = self._path_for(key)
        if not p.exists(): return None
        try:
            return json.loads(p.read_text(encoding='utf-8'))
        except: return None

    def _write_to_disk(self, key: str, value: Any) -> None:
        try:
            self._path_for(key).write_text(json.dumps(value, ensure_ascii=False, indent=2), encoding='utf-8')
        except: pass

public_data_cache = PublicDataCache()
