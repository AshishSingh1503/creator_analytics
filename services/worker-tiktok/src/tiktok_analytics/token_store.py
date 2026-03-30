import json
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, Optional


def _utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _epoch_now() -> int:
    return int(time.time())


def read_token_file(path: Path) -> Optional[Dict[str, object]]:
    if not path.exists():
        return None
    return json.loads(path.read_text(encoding="utf-8"))


def write_token_file(path: Path, payload: Dict[str, object]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2), encoding="utf-8")


def upsert_tokens(conn, token_payload: Dict[str, object]) -> None:
    expires_in = int(token_payload.get("expires_in", 0) or 0)
    refresh_expires_in = int(token_payload.get("refresh_expires_in", 0) or 0)
    now_epoch = _epoch_now()

    access_expires_at = now_epoch + expires_in if expires_in else None
    refresh_expires_at = now_epoch + refresh_expires_in if refresh_expires_in else None

    conn.execute(
        """
        INSERT INTO tokens (
            id, access_token, refresh_token, scope, token_type,
            expires_in, refresh_expires_in, access_expires_at, refresh_expires_at, updated_at
        ) VALUES (1, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ON CONFLICT(id) DO UPDATE SET
            access_token=excluded.access_token,
            refresh_token=excluded.refresh_token,
            scope=excluded.scope,
            token_type=excluded.token_type,
            expires_in=excluded.expires_in,
            refresh_expires_in=excluded.refresh_expires_in,
            access_expires_at=excluded.access_expires_at,
            refresh_expires_at=excluded.refresh_expires_at,
            updated_at=excluded.updated_at
        """,
        (
            str(token_payload.get("access_token", "")),
            str(token_payload.get("refresh_token", "")),
            str(token_payload.get("scope", "")),
            str(token_payload.get("token_type", "Bearer")),
            expires_in,
            refresh_expires_in,
            access_expires_at,
            refresh_expires_at,
            _utc_now_iso(),
        ),
    )
    conn.commit()


def get_tokens(conn) -> Optional[Dict[str, object]]:
    row = conn.execute("SELECT * FROM tokens WHERE id = 1").fetchone()
    if not row:
        return None
    return dict(row)


def token_needs_refresh(tokens: Dict[str, object], buffer_seconds: int) -> bool:
    access_expires_at = tokens.get("access_expires_at")
    if access_expires_at is None:
        return True
    return int(access_expires_at) <= _epoch_now() + buffer_seconds
