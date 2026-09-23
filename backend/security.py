"""
backend/security.py — Sistem Pengamanan API: Rate Limiting & Resolusi Client IP.
Mendukung tunneling Cloudflare (membaca header cf-connecting-ip).
"""

import time
from collections import defaultdict
from typing import Dict, List, Tuple
from fastapi import Request


def get_client_ip(request: Request) -> str:
    """
    Mengambil IP asli klien.
    Jika di belakang Cloudflare Tunnel, ambil dari 'cf-connecting-ip' atau 'x-forwarded-for'.
    """
    cf_ip = request.headers.get("cf-connecting-ip")
    if cf_ip:
        return cf_ip.strip()

    x_forwarded = request.headers.get("x-forwarded-for")
    if x_forwarded:
        return x_forwarded.split(",")[0].strip()

    if request.client and request.client.host:
        return request.client.host

    return "127.0.0.1"


class InMemoryRateLimiter:
    """
    Sliding window in-memory rate limiter sederhana tanpa dependensi luar (Redis/Slowapi).
    """

    def __init__(self, requests_limit: int, window_seconds: int = 60):
        self.requests_limit = requests_limit
        self.window_seconds = window_seconds
        self.records: Dict[str, List[float]] = defaultdict(list)

    def is_allowed(self, key: str) -> Tuple[bool, int]:
        """
        Mengecek apakah request diizinkan untuk key (IP).
        Returns:
            (allowed: bool, retry_after_seconds: int)
        """
        now = time.time()
        timestamps = self.records[key]

        # Bersihkan timestamp di luar jendela waktu
        cutoff = now - self.window_seconds
        valid_timestamps = [t for t in timestamps if t > cutoff]
        self.records[key] = valid_timestamps

        if len(valid_timestamps) >= self.requests_limit:
            # Hitung sisa waktu tunggu
            oldest = valid_timestamps[0]
            retry_after = int(self.window_seconds - (now - oldest)) + 1
            return False, max(1, retry_after)

        # Catat timestamp request saat ini
        self.records[key].append(now)
        return True, 0
