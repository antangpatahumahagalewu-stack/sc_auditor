# Agenda 09 — Security Hardening (No Auth)

> **Project**: sc_auditor (Vyper — Smart Contract Bug Hunter)
> **Status**: ✅ CLOSED
> **Severity**: HIGH — CORS wildcard, no rate limiting, no security headers
> **Dependensi**: Agenda 07 (docker-compose fix), Agenda 08 (test suite)
> **Catatan**: Project ini personal + tidak dipublikasikan → **tidak perlu login/JWT**. Fokus pada hardening teknis.

---

## 1. Latar Belakang

Hasil audit project menemukan celah security non-auth:

| Celah | Dampak | Lokasi |
|-------|--------|--------|
| CORS terbuka | `allow_origins=["*"]` — semua origin bisa call API | Dashboard `app.py` |
| Tidak ada rate limiting | Rentan resource exhaustion | ALL services |
| Tidak ada security headers | Rentan clickjacking, MIME sniffing | Dashboard `app.py` |
| Tidak ada API key | Service-to-service tanpa gembok | ALL internal services |

---

## 2. Detail Pekerjaan

### 2.1 CORS Hardening

File: `services/15-dashboard/app.py`

```python
# SEBELUM (INSECURE):
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],          # ← SEMUA ORIGIN DIPERBOLEHKAN
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# SESUDAH (SECURE — localhost only):
ALLOWED_ORIGINS = [
    "http://localhost:8000",
    "http://localhost:5173",
    "http://127.0.0.1:8000",
    "http://127.0.0.1:5173",
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE"],
    allow_headers=["Content-Type", "X-API-Key"],
)
```

### 2.2 Security Headers

File: `services/15-dashboard/app.py` (tambah middleware)

```python
from starlette.middleware.base import BaseHTTPMiddleware

class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request, call_next):
        response = await call_next(request)
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["X-XSS-Protection"] = "1; mode=block"
        response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
        if request.url.scheme == "https":
            response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains"
        return response

app.add_middleware(SecurityHeadersMiddleware)
```

### 2.3 Rate Limiting (Local Dev Friendly)

File: `services/15-dashboard/app.py`

Gunakan `slowapi` dengan konfigurasi longgar (local dev — prevent accidental abuse, bukan hard security):

```python
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address

limiter = Limiter(key_func=get_remote_address)
app.state.limiter = limiter
app.add_exception_handler(429, _rate_limit_exceeded_handler)

# Rate limits (longgar untuk local dev):
# - /events SSE : 100 requests/minute (mencegah looping)
# - /api/cases POST : 30 requests/minute
# - /api/daemon/* : 10 requests/minute
# - All others : 120 requests/minute (default longgar)
```

Tambahkan `@limiter.limit()` ke endpoint-endpoint tertentu:
- `api_daemon_start`, `api_daemon_stop` → `"10/minute"`
- `api_create_case` → `"30/minute"`
- SSE endpoint → `"100/minute"`

### 2.4 Service-to-Service API Key Auth (Opsional — Internal Only)

File baru: `services/01-config/src/api_keys.py`

```python
"""API Key management for internal service-to-service auth.

Setiap service punya unique API key. Saat service A call service B,
ia menyertakan header:
  X-API-Key: <service_api_key>
  X-Service-Name: <service_name>

Karena project personal, ini adalah OPTIONAL hardening —
keys bisa di-generate otomatis dan tidak perlu rotasi rutin.
"""

import secrets
from typing import Dict, Optional

# Default keys — auto-generated, disimpan di file YAML config
# Override via Config Service → settings page
SERVICE_API_KEYS: Dict[str, str] = {}

def generate_api_key() -> str:
    """Generate random 32-char hex API key."""
    return secrets.token_hex(16)

def get_or_create_key(service_name: str, storage_path: str = "") -> str:
    """Get existing key or generate + persist new one."""
    if service_name in SERVICE_API_KEYS:
        return SERVICE_API_KEYS[service_name]
    key = generate_api_key()
    SERVICE_API_KEYS[service_name] = key
    # Persist to storage if path provided
    if storage_path:
        _persist_keys(storage_path)
    return key

def validate_service_api_key(key: str, service_name: str) -> bool:
    """Validate service API key.

    Returns True if key matches OR if API key auth is disabled.
    (Disabled = empty string — dev mode no-auth.)
    """
    if not SERVICE_API_KEYS:
        return True  # API key auth disabled — dev mode
    expected = SERVICE_API_KEYS.get(service_name)
    if expected is None:
        return False
    return secrets.compare_digest(key, expected)

def _persist_keys(path: str) -> None:
    """Save keys to YAML file for persistence across restarts."""
    import yaml
    import os
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w") as f:
        yaml.dump({"api_keys": SERVICE_API_KEYS}, f)

def load_keys(path: str) -> None:
    """Load keys from YAML file."""
    import yaml
    import os
    if os.path.exists(path):
        with open(path) as f:
            data = yaml.safe_load(f) or {}
            SERVICE_API_KEYS.update(data.get("api_keys", {}))
```

