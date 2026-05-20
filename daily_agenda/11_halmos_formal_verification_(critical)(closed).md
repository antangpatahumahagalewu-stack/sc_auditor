# Agenda 11 — Halmos Formal Verification (Pipeline Integration)

> **Project**: sc_auditor (Vyper — Smart Contract Bug Hunter)
> **Status**: ✅ CLOSED
> **Severity**: CRITICAL — Halmos service exist tapi belum terintegrasi ke pipeline utama
> **Dependensi**: Agenda 07 (docker-compose fix), Agenda 10 (observability)

---

## 1. Latar Belakang

Service `04d-scanner-halmos` sudah memiliki scaffold lengkap (app.py, HalmosRunner, intelligence modules), tapi **belum terintegrasi** ke pipeline utama:

| Gap | Dampak | Lokasi |
|-----|--------|--------|
| **Halmos tidak ada di orchestrator** | Pipeline tidak bisa invoke Halmos | `11-orchestrator/src/pipeline.py` |
| **Halmos tidak ada di scanner router** | Scanner service tidak routing ke Halmos | `04-scanner/app.py` |
| **Container halmos tidak di compose** | Service tidak bisa di-start | `docker-compose.yml` |
| **No fallback** | Pipeline skip begitu saja | `11-orchestrator/pipeline.py` |
| **Belum ada integration test** | Tidak bisa verify Halmos work | `tests/` |
| **Halmos belum ada di CLI** | User tidak bisa trigger manual | `cli/commands/scan.py` |

---

## 2. Detail Pekerjaan

### 2.1 Integrasi Halmos ke Scanner Router

File: `services/04-scanner/app.py`

Tambah rute routing ke Halmos service ketika tool="halmos":

```python
# Tambah di SCAN_TOOL_MAP atau tool routing function
SCAN_TOOL_MAP = {
    "slither": ("http://04a-scanner-slither:8000", "/scan"),
    "echidna": ("http://04b-scanner-echidna:8000", "/scan"),
    "forge":   ("http://04c-scanner-forge:8000", "/scan"),
    "halmos":  ("http://04d-scanner-halmos:8017", "/scan"),   # 🆕
    "mythril": ("http://05-scanner-mythril:8000", "/scan"),
}
```

### 2.2 Integrasi Halmos ke Orchestrator Pipeline

File: `services/11-orchestrator/src/pipeline.py`

Pipeline state machine perlu tambah stage (atau integrasi di SCANNING):

```python
# Di pipeline state machine — setelah SCANNING, tambah HALMOS_ANALYSIS
# atau integrasikan sebagai tool dalam SCANNING stage

class PipelineStage(str, Enum):
    PENDING = "PENDING"
    FETCHING_PROGRAM = "FETCHING_PROGRAM"
    FETCHING_SOURCE = "FETCHING_SOURCE"
    SCANNING = "SCANNING"         # Slither + Mythril + Echidna
    HALMOS_ANALYSIS = "HALMOS_ANALYSIS"   # 🆕 Formal verification
    AI_ANALYSIS = "AI_ANALYSIS"
    CLASSIFYING = "CLASSIFYING"
    EXPLOITING = "EXPLOITING"
    REPORTING = "REPORTING"
    NOTIFYING = "NOTIFYING"
    COMPLETED = "COMPLETED"
```

Pipeline flow dengan Halmos:

```
                   ┌─────────────────────┐
                   │   FETCHING SOURCE    │
                   └──────────┬──────────┘
                              │
                    ┌─────────▼─────────┐
                    │     SCANNING       │
                    │  Slither+Echidna   │
                    │  +Mythril+Forge    │
                    └─────────┬──────────┘
                              │
                    ┌─────────▼─────────┐     ┌─────────────────────┐
                    │  HALMOS_ANALYSIS   │────▶│  SYMBOLIC EXECUTION │
                    │  Formal Verif.     │     │  Counterexamples    │
                    └─────────┬──────────┘     └─────────────────────┘
                              │
                    ┌─────────▼─────────┐
                    │   AI_ANALYSIS      │
                    └─────────┬──────────┘
                              │
                              ▼
```

### 2.3 Container di Docker Compose

File: `docker-compose.yml`

Pastikan service `04d-scanner-halmos` ada di compose dengan konfigurasi yang benar:

```yaml
04d-scanner-halmos:
  <<: *service-base
  container_name: vyper-scanner-halmos
  build:
    context: ./services/04d-scanner-halmos
  ports:
    - "8017:8017"
  volumes:
    - scanner-halmos-data:/data/scanner-halmos
    - scanner-halmos-solc:/root/.solcx
    - shared-tmp:/tmp
  depends_on:
    - 01-config
```

### 2.4 CLI Integration

File: `cli/commands/scan.py`

Tambah `--halmos` flag:

```python
@app.command()
def scan(
    source: str = Argument(..., help="Contract address or file path"),
    tools: str = Option("slither,mythril", "--tools", "-t", help="Comma-separated tools"),
    halmos: bool = Option(False, "--halmos", help="Enable Halmos formal verification"),
):
    """Scan a smart contract for vulnerabilities."""
    if halmos:
        tools = f"{tools},halmos"
    ...
```

### 2.5 Halmos Runner Enhancement

File: `services/04d-scanner-halmos/src/halmos.py`

Review & enhance HalmosRunner jika diperlukan:

