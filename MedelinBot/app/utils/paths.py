from __future__ import annotations

import os
from pathlib import Path


def get_uploads_dir() -> Path:
    """
    Resolve a writable uploads directory across environments.
    """
    env_dir = (os.getenv("UPLOADS_DIR") or "").strip()
    if env_dir:
        p = Path(env_dir)
        p.mkdir(parents=True, exist_ok=True)
        return p

    candidates = [
        Path("/usr/share/nginx/html/assets/images/uploads"),
        Path("/app/MedelinSite/assets/images/uploads"),
        Path("/app/uploads"),
    ]
    for p in candidates:
        if p.exists() or p.parent.exists():
            try:
                p.mkdir(parents=True, exist_ok=True)
                return p
            except Exception:
                pass

    repo_root = Path(__file__).resolve().parents[3]
    dev_path = repo_root / "MedelinSite" / "assets" / "images" / "uploads"
    dev_path.mkdir(parents=True, exist_ok=True)
    return dev_path


def get_cache_dir() -> Path:
    """
    Resolve the public JSON cache directory across environments.

    Priority:
    1) `CACHE_DIR` env override
    2) Unified container path (/usr/share/nginx/html/cache)
    3) Docker bind-mount path (/app/cache)
    4) Repo-local `MedelinSite/cache`
    """
    env_dir = (os.getenv("CACHE_DIR") or "").strip()
    if env_dir:
        p = Path(env_dir)
        p.mkdir(parents=True, exist_ok=True)
        return p

    unified_path = Path("/usr/share/nginx/html/cache")
    if unified_path.parent.exists():
        unified_path.mkdir(parents=True, exist_ok=True)
        return unified_path

    docker_path = Path("/app/cache")
    if docker_path.exists() or docker_path.parent.exists():
        docker_path.mkdir(parents=True, exist_ok=True)
        return docker_path

    repo_root = Path(__file__).resolve().parents[3]
    dev_path = repo_root / "MedelinSite" / "cache"
    dev_path.mkdir(parents=True, exist_ok=True)
    return dev_path

