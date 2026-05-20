# Agenda 07 — CI/CD Pipeline & Infrastructure Hardening

> **Project**: sc_auditor (Vyper — Smart Contract Bug Hunter)
> **Status**: ✅ CLOSED (2026-05-20)
> **Severity**: CRITICAL — Blocker untuk semua agenda berikutnya
> **Dependensi**: Tidak ada (root fix)

---

## 1. Latar Belakang

Hasil audit project menemukan **3 critical infrastructure issues**:

| # | Issue | Lokasi | Dampak |
|---|-------|--------|--------|
| 1 | **Docker Compose broken** | `docker-compose.yml` line 117-126, 198-221 | Semua service ga bisa di-deploy sebagai unified system |
| 2 | **Zero CI/CD** | `.github/workflows/` tidak ada | Tidak ada automated build, test, atau deployment |
| 3 | **Zero linting/QA** | Tidak ada pre-commit, eslint, ruff | Kualitas kode tidak terjamin, bug masuk diam-diam |
| 4 | **Missing `__init__.py`** | `09-reporter/src/`, `12-webhook/src/` | 2 Python packages broken, cannot import |

---

## 2. Detail Pekerjaan

### 2.1 Fix Docker Compose YAML

File: `docker-compose.yml`

**Masalah #1 — Line 117: indentasi 5 spasi (harus 4)**
```yaml
# SEBELUM (RUSAK):
    05-scanner-mythril:        # ← 5 spasi
    <<: *service-base          # ← 4 spasi → INVALID YAML
# SESUDAH (BENAR):
   05-scanner-mythril:         # ← 4 spasi
     <<: *service-base         # ← 4 spasi
```

**Masalah #2 — Line 198: indentasi inkonsisten**
```yaml
# SEBELUM (RUSAK):
    11-orchestrator:           # ← 5 spasi
      <<: *service-base        # ← 6 spasi
# SESUDAH (BENAR):
   11-orchestrator:            # ← 4 spasi
     <<: *service-base         # ← 4 spasi
```

**Masalah #3 — Line 212: depends_on format broken**
```yaml
# SEBELUM (RUSAK):
      - 04c-scanner-forge     # ← 6 spasi + dash (WRONG)
      - 04d-scanner-halmos    # ← Same
# SESUDAH (BENAR):
        - 04c-scanner-forge   # ← 8 spasi + dash (correct YAML list)
        - 04d-scanner-halmos
```

**Validasi**: `docker-compose config` harus return exit code 0.

### 2.2 GitHub Actions CI Pipeline

File baru: `.github/workflows/ci.yml`

```yaml
Pipeline:
  trigger: push ke main, PR ke main
  stages:
    1. lint-python: ruff check services/*/src/
    2. lint-frontend: cd frontend && npx eslint src/
    3. type-check: cd frontend && npx tsc --noEmit
    4. test-backend: pytest tests/ -v
    5. build-docker: docker-compose build
    6. security-scan: (optional) bandit / trivy
```

File baru: `.github/workflows/docker-build.yml`
- Build & push images ke registry (opsional: GitHub Container Registry)
- Cache layers untuk mempercepat build

File baru: `.github/workflows/security-scan.yml`
- Weekly schedule: scan dependencies for CVEs
- Gunakan `pip-audit` untuk Python, `npm audit` untuk frontend

### 2.3 Pre-commit Hooks + Linter Configuration

File baru: `.pre-commit-config.yaml`

| Hook | Repo | File Pattern |
|------|------|-------------|
| ruff | `astral-sh/ruff-pre-commit` | `*.py` |
| eslint | `pre-commit/mirrors-eslint` | `*.ts`, `*.tsx` |
| yamllint | `adrienverge/yamllint` | `*.yml`, `*.yaml` |
| trailing-whitespace | pre-commit-hooks | semua |
| end-of-file-fixer | pre-commit-hooks | semua |
| check-json | pre-commit-hooks | `*.json` |

File baru (opsional): `pyproject.toml` — konfigurasi ruff
```toml
[tool.ruff]
target-version = "py312"
line-length = 100

[tool.ruff.lint]
select = ["E", "F", "I", "N", "W", "UP"]
ignore = ["E501"]  # line length handled by formatter
```

### 2.4 Fix Missing `__init__.py`

File: `services/09-reporter/src/__init__.py`
```python
"""Reporter Service — generates audit reports (Immunefi + Full) in Markdown/PDF."""
```

File: `services/12-webhook/src/__init__.py`
```python
"""Webhook Service — dispatches events to external endpoints."""
```

---

## 3. Struktur File

```
sc_auditor/
│
├── .github/
│   └── workflows/
│       ├── ci.yml                    # 🆕 Main CI pipeline
│       ├── docker-build.yml          # 🆕 Docker build workflow
│       └── security-scan.yml         # 🆕 Weekly security scan
│
├── .pre-commit-config.yaml           # 🆕 Pre-commit hooks
├── pyproject.toml                    # 🆕 (opsional) Ruff config
│
├── docker-compose.yml                # ✏️ Fix YAML indentation
│
└── services/
    ├── 09-reporter/src/
    │   └── __init__.py               # 🆕 Missing file
    └── 12-webhook/src/
        └── __init__.py               # 🆕 Missing file
```

---

## 4. Task List

| # | Task | File | Estimasi |
|---|------|------|----------|
| T1 | Fix docker-compose.yml indentasi (05-scanner-mythril) | `docker-compose.yml` | 5 min |
| T2 | Fix docker-compose.yml indentasi (11-orchestrator) | `docker-compose.yml` | 5 min |
| T3 | Validasi: `docker-compose config` | - | 2 min |
| T4 | Buat GitHub Actions CI pipeline | `.github/workflows/ci.yml` | 15 min |
| T5 | Buat GitHub Actions docker build | `.github/workflows/docker-build.yml` | 10 min |
| T6 | Buat GitHub Actions security scan | `.github/workflows/security-scan.yml` | 10 min |
| T7 | Buat pre-commit config | `.pre-commit-config.yaml` | 10 min |
| T8 | Buat pyproject.toml ruff config | `pyproject.toml` | 5 min |
| T9 | Buat `__init__.py` untuk 09-reporter | `services/09-reporter/src/__init__.py` | 2 min |
| T10 | Buat `__init__.py` untuk 12-webhook | `services/12-webhook/src/__init__.py` | 2 min |
| | **Total** | | **~66 menit** |

---

## 5. Quality Gate

| Dimensi | Target | Cara Ukur |
|---------|--------|-----------|
| Correctness | 100% | `docker-compose config` sukses, CI passing |
| Performance | N/A | Infrastructure task |
| Security | 90% | Security scan workflow running |
| Maintainability | 90% | Pre-commit hooks aktif, lint passing |
| Completeness | 100% | Semua task selesai |
| Alignment | 100% | Semua issue dari audit ter-cover |

---

*Dibuat: 2026-05-20 | Status: OPEN | Blocker untuk Agenda 08-10*
