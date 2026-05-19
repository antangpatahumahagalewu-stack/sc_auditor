# Scanner Service Split Plan — Service 04 → 04a, 04b, 04c

> **Tujuan**: Memecah service 04 (scanner) menjadi 3 service independen:
> Slither, Echidna, dan Forge. Mythril (service 05) sudah terpisah.

---

## 1. Target Arsitektur — Akhir

```
Sebelum:
Orchestrator ──POST /scan──→ Service 04 (scanner)
                                ├── Slither (inline)
                                ├── Echidna (inline)
                                ├── Forge (inline)
                                └── Mythril ──HTTP→ Service 05

Sesudah:
Orchestrator ──POST──→ Service 04a (slither)    port 8014
             ──POST──→ Service 04b (echidna)    port 8015
             ──POST──→ Service 04c (forge)      port 8016
             ──POST──→ Service 05  (mythril)    port 8013 (existing)
```

---

## 2. Shared Library — `vyper_lib/`

Semua model dan utility yang dipakai bersama diekstrak ke `vyper_lib/` di root.

### Struktur
```
vyper_lib/
├── __init__.py
├── models.py          # Finding, ToolResult, ForgeResult, ApiResponse, Meta, dll
├── solc_manager.py    # SolcManager (compiler version management)
├── deps.py            # DependencyResolver
└── slither_config.py  # SlitherConfigBuilder (hanya dipakai slither)
```

### Perubahan pada file yang ada

**`vyper_lib/models.py`** — Isinya dari `services/04-scanner/src/models.py`:
- `Finding`
- `ToolResult`
- `ForgeResult`
- `ScanRequest`
- `ScanResponse`
- `ApiResponse`, `Meta`
- `ToolInfo`, `InstallResult`, `HealthData`

Semua service baru akan import dari `vyper_lib.models` instead of local models.

**`vyper_lib/solc_manager.py`** — Isinya dari `services/04-scanner/src/solc_manager.py`:
- Class `SolcManager`
- Factory `create_solc_manager()`

### Cara Pakai di Dockerfile
```dockerfile
# Setiap service baru:
COPY vyper_lib/ /app/vyper_lib/
RUN pip install -e /app/vyper_lib
```

Atau lebih sederhana: langsung copy file dan set PYTHONPATH.

---

## 3. Service 04a — `scanner-slither` (port 8014)

### App pattern
```python
"""Scanner Slither — standalone Slither static analysis service."""
from vyper_lib.models import ScanRequest, ScanResponse, Finding, ToolResult
from vyper_lib.solc_manager import SolcManager
from vyper_lib.slither_config import SlitherConfigBuilder
from vyper_lib.deps import DependencyResolver

# POST /scan — hanya jalankan Slither
# POST /install — install/update Slither
# GET /health
```

### Dockerfile
```dockerfile
FROM python:3.11-slim
# Install: Python base, slither-analyzer, solc-select
# NO foundry, NO echidna binary
```

### Image size: ~200MB (turunan dari ~730MB)

### requirements.txt
```
fastapi>=0.111.0
uvicorn[standard]>=0.30.1
httpx>=0.27.0
pydantic>=2.7.0
structlog>=24.2.0
python-multipart>=0.0.9
slither-analyzer>=0.10.0
solc-select>=1.0.0
```

---

## 4. Service 04b — `scanner-echidna` (port 8015)

### App pattern
```python
"""Scanner Echidna — standalone Echidna fuzzing service."""
from vyper_lib.models import ScanRequest, ScanResponse, Finding, ToolResult
from vyper_lib.solc_manager import SolcManager

# POST /scan — hanya jalankan Echidna fuzzing
# POST /install — install/update Echidna
# GET /health
```

### Dockerfile
```dockerfile
FROM python:3.11-slim
# Install: Python base, echidna binary (Go), solc-select
# NO slither, NO foundry
```

### Image size: ~180MB

### requirements.txt
```
fastapi>=0.111.0
uvicorn[standard]>=0.30.1
httpx>=0.27.0
pydantic>=2.7.0
structlog>=24.2.0
python-multipart>=0.0.9
solc-select>=1.0.0
```

---

## 5. Service 04c — `scanner-forge` (port 8016)

### App pattern
```python
"""Scanner Forge — standalone Foundry build verification service."""
from vyper_lib.models import ScanRequest, ForgeResult
from vyper_lib.solc_manager import SolcManager

# POST /build — verifikasi kompilasi dengan forge build
# POST /install — install/update Foundry
# GET /health
```

### Dockerfile
```dockerfile
FROM python:3.11-slim
# Install: Python base, foundry (forge, cast), solc-select
# NO slither, NO echidna
```

### Image size: ~550MB

### requirements.txt
```
fastapi>=0.111.0
uvicorn[standard]>=0.30.1
httpx>=0.27.0
pydantic>=2.7.0
structlog>=24.2.0
python-multipart>=0.0.9
solc-select>=1.0.0
```

---

## 6. Perubahan di `docker-compose.yml`

