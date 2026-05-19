
from __future__ import annotations

import logging

import os

import json

import subprocess

from urllib.parse import parse_qsl, urlencode

from typing import Any

from motor.motor_asyncio import AsyncIOMotorClient, AsyncIOMotorDatabase

from pymongo import ASCENDING, IndexModel

from app.common.config import MONGO_DB_NAME, MONGO_URI

logger = logging.getLogger(__name__)

_client: AsyncIOMotorClient | None = None

_db: AsyncIOMotorDatabase | None = None

_indexes_ready: bool = False

async def get_db() -> AsyncIOMotorDatabase:

    global _client, _db, _indexes_ready

    if not MONGO_URI:

        raise RuntimeError('MONGO_URI is not set in .env')

    if _client is None:

        uri_to_use = MONGO_URI

        if str(MONGO_URI).startswith('mongodb+srv://'):

            uri_to_use = _expand_mongodb_srv_uri_windows(MONGO_URI) or MONGO_URI

        _client = AsyncIOMotorClient(uri_to_use)

    if _db is None:

        if _client is not None:

            _db = _client[MONGO_DB_NAME]

    if _db is not None and (not _indexes_ready):

        await _ensure_indexes(_db)

        _indexes_ready = True

    if _db is None:

        raise RuntimeError('Failed to initialize Mongo database')

    return _db

def _expand_mongodb_srv_uri_windows(uri: str) -> str | None:

    try:

        if os.name != 'nt':

            return None

        rest = uri.replace('mongodb+srv://', '', 1)

        auth, host_and_path = ('', rest)

        if '@' in rest.split('/', 1)[0]:

            auth, host_and_path = rest.split('@', 1)

        host_part, path_part = (host_and_path.split('/', 1) + [''])[:2]

        db_name = ''

        query_str = ''

        if path_part:

            if '?' in path_part:

                db_name, query_str = path_part.split('?', 1)

            else:

                db_name = path_part

        db_name = (db_name or '').strip('/')

        srv = _ps_resolve_srv(host_part)

        if not srv:

            return None

        txt = _ps_resolve_txt(host_part) or ''

        query: dict[str, str] = {}

        for k, v in parse_qsl(query_str, keep_blank_values=True):

            query[k] = v

        for k, v in parse_qsl(txt, keep_blank_values=True):

            query.setdefault(k, v)

        if 'tls' not in query and 'ssl' not in query:

            query['tls'] = 'true'

        hosts = ','.join((f'{t}:{p}' for t, p in srv))

        auth_prefix = f'{auth}@' if auth else ''

        path = f'/{db_name}' if db_name else ''

        return f'mongodb://{auth_prefix}{hosts}{path}?{urlencode(query)}'

    except Exception as e:

        logger.warning(f'Failed to expand mongodb+srv uri: {e}')

        return None

def _ps_resolve_srv(host: str) -> list[tuple[str, int]]:

    cmd = ['powershell', '-NoProfile', '-Command', f'Resolve-DnsName -Type SRV _mongodb._tcp.{host} | Select-Object NameTarget,Port | ConvertTo-Json -Compress']

    out = subprocess.check_output(cmd, text=True, encoding='utf-8', errors='replace').strip()

    if not out:

        return []

    data = json.loads(out)

    if isinstance(data, dict):

        data = [data]

    result: list[tuple[str, int]] = []

    for row in data:

        target = str(row.get('NameTarget') or '').strip().rstrip('.')

        port = int(row.get('Port') or 27017)

        if target:

            result.append((target, port))

    result.sort(key=lambda x: x[0])

    return result

def _ps_resolve_txt(host: str) -> str | None:

    cmd = ['powershell', '-NoProfile', '-Command', f'Resolve-DnsName -Type TXT {host} | Select-Object -First 1 -ExpandProperty Strings']

    out = subprocess.check_output(cmd, text=True, encoding='utf-8', errors='replace').strip()

    return out or None

async def close_client():

    global _client, _db, _indexes_ready

    if _client is not None:

        _client.close()

    _client = None

    _db = None

    _indexes_ready = False

async def _ensure_indexes(db: AsyncIOMotorDatabase):

    ttl_6_months = 60 * 60 * 24 * 180

    try:

        await db.users.create_index([('user_id', ASCENDING)], unique=True)

        await db.users.create_index([('username_lc', ASCENDING)])

        await db.users.create_index([('phone_digits', ASCENDING)])

        await db.admins.create_index([('user_id', ASCENDING)], unique=True)

        await db.admins.create_index([('role', ASCENDING)])

        await db.admins.create_index([('is_on_shift', ASCENDING)])

        await db.menu.create_index([('category', ASCENDING)])

        await db.menu.create_index([('name', ASCENDING)])

        await db.sales.create_index([('record_type', ASCENDING)])

        await db.sales.create_index([('user_id', ASCENDING)])

        await _ensure_ttl_index(db.bookings, 'created_at', ttl_6_months)

        await _ensure_ttl_index(db.sales, 'timestamp', ttl_6_months)

        await _ensure_ttl_index(db.activity_logs, 'timestamp', ttl_6_months)

        await _ensure_ttl_index(db.errors, 'timestamp', ttl_6_months)

    except BaseException as e:

        if isinstance(e, (SystemExit, KeyboardInterrupt)):

            raise

        logger.error(f'Error ensuring indexes: {e}')

async def _ensure_ttl_index(collection, field: str, expire_seconds: int):

    try:

        info = await collection.index_information()

        for name, spec in (info or {}).items():

            key = spec.get('key')

            if key == [(field, 1)]:

                if spec.get('expireAfterSeconds') != expire_seconds:

                    try:

                        await collection.drop_index(name)

                    except Exception:

                        pass

        await collection.create_index([(field, ASCENDING)], expireAfterSeconds=int(expire_seconds), name=f'{field}_ttl')

    except BaseException as e:

        if isinstance(e, (SystemExit, KeyboardInterrupt)):

            raise

        logger.error(f'Error ensuring TTL index on {collection.name}: {e}')

def projection_without_mongo_id() -> dict[str, Any]:

    return {'_id': 0}
