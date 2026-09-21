"""
auth.py — Autentikasi admin untuk REST API backend.

Mekanisme:
  - Username & bcrypt hash password disimpan di .env
  - Login memverifikasi plaintext vs hash menggunakan bcrypt
  - Status login dikelola via token sesi in-memory untuk REST API
"""

import bcrypt
import secrets
from config import ADMIN_USERNAME, ADMIN_PASSWORD_HASH


# ── Verification ──────────────────────────────────────────────────────────────

def _check_password(plain_password: str) -> bool:
    """Verifikasi plaintext password terhadap hash bcrypt di .env."""
    if not ADMIN_PASSWORD_HASH:
        # Belum di-setup → tolak semua login, tampilkan pesan
        return False
    try:
        return bcrypt.checkpw(
            plain_password.encode("utf-8"),
            ADMIN_PASSWORD_HASH.encode("utf-8"),
        )
    except Exception:
        return False


# ── In-Memory Token Session (untuk REST API) ──────────────────────────────────
_ACTIVE_TOKENS: set[str] = set()


def create_session_token() -> str:
    """Generate secure random token untuk sesi admin aktif."""
    token = secrets.token_hex(24)
    _ACTIVE_TOKENS.add(token)
    return token


def verify_session_token(token: str) -> bool:
    """Verifikasi apakah token sesi valid."""
    return bool(token and token in _ACTIVE_TOKENS)


def revoke_session_token(token: str) -> None:
    """Hapus token sesi saat logout."""
    _ACTIVE_TOKENS.discard(token)


def verify_admin_credentials(username: str, password: str) -> bool:
    """Verifikasi kombinasi username dan password admin."""
    return username.strip() == ADMIN_USERNAME and _check_password(password)


def is_password_configured() -> bool:
    """Cek apakah password hash sudah di-set di .env."""
    return bool(ADMIN_PASSWORD_HASH)


# ── Setup Utility ─────────────────────────────────────────────────────────────

def generate_hash(password: str) -> str:
    """
    Generate bcrypt hash dari plaintext password.
    Digunakan oleh setup_admin.py.
    """
    return bcrypt.hashpw(
        password.encode("utf-8"), bcrypt.gensalt()
    ).decode("utf-8")
