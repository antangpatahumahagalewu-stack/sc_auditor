# Vyper Auditor — Roadmap & Implementation Plan

> Dibuat: 2026-05-18 | 5 Prioritas, ~8 Minggu
> Status: 15 services (88% maturity), pipeline belum terintegrasi end-to-end

---

## Ringkasan Eksekutif

Vyper punya 15 service yang sudah diimplementasi (scanner, AI, exploit, classifier, reporter, notifier, dll) tapi belum pernah diuji **bekerja bersama sebagai pipeline**. Prioritas utama: sambungkan semua service dalam satu flow end-to-end. Setelah itu: CLI, formal verification (Halmos), GitHub Actions, dan custom detectors.

---

## Prioritas 1: End-to-End Pipeline ✓ Wajib dilakukan duluan

### Kenapa
15 service yang jalan sendiri-sendiri = 0 value. Pipeline terintegrasi = **product**.

### Sasaran
Semua 8 pipeline stages berhasil dari orchestrator:
```
PENDING → FETCHING_PROGRAM → FETCHING_SOURCE → SCANNING → AI_ANALYSIS
→ CLASSIFYING → (EXPLOITING) → REPORTING → NOTIFYING → COMPLETED
```

### Task Breakdown

| # | Task | Service | Files | Output |
|---|------|---------|-------|--------|
| E1 | Docker compose up & healthcheck | All | `docker-compose.yml` | 15/15 healthy |
| E2 | Fix scanner ← orchestrator data contract | scanner | `src/models.py` | Align `ScanRequest` with `pipeline._run_scan` payload |
| E3 | Test Config CRUD | config | — | `GET /config/`, `PUT /config/test` |
| E4 | Test Immunefi sync | immunefi | — | `POST /sync`, `GET /programs` |
| E5 | Test Source fetch (mock) | source | — | `POST /fetch` with known contract |
| E6 | Test AI analyze | ai | — | `POST /analyze` with mock findings |
| E7 | Test Classifier classify | classifier | — | `POST /classify` with AI output |
| E8 | Test Reporter report | reporter | — | `POST /report` with classified findings |
| E9 | Test Notifier notify | notifier | — | `POST /notify` (skip actual send) |
| E10 | E2E test: orchestrator → all | orchestrator | `test/e2e_test.py` | Full pipeline success |
| E11 | Fix integration bugs | varies | varies | All steps pass |
| E12 | Build E2E test suite | — | `test/test_pipeline.py` | CI-ready test |

### Dependencies
```
E1 → E2 → E3+E4+E5 (parallel) → E6 → E7 → E8 → E9 → E10 → E11 → E12
```

### Risiko
- Data contract mismatch antara services (format finding berbeda-beda)
- Service URL tidak reachable dari orchestrator container
- Immunefi/Source butuh API key eksternal

---

## Prioritas 2: Vyper CLI Tool

### Kenapa
Tanpa CLI, pipeline cuma bisa diakses via API. CLI adalah **pintu gerbang** ke CI/CD.

### Sasaran
```
# Pipeline lengkap
vyper audit 0xdead... --chain ethereum --report full

# Quick scan (hanya scanner)
vyper scan contract.sol --tools slither,mythril

# Generate PoC
vyper exploit 0xdead... --attack reentrancy

# Check status
vyper status <audit-id>
vyper dashboard         # Buka browser
```

### Task Breakdown

| # | Task | Files | Output |
|---|------|-------|--------|
| C1 | Docker integration: auto up/down | `vyper/cmd/docker.py` | `vyper up`, `vyper down` |
| C2 | Core: audit command | `vyper/cmd/audit.py` | `vyper audit <address>` |
| C3 | Core: scan command | `vyper/cmd/scan.py` | `vyper scan <file>` |
| C4 | Core: exploit command | `vyper/cmd/exploit.py` | `vyper exploit <id>` |
| C5 | Core: status command | `vyper/cmd/status.py` | `vyper status <id>` |
| C6 | Dashboard shortcut | `vyper/cmd/dashboard.py` | Open browser |
| C7 | Output formatters | `vyper/output.py` | JSON, table, color |
| C8 | Config file | `vyper/config.py` | `~/.vyper/config.yml` |
| C9 | Installer | `install.sh` / `pip install` | PyPI package |
| C10 | README + docs | `README.md` | Usage docs |

### Dependencies
```
C1 → C2+C3+C4+C5+C6 (parallel) → C7+C8 (parallel) → C9 → C10
```

### Teknologi
- Python `click` atau `typer` untuk CLI
- `httpx` untuk API calls
- `rich` untuk table/color output
- PyPI publish via `poetry` / `flit`

---

## Prioritas 3: Halmos Formal Verification

### Kenapa
Slither + Mythril + Echidna = standard. **Halmos** = symbolic execution yang bisa buktikan invariants secara matematis. Ini **pembeda** dari auditor tools lain.

### Sasaran
```
POST /scan + tools: ["halmos"]
→ HalmosRunner meng-compile + symbolic-execute kontrak
→ Temukan assertion violations & counterexamples
→ Findings terintegrasi dengan pipeline yang ada
```