```yaml
services:
  04-scanner:                          # ← HAPUS atau jadi legacy wrapper
    # ... existing ...

  04a-scanner-slither:                 # ← BARU
    build:
      context: services/04a-scanner-slither
      dockerfile: Dockerfile
    ports: ["8014:8000"]
    volumes: [vyper_scanner_slither:/data/scanner]
    depends_on: [01-config]
    environment:
      - CONFIG_URL=http://01-config:8000

  04b-scanner-echidna:                 # ← BARU
    build:
      context: services/04b-scanner-echidna
      dockerfile: Dockerfile
    ports: ["8015:8000"]
    volumes: [vyper_scanner_echidna:/data/scanner]
    depends_on: [01-config]
    environment:
      - CONFIG_URL=http://01-config:8000

  04c-scanner-forge:                   # ← BARU
    build:
      context: services/04c-scanner-forge
      dockerfile: Dockerfile
    ports: ["8016:8000"]
    volumes: [vyper_scanner_forge:/data/scanner]
    depends_on: [01-config]
    environment:
      - CONFIG_URL=http://01-config:8000

  11-orchestrator:
    depends_on:
      - 04a-scanner-slither    # ← tambah
      - 04b-scanner-echidna    # ← tambah
      - 04c-scanner-forge      # ← tambah
      - 05-scanner-mythril     # ← sudah ada
    environment:
      - SCANNER_SLITHER_URL=http://04a-scanner-slither:8000   # ← BARU
      - SCANNER_ECHIDNA_URL=http://04b-scanner-echidna:8000   # ← BARU
      - SCANNER_FORGE_URL=http://04c-scanner-forge:8000       # ← BARU
      # SCANNER_URL tetap atau dihapus

volumes:
  vyper_scanner_slither:    # ← BARU
  vyper_scanner_echidna:    # ← BARU
  vyper_scanner_forge:      # ← BARU
```

---

## 7. Perubahan di `services/11-orchestrator/src/config.py`

```python
# Tambah:
scanner_slither_url: str = "http://04a-scanner-slither:8000"
scanner_echidna_url: str = "http://04b-scanner-echidna:8000"
scanner_forge_url: str = "http://04c-scanner-forge:8000"
# scanner_url bisa dihapus atau dipertahankan untuk backward compat
```

---

## 8. Perubahan di `services/11-orchestrator/src/pipeline.py`

### Opsi A — Fan-out dalam 1 step (minim perubahan state machine)

```python
async def _run_scan(self, record: AuditRecord) -> Dict[str, Any]:
    """Call ALL scanner services in parallel (fan-out)."""
    
    source_data = record.metadata.get("source_data") or {}
    sources = source_data.get("sources") or {}
    compiler = record.metadata.get("compiler_version") or "0.8.20"
    
    # Payload yang sama untuk semua scanner
    payload = {
        "chain": record.chain,
        "address": record.address,
        "sources": sources,
        "compiler": compiler,
    }
    
    # Fan-out ke 4 scanner secara paralel
    results = await asyncio.gather(
        self._call_scanner_slither(payload),
        self._call_scanner_echidna(payload),
        self._call_scanner_forge(payload),
        self._call_scanner_mythril(payload),
        return_exceptions=True,  # 1 gagal tidak menghentikan yang lain
    )
    
    # Aggregate semua findings
    all_findings = []
    tool_results = []
    forge_result = None
    
    for result in results:
        if isinstance(result, Exception):
            log.error("scan.tool_failed", error=str(result))
            continue
        data = result.get("data") or {}
        all_findings.extend(data.get("all_findings", []))
        tool_results.extend(data.get("tools", []))
        if data.get("forge"):
            forge_result = data.get("forge")
    
    record.metadata["scan_results"] = {
        "all_findings": all_findings,
        "tools": tool_results,
        "forge": forge_result,
    }
    
    return {"status": "ok", "total_findings": len(all_findings)}

async def _call_scanner_slither(self, payload: dict) -> dict:
    resp = await self.client.post(f"{config.scanner_slither_url}/scan", json=payload)
    resp.raise_for_status()
    return resp.json()

async def _call_scanner_echidna(self, payload: dict) -> dict:
    payload["contract_name"] = None  # echidna-specific
    resp = await self.client.post(f"{config.scanner_echidna_url}/scan", json=payload)
    resp.raise_for_status()
    return resp.json()

async def _call_scanner_forge(self, payload: dict) -> dict:
    resp = await self.client.post(f"{config.scanner_forge_url}/build", json=payload)
    resp.raise_for_status()
    return resp.json()

async def _call_scanner_mythril(self, payload: dict) -> dict:
    resp = await self.client.post(f"{config.mythril_url}/analyze", json=payload)
    resp.raise_for_status()
    return resp.json()
```

### Opsi B — Multiple pipeline steps (lebih granular)

