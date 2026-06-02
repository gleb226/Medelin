from __future__ import annotations
import logging
import os
import json
import subprocess
from urllib.parse import parse_qsl, urlencode
from typing import Any
from motor.motor_asyncio import AsyncIOMotorClient, AsyncIOMotorDatabase
from app.common.config import MONGO_URI, MONGO_DB_NAME

logger = logging.getLogger(__name__)

_client: AsyncIOMotorClient | None = None
_db: AsyncIOMotorDatabase | None = None
_indexes_ready = False

async def get_db() -> AsyncIOMotorDatabase:
    global _client, _db, _indexes_ready
    if not MONGO_URI:
        raise RuntimeError('MONGO_URI is not set in .env')
    
    if _client is None:
        _client = AsyncIOMotorClient(
            MONGO_URI,
            serverSelectionTimeoutMS=30000,
            connectTimeoutMS=20000,
            retryWrites=True
        )
    
    if _db is None:
        if _client is not None:
            _db = _client[MONGO_DB_NAME]
            if not _indexes_ready:
                _indexes_ready = True
                await ensure_indexes(_db)
    
    return _db

async def ensure_indexes(db: AsyncIOMotorDatabase):
    try:
        await db.users.create_index('user_id', unique=True)
        await db.users.create_index('username_lc')
        await db.users.create_index('phone_digits')
        await db.admins.create_index('user_id', unique=True)
        await db.orders.create_index('order_id', unique=True)
        await db.orders.create_index('created_at')
        await db.active_orders.create_index('order_id', unique=True)
    except Exception as e:
        logger.error(f'Error ensuring indexes: {e}')

def _ps_resolve_srv_sync(host: str) -> list[tuple[str, int]]:
    cmd = ['powershell', '-NoProfile', '-Command', f'Resolve-DnsName -Type SRV _mongodb._tcp.{host} | Select-Object NameTarget,Port | ConvertTo-Json -Compress']
    try:
        out = subprocess.check_output(cmd, text=True, encoding='utf-8', errors='replace', timeout=5).strip()
        if not out: return []
        data = json.loads(out)
        if isinstance(data, dict): data = [data]
        result = []
        for row in data:
            target = str(row.get('NameTarget') or '').strip().rstrip('.')
            port = int(row.get('Port') or 27017)
            if target: result.append((target, port))
        result.sort(key=lambda x: x[0])
        return result
    except: return []

def _ps_resolve_txt_sync(host: str) -> str | None:
    cmd = ['powershell', '-NoProfile', '-Command', f'Resolve-DnsName -Type TXT {host} | Select-Object -First 1 -ExpandProperty Strings']
    try:
        out = subprocess.check_output(cmd, text=True, encoding='utf-8', errors='replace', timeout=5).strip()
        return out or None
    except: return None

async def _expand_mongodb_srv_uri_windows(srv_uri: str) -> str | None:
    try:
        from urllib.parse import urlparse, parse_qsl, urlencode
        import asyncio
        parsed = urlparse(srv_uri)
        host = parsed.hostname
        loop = asyncio.get_event_loop()
        
        srv_results = await loop.run_in_executor(None, _ps_resolve_srv_sync, host)
        if not srv_results: return None
        
        hosts = ','.join([f'{h}:{p}' for h, p in srv_results])
        txt_record = await loop.run_in_executor(None, _ps_resolve_txt_sync, host)
        
        query = dict(parse_qsl(parsed.query))
        if txt_record:
            for item in txt_record.split(','):
                if '=' in item:
                    k, v = item.split('=', 1)
                    query.setdefault(k.strip(), v.strip())
        
        auth_prefix = ''
        if parsed.username:
            auth_prefix = f'{parsed.username}:{parsed.password}@' if parsed.password else f'{parsed.username}@'
        
        db_name = parsed.path.lstrip('/')
        path = f'/{db_name}' if db_name else ''
        return f'mongodb://{auth_prefix}{hosts}{path}?{urlencode(query)}'
    except Exception as e:
        logger.warning(f'Failed to expand mongodb+srv uri: {e}')
        return None

async def close_client():
    global _client, _db, _indexes_ready
    if _client is not None:
        _client.close()
    _client = None
    _db = None

def projection_without_mongo_id() -> dict[str, Any]:
    return {'_id': 0}