### Task Breakdown

| # | Task | Files | Output |
|---|------|-------|--------|
| H1 | Tambah Halmos ke scanner Dockerfile | `services/04-scanner/Dockerfile` | `pip install halmos` |
| H2 | HalmosRunner module | `services/04-scanner/src/halmos.py` | `run()` → `list[Finding]` |
| H3 | Integrasi ke scanner app.py | `services/04-scanner/app.py` | Tool "halmos" di POST /scan |
| H4 | Parse hasil symbolic execution | `services/04-scanner/src/halmos.py` | Counterexample → Finding |
| H5 | Integration test | `tests/test_halmos.py` | Found invariant violation |
| H6 | Dokumentasi | — | Halmos usage guide |

### Dependencies
```
H1 → H2 → H3+H4 (parallel) → H5 → H6
```

### Risiko
- Halmos butuh Python 3.10+ (scanner pake 3.11 ✅)
- Halmos heavyweight — lama untuk kontrak besar
- Tidak semua kontrak compatible (butuh Foundry test structure)

---

## Prioritas 4: GitHub Actions Integration

### Kenapa
**Killer feature** buat Web3 dev teams: auto-audit tiap PR.

### Sasaran
```yaml
# .github/workflows/vyper-audit.yml
name: Vyper Audit
on: [pull_request]
jobs:
  audit:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: vyper-audit/action@v1
        with:
          api-key: ${{ secrets.VYPER_API_KEY }}
          tools: slither,echidna,halmos
          mode: pr-comment
```

### Task Breakdown

| # | Task | Files | Output |
|---|------|-------|--------|
| G1 | action.yml | `action/action.yml` | GitHub Action definition |
| G2 | Docker-based action runner | `action/Dockerfile` | Container with vyper CLI |
| G3 | Entrypoint script | `action/entrypoint.sh` | Parse inputs, call vyper |
| G4 | PR comment posting | `action/post_comment.py` | GitHub API comment |
| G5 | Annotation support | `action/annotations.py` | Inline code annotations |
| G6 | Documentation + example | `action/README.md` | Usage examples |
| G7 | Publish to marketplace | — | GitHub Marketplace listing |

### Dependencies
```
G1 → G2 → G3+G4+G5 (parallel) → G6 → G7
```

### Risiko
- Vyper CLI harus selesai duluan
- Docker image perlu publish ke GHCR

---

## Prioritas 5: Custom Slither Detectors

### Kenapa
Slither detector bawaan terbatas. Custom detectors bikin platform **extensible**.

### Sasaran
```
POST /scan + detectors: ["my_custom_detector.py"]
→ Load detector dari user upload
→ Apply ke kontrak
→ Findings dari custom detector
```

### Task Breakdown

| # | Task | Files | Output |
|---|------|-------|--------|
| D1 | Detector loader system | `services/04-scanner/src/detector_loader.py` | Load `.py` detectors dynamically |
| D2 | Detector registry API | `services/04-scanner/app.py` | `GET /detectors`, `POST /detectors` |
| D3 | Example detectors | `services/04-scanner/detectors/reentrancy_detailed.py` | 3 example detectors |
| D4 | Validation & sandboxing | `services/04-scanner/src/detector_loader.py` | Safe exec, timeout |
| D5 | Integration with scanner | `services/04-scanner/src/slither.py` | Pass custom detectors |
| D6 | Documentation | — | How to write detectors |

### Dependencies
```
D1 → D2+D3 (parallel) → D4 → D5 → D6
```

### Risiko
- Slither API berubah antar versi
- User-submitted code = security risk

---

## Gantt Chart

```
Minggu:    1    2    3    4    5    6    7    8
E2E:       ████████░░░░░░░░░░░░░░░░░░░░░░░░░░
CLI:       ░░░░░░░░████████░░░░░░░░░░░░░░░░░░
Halmos:    ░░░░░░░░░░░░░░░░████████░░░░░░░░░░
GitHub:    ░░░░░░░░░░░░░░░░░░░░░░░░████░░░░░░
Detectors: ░░░░░░░░░░░░░░░░░░░░░░░░░░░░████░░
```

## Resource Estimates

| Prioritas | File Baru | File Diubah | Total Baris |
|-----------|-----------|-------------|-------------|
| E2E Pipeline | 3-5 | 15-20 | ~800 |
| Vyper CLI | 15-20 | 0 | ~3,000 |
| Halmos | 2-3 | 2-3 | ~600 |
| GitHub Actions | 5-7 | 0 | ~400 |
| Custom Detectors | 5-8 | 3-4 | ~1,000 |

## Quality Gate

Setelah SETIAP prioritas selesai → review:
1. **Correctness**: Semua test passing
2. **Performance**: Response dalam batas wajar
3. **Security**: Input validation, timeouts
4. **Maintainability**: DRY, type hints, docstrings
5. **Completeness**: Semua AC terpenuhi
6. **Alignment**: Sesuai VYPER.md & arsitektur