```python
WORKFLOW = [
    (PipelineState.FETCHING_PROGRAM, "_fetch_program", ToolType.SOURCE),
    (PipelineState.FETCHING_SOURCE, "_fetch_source", ToolType.SOURCE),
    (PipelineState.SCAN_SLITHER, "_run_slither", ToolType.SCANNER),    # ← split
    (PipelineState.SCAN_ECHIDNA, "_run_echidna", ToolType.SCANNER),    # ← split
    (PipelineState.SCAN_FORGE, "_run_forge", ToolType.SCANNER),        # ← split
    (PipelineState.SCAN_MYTHRIL, "_run_mythril", ToolType.SCANNER),   # ← terpisah
    (PipelineState.AI_ANALYSIS, "_run_ai_analysis", ToolType.AI),
    (PipelineState.CLASSIFYING, "_classify_findings", ToolType.CLASSIFIER),
    (PipelineState.EXPLOITING, "_generate_exploit", ToolType.EXPLOIT),
    (PipelineState.REPORTING, "_generate_report", ToolType.REPORTER),
    (PipelineState.NOTIFYING, "_notify", None),
]
```

**Rekomendasi: Opsi A** — lebih sederhana, perubahan minimal, pipeline state machine tidak perlu diubah.

---

## 9. Urutan Implementasi

| Langkah | Apa | File | Estimasi |
|---------|-----|------|----------|
| 1 | Buat `vyper_lib/` package | `vyper_lib/__init__.py`, `models.py`, `solc_manager.py`, `deps.py`, `slither_config.py` | 30 menit |
| 2 | Buat service 04a (slither) | `services/04a-scanner-slither/app.py`, `src/slither.py`, `Dockerfile`, `requirements.txt` | 30 menit |
| 3 | Buat service 04b (echidna) | `services/04b-scanner-echidna/app.py`, `src/echidna.py`, `Dockerfile`, `requirements.txt` | 30 menit |
| 4 | Buat service 04c (forge) | `services/04c-scanner-forge/app.py`, `src/forge.py`, `Dockerfile`, `requirements.txt` | 30 menit |
| 5 | Update docker-compose.yml | Tambah 3 service baru, update depends_on | 15 menit |
| 6 | Update orchestrator config | `config.py` tambah URL baru | 5 menit |
| 7 | Update pipeline | `pipeline.py` → `_run_scan` jadi fan-out | 30 menit |
| 8 | Test | `docker-compose up`, jalankan test | 30 menit |
| 9 | Cleanup | Hapus service 04 lama (optional) | 15 menit |

**Total estimasi: ~3 jam**

---

## 10. Risiko & Mitigasi

| Risiko | Dampak | Mitigasi |
|--------|--------|----------|
| **Source code transfer** — tiap service terima source via HTTP, ada overhead | Latensi naik | Stay dengan 1 step SCANNING, fan-out paralel dalam 1 method |
| **SolcManager duplikasi** — tiap service install solc sendiri | Disk usage naik | Shared volume untuk cache solc (`vyper_solc_cache`) |
| **Backward compatibility** — service lain masih panggil `http://04-scanner:8000` | Service discovery broken | Pertahankan service 04 sebagai proxy/legacy wrapper, atau update semua referensi |
| **ResourceGovernor tidak optimal** — current governor hanya batasi "scanner" dan "ai" | Overload | Update ResourceGovernor untuk handle 4 tipe scanner |

---

## 11. Diagram End-State

```
                                ┌──────────────────────┐
                                │   Orchestrator (11)   │
                                │   _run_scan()         │
                                │   fan-out paralel     │
                                └──┬───┬───┬───┬───────┘
                                   │   │   │   │
              ┌────────────────────┘   │   │   └──────────────┐
              ▼                        ▼   ▼                  ▼
     ┌──────────────┐        ┌──────────────┐       ┌──────────────┐
     │ 04a-slither  │        │ 04b-echidna  │       │ 04c-forge    │
     │ port 8014    │        │ port 8015    │       │ port 8016    │
     │ Python       │        │ Python+Go    │       │ Rust (forge) │
     │ ~200MB       │        │ ~180MB       │       │ ~550MB       │
     └──────────────┘        └──────────────┘       └──────────────┘

                                   ┌──────────────┐
                                   │ 05-mythril   │
                                   │ port 8013    │
                                   │ Python       │
                                   │ (existing)   │
                                   └──────────────┘
```

---

## 12. Catatan Tambahan

### Mengapa tidak semua tool dipisah total?
- **Slither + Echidna** bisa digabung karena sama-sama Python-based dan sharing `SolcManager` langsung
- Tapi dipisah tetap lebih baik karena **fault isolation** dan **image size**

### Bagaimana dengan ResourceGovernor?
```python
# Current:
ToolType.SCANNER  # semua scanner dianggap sama
ToolType.AI       # AI analysis

# After: perlu dibedakan atau tetap 1 kategori
ToolType.SCANNER  # tetap 1 kategori untuk fairness
```
ResourceGovernor tetap bisa pake 1 kategori `SCANNER` dengan `max_concurrent_scans=4` untuk 4 service.

### Apakah service 04 lama dihapus?
**Sebaiknya dipertahankan** sebagai legacy wrapper untuk transisi, lalu dihapus setelah semua service lain migrate.
