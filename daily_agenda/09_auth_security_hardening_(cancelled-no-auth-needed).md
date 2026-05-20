# Agenda 09 — Auth & Security Hardening

> **Project**: sc_auditor (Vyper — Smart Contract Bug Hunter)
> **Status**: 🔴 OPEN
> **Severity**: CRITICAL — Zero authentication di semua service
> **Dependensi**: Agenda 08 (test harus ada untuk validasi auth)

---

## 1. Latar Belakang

Hasil audit project menemukan **zero authentication**:

| Celah | Dampak | Lokasi |
|-------|--------|--------|
| Tidak ada login | Siapa pun bisa akses dashboard | Frontend + Backend |
| Tidak ada JWT | Semua API endpoint unprotected | ALL 20 services |
| Tidak ada API key | Service-to-service communication tanpa auth | ALL internal |
| Tidak ada rate limiting | Rentan brute force / DoS | ALL services |
| CORS terbuka | `allow_origins=["*"]` — siapa pun bisa call API | Dashboard |

---

## 2. Detail Pekerjaan

### 2.1 Dashboard Auth (Frontend + Backend)

#### Backend: Auth API

File: `services/15-dashboard/app.py` (tambah endpoint)

```
POST /api/auth/login      → verify credentials, return JWT
POST /api/auth/verify     → verify JWT token validity
GET  /api/auth/me         → get current user info
```

Model baru di `services/15-dashboard/src/models.py`:

```python
class LoginRequest(BaseModel):
    username: str
    password: str

class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    expires_at: str
```

File baru: `services/15-dashboard/src/auth.py`

```python
"""Auth module — JWT token generation + validation.

- Uses python-jose for JWT
- Password hashing via bcrypt
- Configurable JWT secret via Config Service
- Default credentials: admin / vyper-admin (MUST be changed)
"""

SECRET_KEY = "vyper-default-secret-change-me"  # Overridden via Config
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 480  # 8 hours

def create_access_token(username: str) -> str:
    """Create JWT token with expiration."""
    ...

def verify_token(token: str) -> Optional[dict]:
    """Verify and decode JWT token."""
    ...

def get_password_hash(password: str) -> str:
    """Hash password with bcrypt."""
    ...

def verify_password(plain: str, hashed: str) -> bool:
    """Verify password against hash."""
    ...
```

FastAPI middleware untuk proteksi route:

```python
# Di app.py
from fastapi import Depends, HTTPException
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials

security = HTTPBearer()

def require_auth(credentials: HTTPAuthorizationCredentials = Depends(security)):
    """Dependency: require valid JWT token."""
    payload = verify_token(credentials.credentials)
    if payload is None:
        raise HTTPException(status_code=401, detail="Invalid token")
    return payload

# Protected routes:
@app.post("/api/daemon/start", dependencies=[Depends(require_auth)])
async def api_daemon_start():
    ...

@app.put("/api/config/{key}", dependencies=[Depends(require_auth)])
async def api_set_config(key: str, body: dict):
    ...
```

**Route protection matrix:**

| Route Group | Auth Required | Notes |
|-------------|---------------|-------|
| `/health` | ❌ No | Public |
| `/api/auth/*` | ❌ No | Public (login) |
| `/events` | ❌ No | SSE stream |
| `/api/cases` GET | ❌ No | Read-only, public |
| `/api/cases` POST | ✅ Yes | Agent-only (API key) |
| `/api/cases/{id}/close` | ✅ Yes | User action |
| `/api/daemon/*` | ✅ Yes | Admin |
| `/api/config/*` | ✅ Yes | Admin |
| `/api/feedback` POST | ❌ No | User feedback |
| `{path:path}` (SPA) | ❌ No | Static files |

#### Frontend: Login Page

File baru: `services/15-dashboard/frontend/src/pages/Login.tsx`

```
Route: /login
Fungsi: Form username + password → POST /api/auth/login → simpan token
```

File baru: `services/15-dashboard/frontend/src/components/AuthGuard.tsx`

```tsx
// Wrapper component: redirect ke /login jika tidak ada token
function AuthGuard({ children }: { children: React.ReactNode }) {
  const token = localStorage.getItem('vyper_token');
  if (!token) return <Navigate to="/login" />;
  return <>{children}</>;
}
```

File baru: `services/15-dashboard/frontend/src/lib/auth.ts`

```typescript
export const auth = {
  login: (username: string, password: string) => request<TokenResponse>('/api/auth/login', { method: 'POST', body: JSON.stringify({ username, password }) }),
  logout: () => { localStorage.removeItem('vyper_token'); },
  isAuthenticated: () => !!localStorage.getItem('vyper_token'),
  getToken: () => localStorage.getItem('vyper_token'),
};
```

Update `App.tsx`:
```tsx
<Route path="/login" element={<Login />} />
<Route element={<AuthGuard><Layout /></AuthGuard>}>
  {/* existing protected routes */}
</Route>
```

### 2.2 Service-to-Service API Key Auth

File baru: `services/01-config/src/api_keys.py`

