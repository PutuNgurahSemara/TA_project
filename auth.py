"""
auth.py — Autentikasi multi-admin dan manajemen sesi untuk REST API backend.

Mekanisme:
  - Data akun admin disimpan di SQLite (tabel `admins`)
  - Login memverifikasi plaintext password vs bcrypt hash
  - Status sesi dikelola via in-memory token mapping ke data akun (id, username, role)
"""

import secrets
from typing import Any, Optional
import bcrypt
from db.database import get_admin_by_username


# ── In-Memory Token Session Mapping ──────────────────────────────────────────
# Format: { token: { "id": int, "username": str, "role": str } }
_ACTIVE_SESSIONS: dict[str, dict[str, Any]] = {}


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
    _ACTIVE_SESSIONS[token] = {
        "id": user_data["id"],
        "username": user_data["username"],
        "role": user_data["role"],
    }
    return token


def get_session_user(token: str) -> Optional[dict[str, Any]]:
    """Ambil data user dari token sesi aktif."""
    if not token:
        return None
    return _ACTIVE_SESSIONS.get(token)


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
