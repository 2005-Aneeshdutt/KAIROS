from __future__ import annotations

import json
import os
import time
from pathlib import Path

_DEFAULT = "sqlite:///" + str((Path(__file__).resolve().parent / "kairos.db")).replace("\\", "/")
_URL = os.environ.get("DATABASE_URL") or _DEFAULT

_engine = None
_state = None


def _normalize(url: str) -> str:
    if url.startswith("postgres://"):
        return "postgresql://" + url[len("postgres://"):]
    return url


def init() -> bool:
    global _engine, _state
    if _state is not None:
        return _state
    try:
        from sqlalchemy import create_engine, text
        url = _normalize(_URL)
        kw = {"pool_pre_ping": True}
        if url.startswith("sqlite"):
            kw["connect_args"] = {"check_same_thread": False}
        _engine = create_engine(url, **kw)
        with _engine.begin() as c:
            c.execute(text("CREATE TABLE IF NOT EXISTS visitors ("
                           "uid TEXT PRIMARY KEY, data TEXT, updated REAL)"))
        _state = True
        print(f"[db] persistence ON ({backend()})")
    except Exception as e:
        print(f"[db] persistence OFF ({e!r}); running in-memory only")
        _state = False
    return _state


def enabled() -> bool:
    return init()


def backend() -> str:
    if _state is False:
        return "memory"
    url = _normalize(_URL)
    return "postgres" if url.startswith("postgresql") else "sqlite"


def load_all() -> dict:
    if not init():
        return {}
    from sqlalchemy import text
    out: dict[str, dict] = {}
    try:
        with _engine.connect() as c:
            for uid, data in c.execute(text("SELECT uid, data FROM visitors")):
                try:
                    out[uid] = json.loads(data)
                except Exception:
                    pass
    except Exception as e:
        print(f"[db] load failed ({e!r})")
    return out


def save(uid: str, data: dict) -> None:
    if not init():
        return
    from sqlalchemy import text
    try:
        with _engine.begin() as c:
            c.execute(text(
                "INSERT INTO visitors (uid, data, updated) VALUES (:uid, :data, :updated) "
                "ON CONFLICT (uid) DO UPDATE SET data = excluded.data, updated = excluded.updated"),
                {"uid": uid, "data": json.dumps(data, default=str), "updated": time.time()})
    except Exception as e:
        print(f"[db] save failed for {uid} ({e!r})")