```python
"""API Key management for internal service-to-service auth.

Setiap service punya unique API key yang disimpan di Config Service.
Saat service A call service B, ia harus menyertakan header:
  X-API-Key: <service_a_key>
  X-Service-Name: 04a-scanner-slither
"""

SERVICE_API_KEYS = {
    "01-config": "cfg_key_...",
    "02-immunefi": "imm_key_...",
    # ... auto-generated on first deploy
}

def validate_service_api_key(key: str, service_name: str) -> bool:
    """Validate service API key."""
    ...
```

**Implementation di proxy (dashboard):**
```python
# services/15-dashboard/src/proxy.py
class ServiceProxy:
    async def _request(self, method, path, **kwargs):
        headers = kwargs.setdefault("headers", {})
        headers["X-API-Key"] = self._get_api_key()
        headers["X-Service-Name"] = "15-dashboard"
        ...
```

### 2.3 Rate Limiting

File: `services/15-dashboard/app.py` (tambah middleware)

```python
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address

limiter = Limiter(key_func=get_remote_address)
app.state.limiter = limiter
app.add_exception_handler(429, _rate_limit_exceeded_handler)

# Rate limits:
# - /api/auth/* : 5 requests/minute (brute force protection)
# - /api/cases POST : 10 requests/minute
# - /api/daemon/* : 3 requests/minute
# - All others : 60 requests/minute
```

### 2.4 CORS Hardening

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

# SESUDAH (SECURE):
ALLOWED_ORIGINS = os.environ.get(
    "CORS_ORIGINS",
    "http://localhost:8000,http://localhost:5173"
).split(",")

app.add_middleware(
    CORSMiddleware,
    allow_origins=ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE"],
    allow_headers=["Authorization", "Content-Type", "X-API-Key"],
)
```

### 2.5 Security Headers

File: `services/15-dashboard/app.py` (tambah middleware)

```python
from starlette.middleware.base import BaseHTTPMiddleware

class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request, call_next):
        response = await call_next(request)
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["X-XSS-Protection"] = "1; mode=block"
        response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains"
        response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
        return response

app.add_middleware(SecurityHeadersMiddleware)
```

---

## 3. Struktur File

```
services/15-dashboard/
├── app.py                           # ✏️ + Auth routes, middleware, CORS hardening
├── src/
│   ├── auth.py                      # 🆕 JWT + bcrypt module
│   ├── models.py                    # ✏️ + Auth models
│   └── proxy.py                     # ✏️ + API key headers
│
├── frontend/src/
│   ├── App.tsx                      # ✏️ + /login route, AuthGuard
│   ├── lib/
│   │   └── auth.ts                  # 🆕 Auth client
│   ├── components/
│   │   └── AuthGuard.tsx            # 🆕 Route protection
│   └── pages/
│       └── Login.tsx                # 🆕 Login page
│
services/01-config/src/
├── api_keys.py                      # 🆕 API key management
└── app.py                           # ✏️ + API key endpoints
```

---

## 4. Task List

| # | Task | File | Estimasi |
|---|------|------|----------|
| T1 | Buat auth module (JWT + bcrypt) | `services/15-dashboard/src/auth.py` | 15 min |
| T2 | Tambah auth models | `services/15-dashboard/src/models.py` | 5 min |
| T3 | Tambah auth API endpoints | `services/15-dashboard/app.py` | 10 min |
| T4 | Implement AuthGuard component | `frontend/src/components/AuthGuard.tsx` | 10 min |
| T5 | Buat Login page | `frontend/src/pages/Login.tsx` | 20 min |
| T6 | Buat auth client lib | `frontend/src/lib/auth.ts` | 5 min |
| T7 | Update App.tsx routes + AuthGuard | `frontend/src/App.tsx` | 5 min |
| T8 | Tambah API key management | `services/01-config/src/api_keys.py` | 15 min |
| T9 | Update proxy dengan API key header | `services/15-dashboard/src/proxy.py` | 10 min |
| T10 | Implement rate limiting | `services/15-dashboard/app.py` | 10 min |
| T11 | CORS hardening | `services/15-dashboard/app.py` | 5 min |
| T12 | Security headers middleware | `services/15-dashboard/app.py` | 5 min |
| T13 | Update requirements.txt (python-jose, bcrypt, slowapi) | `services/15-dashboard/requirements.txt` | 2 min |
| | **Total** | | **~117 menit** |

---

## 5. Quality Gate

| Dimensi | Target | Cara Ukur |
|---------|--------|-----------|
| Correctness | 95% | Auth flow working: login → token → protected route |
| Performance | 85% | Rate limiting tidak slow down normal requests |
| Security | 95% | Route protection matrix verified, no public admin routes |
| Maintainability | 90% | Auth logic terpusat di auth.py |
| Completeness | 100% | Semua route di matrix terproteksi |
| Alignment | 100% | Auth non-blocking untuk read-only public routes |

---

*Dibuat: 2026-05-20 | Status: OPEN | Dependensi: Agenda 08*
