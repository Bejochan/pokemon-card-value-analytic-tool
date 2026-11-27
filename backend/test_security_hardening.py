import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from starlette.testclient import TestClient
from app.main import app, MAX_BASE64_CHARS, MAX_FILE_SIZE_BYTES, AI_RATE_LIMIT_PER_MINUTE

client = TestClient(app)

def test_health():
    res = client.get("/health")
    assert res.status_code == 200
    data = res.json()
    assert data["status"] == "healthy"
    print("[PASS] Test Healthcheck 200 OK")

def test_cors():
    # Test valid origin
    headers = {
        "Origin": "http://localhost:5173",
        "Access-Control-Request-Method": "POST",
        "Access-Control-Request-Headers": "content-type"
    }
    res = client.options("/identify", headers=headers)
    assert res.status_code == 200
    assert res.headers.get("access-control-allow-origin") == "http://localhost:5173"
    assert res.headers.get("access-control-allow-credentials") == "true"
    print("[PASS] Test CORS Whitelist (localhost:5173)")

    # Test vercel preview regex
    headers_vercel = {
        "Origin": "https://regokemon-test.vercel.app",
        "Access-Control-Request-Method": "GET"
    }
    res_vercel = client.options("/sets", headers=headers_vercel)
    assert res_vercel.status_code == 200
    assert res_vercel.headers.get("access-control-allow-origin") == "https://regokemon-test.vercel.app"
    print("[PASS] Test CORS Vercel Subdomain Regex")

def test_payload_limit_base64():
    # Buat payload base64 raksasa (> 22 MB)
    huge_base64 = "A" * (MAX_BASE64_CHARS + 1024)
    res = client.post("/identify", json={"image": huge_base64})
    assert res.status_code == 413, f"Expected 413, got {res.status_code}"
    print(f"[PASS] Test Payload Too Large Base64: 413 caught ({res.json()['detail']})")

def test_payload_limit_file():
    # Buat file raksasa (> 15 MB)
    huge_file = b"0" * (MAX_FILE_SIZE_BYTES + 2048)
    files = {"file": ("huge_card.jpg", huge_file, "image/jpeg")}
    res = client.post("/upload/identify", files=files)
    assert res.status_code == 413, f"Expected 413, got {res.status_code}"
    print(f"[PASS] Test Payload Too Large Multipart File: 413 caught ({res.json()['detail']})")

def test_rate_limiting():
    # Panggil endpoint AI berulang kali hingga batas terlampaui
    # Batas default = 60 req/menit
    print(f"[*] Menguji Rate Limiter AI ({AI_RATE_LIMIT_PER_MINUTE} req/menit)...")
    hit_429 = False
    for i in range(AI_RATE_LIMIT_PER_MINUTE + 5):
        # Pakai validasi ringan pada endpoint heavy agar uji rate limiter tidak memicu
        # 60x kueri Supabase / inferensi Chronos yang berisiko melewati jendela 60 detik.
        res = client.post("/cards/base1-4/condition", json={})
        if res.status_code == 429:
            hit_429 = True
            print(f"[PASS] Rate Limiter AI sukses memblokir spam pada request ke-{i+1}: 429 Too Many Requests!")
            assert "Retry-After" in res.headers
            print(f"       Detail: {res.json()['detail']}")
            print(f"       Retry-After: {res.headers['Retry-After']} detik")
            break
    assert hit_429, "Rate limiter gagal memicu 429!"

if __name__ == "__main__":
    print("=== PENGUJIAN KEAMANAN & PROTEKSI API REGOKEMON ===")
    test_health()
    test_cors()
    test_payload_limit_base64()
    test_payload_limit_file()
    test_rate_limiting()
    print("=== SELURUH PENGUJIAN KEAMANAN BERHASIL (100% LULUS) ===")

