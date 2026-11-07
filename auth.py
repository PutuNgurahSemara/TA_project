"""
auth.py — Autentikasi multi-admin dan manajemen sesi untuk REST API backend.

Mekanisme:
  - Data akun admin disimpan di SQLite (tabel `admins`)
  - Login memverifikasi plaintext password vs bcrypt hash
  - Status sesi dikelola via in-memory token mapping ke data akun (id, username, role)
"""

import secrets
import time
from typing import Any, Optional
import bcrypt
from db.database import get_admin_by_username


# ── In-Memory Token Session Mapping ──────────────────────────────────────────
# Format: { token: { "id": int, "username": str, "role": str } }
_ACTIVE_SESSIONS: dict[str, dict[str, Any]] = {}
SESSION_TTL_SECONDS = 12 * 60 * 60


def verify_admin_credentials(username: str, password: str) -> Optional[dict[str, Any]]:
    """
    Verifikasi username & password admin dari database SQLite.
    Mengembalikan data profil admin jika valid, atau None jika gagal.
    """
    if not username or not password:
        return None

    admin = get_admin_by_username(username.strip())
    if not admin:
        return None

    try:
        is_valid = bcrypt.checkpw(
            password.encode("utf-8"),
            admin["password_hash"].encode("utf-8"),
        )
        if is_valid:
            return {
                "id": admin["id"],
                "username": admin["username"],
                "role": admin["role"],
            }
    except Exception:
        return None

    return None


def create_session_token(user_data: dict[str, Any]) -> str:
    """Generate secure token dan simpan data sesi user."""
    token = secrets.token_hex(24)
    admin = get_admin_by_username(user_data["username"])
    _ACTIVE_SESSIONS[token] = {
        "username": user_data["username"],
        "password_hash": admin["password_hash"] if admin else "",
        "expires_at": time.time() + SESSION_TTL_SECONDS,
    }
    return token


def get_session_user(token: str) -> Optional[dict[str, Any]]:
    """
    Ambil data user dari token sesi aktif. Role selalu dibaca ulang dari DB, sehingga
    akun yang dihapus, diturunkan role-nya, atau diganti password-nya langsung berlaku.
    """
    session = _ACTIVE_SESSIONS.get(token) if token else None
    if not session:
        return None

    admin = get_admin_by_username(session["username"])
    if (
        time.time() > session["expires_at"]
        or not admin
        or admin["password_hash"] != session["password_hash"]
    ):
        _ACTIVE_SESSIONS.pop(token, None)
        return None

    return {"id": admin["id"], "username": admin["username"], "role": admin["role"]}


def verify_session_token(token: str) -> bool:
    """Cek apakah token sesi valid."""
    return bool(token and token in _ACTIVE_SESSIONS)


def revoke_session_token(token: str) -> None:
    """Hapus token sesi saat logout."""
    _ACTIVE_SESSIONS.pop(token, None)


# ── Password Utilities ───────────────────────────────────────────────────────

def generate_hash(password: str) -> str:
    """Generate bcrypt hash dari plaintext password."""
    return bcrypt.hashpw(
        password.encode("utf-8"), bcrypt.gensalt()
    ).decode("utf-8")
