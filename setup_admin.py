"""
setup_admin.py — Script CLI interaktif untuk mengelola akun Admin & Super Admin di SQLite.
Jalankan: python setup_admin.py
"""

import sys
from auth import generate_hash
from db.database import (
    initialize_db,
    get_all_admins,
    get_admin_by_username,
    create_admin,
    update_admin,
    delete_admin,
    count_superadmins,
)


def print_header():
    print("\n" + "=" * 54)
    print("      🛠️  PENGELOLA AKUN ADMIN (CHATBOT RAG)")
    print("=" * 54)


def list_admins():
    admins = get_all_admins()
    print("\n--- DAFTAR AKUN ADMIN ---")
    if not admins:
        print("Belum ada akun admin yang terdaftar.")
        return
    print(f"{'ID':<4} | {'Username':<20} | {'Role':<12} | {'Tanggal Dibuat'}")
    print("-" * 54)
    for a in admins:
        print(f"{a['id']:<4} | {a['username']:<20} | {a['role']:<12} | {a['created_at']}")


def add_or_reset_superadmin():
    print("\n--- BUAT / RESET AKUN SUPER ADMIN ---")
    username = input("Username Super Admin [default: admin]: ").strip() or "admin"
    
    while True:
        password = input("Password baru: ").strip()
        if len(password) < 4:
            print("Password minimal 4 karakter.")
            continue
        confirm = input("Konfirmasi password: ").strip()
        if password != confirm:
            print("Password tidak cocok. Coba lagi.")
            continue
        break

    pwd_hash = generate_hash(password)
    existing = get_admin_by_username(username)

    if existing:
        update_admin(existing["id"], role="superadmin", password_hash=pwd_hash)
        print(f"\n[SUKSES] Akun '{username}' berhasil di-reset menjadi Super Admin dengan password baru.")
    else:
        create_admin(username, pwd_hash, role="superadmin")
        print(f"\n[SUKSES] Akun Super Admin baru '{username}' berhasil dibuat.")


def add_new_admin():
    print("\n--- TAMBAH AKUN ADMIN BARU ---")
    username = input("Username: ").strip()
    if not username:
        print("Username tidak boleh kosong.")
        return

    if get_admin_by_username(username):
        print(f"Error: Akun dengan username '{username}' sudah ada.")
        return

    print("Pilih Role:")
    print("1. Admin Biasa (CRUD Dokumen)")
    print("2. Super Admin (CRUD Dokumen & Akun)")
    choice = input("Pilihan [1/2, default 1]: ").strip() or "1"
    role = "superadmin" if choice == "2" else "admin"

    while True:
        password = input("Password: ").strip()
        if len(password) < 4:
            print("Password minimal 4 karakter.")
            continue
        confirm = input("Konfirmasi password: ").strip()
        if password != confirm:
            print("Password tidak cocok. Coba lagi.")
            continue
        break

    pwd_hash = generate_hash(password)
    create_admin(username, pwd_hash, role=role)
    print(f"\n[SUKSES] Akun '{username}' ({role}) berhasil ditambahkan.")


def delete_admin_account():
    list_admins()
    admins = get_all_admins()
    if not admins:
        return

    username = input("\nMasukkan username yang ingin dihapus: ").strip()
    target = get_admin_by_username(username)
    if not target:
        print(f"Akun dengan username '{username}' tidak ditemukan.")
        return

    if target["role"] == "superadmin" and count_superadmins() <= 1:
        print("\n[GAGAL] Tidak dapat menghapus satu-satunya Super Admin di sistem!")
        return

    confirm = input(f"Yakin ingin menghapus akun '{username}'? (y/N): ").strip().lower()
    if confirm == "y":
        delete_admin(target["id"])
        print(f"\n[SUKSES] Akun '{username}' berhasil dihapus.")
    else:
        print("Penghapusan dibatalkan.")


def main():
    initialize_db()
    while True:
        print_header()
        print("1. Lihat Daftar Akun Admin")
        print("2. Buat / Reset Akun Super Admin")
        print("3. Tambah Akun Admin Baru")
        print("4. Hapus Akun Admin")
        print("5. Keluar")
        pilihan = input("\nPilih menu (1-5): ").strip()

        if pilihan == "1":
            list_admins()
        elif pilihan == "2":
            add_or_reset_superadmin()
        elif pilihan == "3":
            add_new_admin()
        elif pilihan == "4":
            delete_admin_account()
        elif pilihan == "5":
            print("\nSampai jumpa!")
            sys.exit(0)
        else:
            print("Pilihan tidak valid.")
        
        input("\nTekan Enter untuk melanjutkan...")


if __name__ == "__main__":
    main()
