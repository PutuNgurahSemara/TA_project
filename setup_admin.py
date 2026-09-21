"""
setup_admin.py — Script satu kali untuk men-set password admin.
Jalankan: python setup_admin.py
"""
import bcrypt
import os
import re
from pathlib import Path

ENV_PATH = Path(__file__).parent / ".env"


def generate_hash(password: str) -> str:
    return bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")


def update_env(key: str, value: str) -> None:
    """Tulis atau update KEY=VALUE di file .env."""
    content = ENV_PATH.read_text(encoding="utf-8") if ENV_PATH.exists() else ""
    pattern = rf"^{re.escape(key)}=.*$"
    new_line = f"{key}={value}"

    if re.search(pattern, content, re.MULTILINE):
        content = re.sub(pattern, new_line, content, flags=re.MULTILINE)
    else:
        content += f"\n{new_line}\n"

    ENV_PATH.write_text(content, encoding="utf-8")


def main():
    print("=" * 50)
    print("  Setup Admin Chatbot RAG")
    print("=" * 50)

    username = input("\nUsername admin [default: admin]: ").strip() or "admin"

    while True:
        password = input("Password admin: ").strip()
        if len(password) < 4:
            print("Password minimal 4 karakter. Coba lagi.")
            continue
        confirm = input("Konfirmasi password: ").strip()
        if password != confirm:
            print("Password tidak cocok. Coba lagi.\n")
            continue
        break

    print("\n[*] Membuat hash password...")
    hashed = generate_hash(password)

    update_env("ADMIN_USERNAME", username)
    update_env("ADMIN_PASSWORD_HASH", hashed)

    print(f"\n[OK] Selesai! Credential admin disimpan ke .env")
    print(f"   Username : {username}")
    print(f"   Hash     : {hashed[:30]}...")
    print("\nJalankan aplikasi dengan: python main.py")


if __name__ == "__main__":
    main()