**Implementation di proxy (dashboard):**
```python
# services/15-dashboard/src/proxy.py
class ServiceProxy:
    async def start(self) -> None:
        self._client = httpx.AsyncClient(
            timeout=httpx.Timeout(self._timeout),
            headers={
                "User-Agent": "Vyper-Dashboard/1.0",
                "X-API-Key": self._get_api_key(),
                "X-Service-Name": "15-dashboard",
            },
        )
    
    def _get_api_key(self) -> str:
        """Get dashboard's API key from env or config."""
        return os.environ.get("DASHBOARD_API_KEY", "dev-mode-no-key")
```

---

## 3. Struktur File

```
services/15-dashboard/
├── app.py                           # ✏️ + CORS hardening, security headers, rate limiting
│
services/01-config/src/
├── api_keys.py                      # 🆕 API key management (optional)
```

**Tidak ada perubahan Frontend** — karena project personal, tidak perlu login page, AuthGuard, atau auth client.

---

## 4. Task List

| # | Task | File | Estimasi |
|---|------|------|----------|
| T1 | CORS hardening — ganti `["*"]` ke localhost list | `services/15-dashboard/app.py` | 5 min |
| T2 | Security headers middleware | `services/15-dashboard/app.py` | 10 min |
| T3 | Rate limiting via slowapi | `services/15-dashboard/app.py` | 15 min |
| T4 | API key management module (optional) | `services/01-config/src/api_keys.py` | 15 min |
| T5 | Update proxy dengan API key header | `services/15-dashboard/src/proxy.py` | 10 min |
| T6 | Update requirements.txt (slowapi) | `services/15-dashboard/requirements.txt` | 2 min |
| | **Total** | | **~57 menit** |

---

## 5. Quality Gate

| Dimensi | Target | Cara Ukur |
|---------|--------|-----------|
| Correctness | 95% | CORS block external origin, rate limit triggers 429 |
| Performance | 90% | Security headers & CORS < 1ms overhead |
| Security | 90% | No wildcard CORS, headers present, rate limit active |
| Maintainability | 90% | All security config in one place (app startup) |
| Completeness | 100% | CORS + headers + rate limiting all implemented |
| Alignment | 100% | Zero auth friction — all existing features unchanged |

---

## 6. Perubahan dari Versi Sebelumnya

| Item | Sebelum (09_auth_security) | Sesudah (09_security_hardening) |
|------|---------------------------|----------------------------------|
| JWT login | ✅ Ada | ❌ **Removed** (personal project, tidak perlu) |
| Login page | ✅ Ada | ❌ **Removed** |
| AuthGuard | ✅ Ada | ❌ **Removed** |
| Auth client lib | ✅ Ada | ❌ **Removed** |
| API key auth | ✅ Wajib | ✅ **Optional** (dev mode no-key by default) |
| Rate limiting | ✅ Ada | ✅ **Ada** (lebih longgar untuk dev) |
| CORS hardening | ✅ Ada | ✅ **Ada** |
| Security headers | ✅ Ada | ✅ **Ada** |

---

*Dibuat: 2026-05-20 | Status: OPEN | Dependensi: Agenda 07, 08*