| Area | Status | Action |
|------|--------|--------|
| `run()` method | ✅ Ada | Review — pastikan output format kompatibel |
| `check_available()` | ✅ Ada | OK |
| `check_forge()` | ✅ Ada | OK |
| Dogfood testing | ❌ Belum | Tambah test dengan kontrak sederhana |
| Large contract timeout | ❌ Belum | Tambah configurable timeout |

### 2.6 Integration Test

File baru: `tests/test_halmos_pipeline.py`

```python
"""Test Halmos integration with main scanner & orchestrator pipeline."""

async def test_halmos_direct_scan():
    """Scan kontrak via Halmos service langsung."""
    async with httpx.AsyncClient(base_url="http://04d-scanner-halmos:8017") as client:
        resp = await client.post("/scan", json={
            "sources": {"Counter.sol": SIMPLE_COUNTER},
            "timeout": 60,
        })
        assert resp.status_code == 200
        data = resp.json()["data"]
        assert "findings" in data

async def test_halmos_via_scanner_router():
    """Scan via main scanner dengan tool=halmos."""
    async with httpx.AsyncClient(base_url="http://04-scanner:8003") as client:
        resp = await client.post("/scan", json={
            "sources": {"Counter.sol": SIMPLE_COUNTER},
            "tools": ["halmos"],
        })
        assert resp.status_code == 200

async def test_halmos_in_pipeline():
    """Pipeline orchestrator dengan Halmos stage aktif."""
    # Trigger audit → pipeline harus include Halmos
    ...

async def test_counterexample_parsing():
    """Parse Halmos counterexample → Finding format."""
    ...
```

### 2.7 Dashboard Enhancement

File: `services/15-dashboard/frontend/src/pages/ScannerDetail.tsx`

Tambah tab/informasi untuk Halmos:
- Counterexample visualization
- Execution path diagram
- Assertion violation details
- Gas estimation dari symbolic results

---

## 3. Struktur File

```
services/
├── 04-scanner/
│   └── app.py                              # ✏️ + halmos di SCAN_TOOL_MAP

services/11-orchestrator/src/
├── pipeline.py                              # ✏️ + HALMOS_ANALYSIS stage
├── models.py                                # ✏️ + PipelineStage enum

services/04d-scanner-halmos/src/
├── halmos.py                                # ✏️ Enhancement (timeout, large contract)
├── intelligence/                            # ✅ Already built

cli/commands/
├── scan.py                                  # ✏️ + --halmos flag

tests/
├── test_halmos_pipeline.py                  # 🆕 Integration test

docker-compose.yml                           # ✏️ + 04d-scanner-halmos service

services/15-dashboard/frontend/src/pages/
├── ScannerDetail.tsx                        # ✏️ + Halmos tab
```

---

## 4. Task List

| # | Task | File | Estimasi | Prioritas |
|---|------|------|----------|-----------|
| T1 | Integrasi Halmos ke scanner router | `04-scanner/app.py` | 10 min | P0 |
| T2 | Integrasi Halmos ke orchestrator pipeline | `11-orchestrator/src/pipeline.py` | 30 min | P0 |
| T3 | Tambah stage HALMOS_ANALYSIS di state machine | `11-orchestrator/src/models.py` | 10 min | P0 |
| T4 | Pastikan container halmos di docker-compose | `docker-compose.yml` | 5 min | P0 |
| T5 | Tambah --halmos flag di CLI scan command | `cli/commands/scan.py` | 10 min | P1 |
| T6 | Dogfood test: scan kontrak sederhana | `tests/test_halmos_pipeline.py` | 20 min | P1 |
| T7 | Integration test: halmos via scanner router | `tests/test_halmos_pipeline.py` | 20 min | P1 |
| T8 | Integration test: halmos di pipeline penuh | `tests/test_halmos_pipeline.py` | 30 min | P1 |
| T9 | Review HalmosRunner timeout handling | `04d-scanner-halmos/src/halmos.py` | 10 min | P2 |
| T10 | Dashboard: Halmos tab di ScannerDetail | `frontend/src/pages/ScannerDetail.tsx` | 20 min | P2 |
| | **Total** | | **~165 menit** | |

---

## 5. Quality Gate

| Dimensi | Target | Cara Ukur |
|---------|--------|-----------|
| Correctness | 95% | Halmos scan via scanner router return valid findings |
| Performance | 85% | Halmos scan timeout handling, large contract < 5 menit |
| Security | 85% | Sandboxed Halmos execution, timeout prevent resource hog |
| Maintainability | 90% | Tool routing pattern konsisten dengan scanner lain |
| Completeness | 100% | Halmos bisa di-trigger dari CLI, API Scanner, dan Pipeline |
| Alignment | 100% | Pipeline flow include Halmos tanpa break existing tools |

---

## 6. Risiko & Mitigasi

| Risiko | Likelihood | Dampak | Mitigasi |
|--------|-----------|--------|----------|
| Halmos timeout di kontrak besar | Tinggi | Pipeline stuck | Configurable timeout + timeout → skip gracefully |
| Halmos butuh Foundry test structure | Sedang | Tidak semua kontrak compatible | Fallback: skip + log warning |
| Halmos output format berubah | Rendah | Parsing broken | Version check + resilient parser |
| Halmos + container size besar | Sedang | Disk usage | Multi-stage build, shared Foundry cache |

---

*Dibuat: 2026-05-20 | Status: OPEN | Dependensi: Agenda 07, 10*
