# Intelligence Expansion Plan — 04b, 04c, 05 + Halmos

## Ringkasan

Menambahkan L2–L4 intelligence (classifier, scorer, fixer, fp_db, path_predictor, nlp) ke service 04b (Echidna), 04c (Forge), dan 05 (Mythril), serta membuat service baru 04d (Halmos).

---

## Bagian 1: Intelligence untuk 04b-scanner-echidna

### Karakteristik Service

- **Tool**: Echidna (fuzzer)
- **Input**: Solidity source + harness → fuzzing campaign
- **Output**: Property violations (`echidna_` functions failing), assertion failures, call sequences
- **Model**: `EchidnaRunner.run()` → `ToolResult` → `Finding[]`
- **Setiap Finding punya**: `title`, `severity="high"`, `test_function`, `failing_input`, `recommendation`

### Kebutuhan Intelijen

| Intelijen | Apakah Masuk Akal? | Approach |
|-----------|-------------------|----------|
| **Classifier** | ✅ Ya | Kategorikan failure berdasarkan pattern di `test_function` / `failing_input` (reentrancy, access control, arithmetic, flash loan, etc.) |
| **Scorer** | ✅ Ya | Scoring berdasarkan reproducibility, call sequence complexity, fund movement |
| **Fixer** | ✅ Ya | Template fix per jenis property violation (reentrancy guard, access control fix, dll) |
| **FP/DB** | ✅ Ya | Echidna bisa false positive (flaky tests) — feedback learning sangat berguna |
| **Path Predictor** | ⚠️ Parsial | Call sequence dari Echidna sudah merupakan exploit path — cukup format ulang |
| **NLP** | ✅ Ya | "what failed?", "show me reentrancy", "how to fix assertion?" |

### Arsitektur

```
services/04b-scanner-echidna/
├── app.py                          # +7 endpoint baru (sama seperti 04a)
├── src/
│   ├── echidna.py                  # Existing (tidak berubah)
│   └── intelligence/               # [BARU] — adaptasi dari 04a
│       ├── __init__.py
│       ├── classifier.py           # → EchidnaClassifier
│       │   ├── classify failure patterns (reentrancy, access, arithmetic)
│       │   ├── detector priority per failure type
│       │   └── severity override berdasarkan call sequence complexity
│       ├── scorer.py               # → EchidnaScorer
│       │   ├── reproducibility (berhasil reproduce? berapa kali?)
│       │   ├── call sequence depth
│       │   ├── fund movement (ETH/token terlibat?)
│       │   └── aggregated fuzzing health score
│       ├── fp_db.py                # → reuse FalsePositiveDB dari vyper_lib
│       ├── fixer.py                # → EchidnaFixer
│       │   ├── template per property type
│       │   └── call sequence → concrete fix guidance
│       ├── path_predictor.py       # → EchidnaPathFormatter
│       │   └── format call sequence jadi exploit narrative
│       └── nlp.py                  # → reuse / relai ke rule-based NLP
```

### Perbedaan Kunci dari 04a

| Aspek | 04a Slither | 04b Echidna |
|-------|-------------|-------------|
| **Classifier input** | Function signatures + imports | Test function names + failure patterns |
| **Severity** | critical / high / medium / low | `"high"` (default) atau dinaikkan |
| **Scoring factor** | Exploitability, business impact | Reproducibility, sequence complexity |
| **Fix templates** | Per detector (reentrancy-eth dll) | Per property type (reentrancy, access, dll) |
| **Path predictor** | Chain detectors → exploit | Format call sequence → exploit narrative |

### Endpoint Baru

| Method | Path | Fungsi |
|--------|------|--------|
| POST | `/classify` | Klasifikasi failure type + rekomendasi detektor |
| POST | `/score` | Skor fuzzing finding + health score |
| POST | `/fix` | Template fix per failure type |
| POST | `/exploit/paths` | Format call sequence chain |
| POST | `/ask` | Natural language query |
| POST | `/feedback` | Record FP/TP untuk fuzzing results |
| GET  | `/intel/stats` | Stats intelligence engine |

### Estiması: 2–3 jam

---

## Bagian 2: Intelligence untuk 04c-scanner-forge

### Karakteristik Service

- **Tool**: Foundry Forge (`forge build`)
- **Input**: Solidity source files
- **Output**: Compiler errors + warnings (bukan security findings)
- **Model**: `ForgeRunner.run()` → `ForgeResult` (success, errors[], warnings[], compiler_version)
- **Tidak ada Finding** — service ini verifikasi kompilasi, bukan deteksi vulnerability

### Kebutuhan Intelijen

| Intelijen | Apakah Masuk Akal? | Approach |
|-----------|-------------------|----------|
| **Classifier** | ✅ Ya | Klasifikasi error compiler (syntax error, type error, import error, visibility, dll) |
| **Scorer** | ✅ Ya | Blocking vs warning, severity berdasarkan error type |
| **Fixer** | ✅ Ya | Template fix per compiler error — ini sangat berguna untuk developer |
| **FP/DB** | ❌ Tidak | Compiler errors bersifat deterministic — tidak ada false positive |
| **Path Predictor** | ❌ Tidak | Compiler errors tidak membentuk chain exploit |
| **NLP** | ✅ Ya | "why did the build fail?", "fix import error" |

### Perbedaan Fundamental dari 04a

04c adalah **build tool**, bukan **security scanner**. Intelijen di sini lebih sebagai **developer assistance** daripada security analysis:

```
04a Slither:     "reentrancy-eth" → security finding
04c Forge:      "ParserError: expected ';'" → compilation error

Model: ForgeResult { success, errors[], warnings[] }
       → BUKAN Finding[] (tidak ada tool, severity, dll)
```

### Arsitektur

```
services/04c-scanner-forge/
├── app.py                    # +4 endpoint baru (classify, score, fix, ask)
├── src/
│   ├── forge.py              # Existing (tidak berubah)
│   └── intelligence/         # [BARU] — lightweight
│       ├── __init__.py
│       ├── compiler_classifier.py
│       │   ├── 30+ pattern regex untuk error Solidity
│       │   └── kategori: syntax, type, import, visibility, ABI, Yul, dll
│       ├── compiler_scorer.py
│       │   └── blocking vs warning + severity per error type
│       └── compiler_fixer.py
│           ├── template fix per error pattern
│           └── contoh: "expected ';'" → "add semicolon at line X"
```

### Penting: All Findings = Empty

Service 04c saat ini mengembalikan `all_findings=[]`. Setelah intelligence:
- `POST /score` akan score errors (bukan findings)
- `POST /fix` akan generate fix untuk compiler errors
- Pipeline tetap tidak memasukkan Forge errors sebagai security finding

### Estiması: 1.5 jam

---

## Bagian 3: Intelligence untuk 05-scanner-mythril

### Karakteristik Service

- **Tool**: Mythril (symbolic execution)
- **Input**: Solidity source files
- **Output**: `AnalyzerFinding[]` dengan `title`, `description`, `severity`, `swc_id`, `swc_title`, `function`, `address`
- **Model**: standalone `app.py` (tidak pakai struktur vyper_lib — port sendiri)
- **PENTING**: Service 05 punya **model sendiri** (`AnalyzerFinding`, `ApiResponse` lokal), tidak pakai `vyper_lib.models`

### Problem: Service 05 Tidak Bisa Import vyper_lib

Service 05 di-isolasi karena **dependency conflict** Mythril vs web3.py:

```
05-scanner-mythril/
├── app.py          # Pakai model sendiri (AnalyzerFinding, ApiResponse lokal)
├── Dockerfile      # Image dengan mythril-compatible deps
└── src/
    └── __init__.py # Hampa
```

Tidak bisa `from vyper_lib.models import Finding` karena konflik dependensi.

### Solusi Intelijen untuk Service 05

Ada **dua pendekatan**:

#### Opsi A: Intelijen di dalam 05 (standalone)
Buat intelligence engine internal (tidak tergantung vyper_lib).
- **Plus**: Fully isolated, cocok dengan arsitektur existing
- **Minus**: Duplikasi kode, maintenance overhead

#### Opsi B: Intelijen via 04a (relay)
05 hanya parse output Mythril → kirim ke 04a `/classify` + `/score` untuk enrichment.
- **Plus**: Zero duplikasi kode
- **Minus**: Tambah dependensi network (HTTP call ke 04a)

#### Opsi C: Vyper Lib Terpisah untuk Mythril
Buat `vyper_lib_mythril/` package khusus untuk service 05.
- **Plus**: Tidak ada konflik dependensi, reuse models
- **Minus**: Dua versi vyper_lib harus di-sync

### Rekomendasi: Opsi A

Karena service 05 sudah fully isolated dan independen, tambah intelligence langsung di dalamnya:

```
services/05-scanner-mythril/
├── app.py                    # +7 endpoint (sama seperti 04a)
├── src/
│   ├── __init__.py
│   └── intelligence/         # [BARU] — standalone (tidak import vyper_lib)
│       ├── __init__.py
│       ├── classifier.py     # → MythrilClassifier
│       │   ├── berdasarkan SWC ID (Mythril sudah kasih ini)
│       │   └── + function signature analysis (optional)
│       ├── scorer.py         # → MythrilScorer
│       │   ├── severity override berdasarkan SWC + function context
│       │   ├── exploitability path dari Mythril's call sequence
│       │   └── business impact per SWC category
│       ├── fp_db.py          # → FP/TP DB (inline, pakai json file)
│       ├── fixer.py          # → FixTemplates per SWC ID
│       ├── path_predictor.py # → Chain SWC findings
│       └── nlp.py            # → Rule-based NLP
```

### Perbedaan dari 04a

| Aspek | 04a Slither | 05 Mythril |
|-------|-------------|------------|
| **Input classifier** | Function signatures + imports | SWC ID sudah tersedia |
| **Severity** | Dari Slither (critical–info) | Dari Mythril (High/Medium/Low) |
| **Fix templates** | Per detector name | Per SWC ID (lebih standard) |
| **FP/DB storage** | `/data/scanner-slither/fp_db.json` | `/data/scanner-mythril/fp_db.json` |
| **Framework** | FastAPI + vyper_lib | FastAPI + models lokal |

### Estiması: 3–4 jam

---

## Bagian 4: Halmos Integration

### Apa Itu Halmos?

```
Halmos = Symbolic testing tool untuk EVM smart contracts.
Dibuat oleh a16z crypto.
Cara kerja: Eksekusi Foundry test secara simbolik (pakai z3 SMT solver).
```

### Comparison with Existing Tools

| Aspek | Echidna (04b) | Mythril (05) | Halmos (04d) |
|-------|--------------|--------------|--------------|
| **Metode** | Fuzzing (random) | Symbolic execution (bytecode) | Symbolic execution (Foundry test) |
| **Input** | Solidity + harness | Solidity source | Foundry test (.t.sol) |
| **Output** | Property violation | SWC findings | Assertion failure + counter-example |
| **Bahasa** | Haskell (binary) | Python | Python |
| **Dependensi** | Standalone binary | Python + solc | Python + Foundry |
| **SWC Coverage** | Tidak langsung | Langsung (SWC ID) | Tidak langsung (via assertion) |
| **Kecepatan** | Cepat (ms per run) | Lambat (detik–menit) | Sedang (detik per test) |

### Service Baru: 04d-scanner-halmos

#### Posisi dalam Arsitektur

```
04d-scanner-halmos (port 8017)
  ├─ POST /scan        → halmos --json --output /tmp/output.json
  ├─ POST /build       → forge build (pra-kondisi)
  ├─ GET  /health      → cek halmos + foundry
  └─ + Intelligence endpoints (classifier, score, fix, ask)
```

#### Docker

```dockerfile
FROM python:3.12-slim

# Install Foundry
RUN curl -fsSL https://foundry.paradigm.xyz | bash
RUN /root/.foundry/bin/foundryup

# Install Halmos
RUN pip install halmos

# Copy service
COPY . .
```

Atau bisa pakai Docker image official: `ghcr.io/a16z/halmos:latest`

#### Cara Kerja Halmos

```
1. User upload source code (Foundry project)
2. Service jalankan: forge build (compile dulu)
3. Service jalankan: halmos --json --function test_*
4. Parse JSON output:
   - Pass: test_name, time
   - Fail: test_name, counter_example (calldata, return_data)
   - Error: test_name, error_message
5. Convert ke Finding[]:
   - title: "Halmos assertion failed: {test_name}"
   - severity: "high" (jika fail) / "info" (jika pass)
   - description: counter_example details
```

#### Halmos Output JSON Format

Halmos v0.3.x menghasilkan JSON seperti ini:

```json
{
  "tests": [
    {
      "name": "test_transfer",
      "status": "fail",
      "num_models": 1,
      "models": [
        {
          "name": "model_0",
          "calldata": "0x..."
        }
      ],
      "time": 1.234
    }
  ],
  "statistics": {
    "total_tests": 10,
    "num_passed": 8,
    "num_failed": 2,
    "total_time": 12.34
  }
}
```

#### Intelligence untuk Halmos

| Intelijen | Approach |
|-----------|----------|
| **Classifier** | Klasifikasi failure berdasarkan error message pattern + function name |
| **Scorer** | Scoring berdasarkan: test complexity, calldata length, time to find counter-example |
| **Fixer** | Template fix: "your function {name} failed assertion — check edge case at {counter_example}" |
| **FP/DB** | Track flaky symbolic tests (jarang, tapi bisa terjadi) |
| **NLP** | "which tests failed?", "show counter-examples" |
| **Path predictor** | Counter-example calldata sudah merupakan exploit path |

### Estiması: 4–5 jam (service baru + intelligence)

---

## Tabel Ringkasan Semua Perubahan

| Service | Tool | Tipe | Intelijen | Endpoint Baru | Estimasi | Status |
|---------|------|------|-----------|---------------|----------|--------|
| **04a** | Slither | Static analysis | classifier, scorer, fixer, fp_db, path, nlp | +7 | — | ✅ Sebelumnya |
| **04b** | Echidna | Fuzzer | classifier, scorer, fixer, fp_db, path, nlp | +7 | 2–3 jam | ✅ |
| **04c** | Forge | Compiler | compiler_classifier, compiler_scorer, compiler_fixer | +5 | 1.5 jam | ✅ |
| **05** | Mythril | Symbolic | classifier, scorer, fixer, path, nlp | +7 | 3–4 jam | ✅ |
| **04d** [BARU] | Halmos | Symbolic test | classifier, scorer, fixer, path, nlp + scan | +7 | 4–5 jam | ✅ |

### Total Realisasi: ~11 jam (semua milestone selesai)

---

## Deliverables per Milestone

### Milestone 1: 04b Intelligence (2–3 jam) ✅
- [x] `src/intelligence/classifier.py` — failure pattern → contract type
- [x] `src/intelligence/scorer.py` — reproducibility + sequence scoring
- [x] `src/intelligence/fp_db.py` — reuse FalsePositiveDB
- [x] `src/intelligence/fixer.py` — template per property type
- [x] `src/intelligence/path_predictor.py` — call sequence formatter
- [x] `src/intelligence/nlp.py` — rule-based NLP
- [x] Update `app.py` — +7 endpoint
- [x] Update `docker-compose.yml` — volume `/data/scanner-echidna`

### Milestone 2: 05 Intelligence (3–4 jam) ✅
- [x] `src/intelligence/classifier.py` — SWC-based classification
- [x] `src/intelligence/scorer.py` — SWC + function context scoring
- [x] `src/intelligence/fixer.py` — template per SWC ID
- [x] `src/intelligence/path_predictor.py` — chain SWC findings
- [x] `src/intelligence/nlp.py` — rule-based NLP
- [x] Update `app.py` — +7 endpoint

### Milestone 3: 04c Intelligence (1.5 jam) ✅
- [x] `src/intelligence/compiler_classifier.py` — 30+ error patterns
- [x] `src/intelligence/compiler_scorer.py` — blocking vs warning
- [x] `src/intelligence/compiler_fixer.py` — template fix per error
- [x] `src/intelligence/compiler_nlp.py` — rule-based NLP
- [x] Update `app.py` — +5 endpoint

### Milestone 4: Halmos Service (4–5 jam) ✅
- [x] `04d-scanner-halmos/app.py` — FastAPI app
- [x] `04d-scanner-halmos/src/halmos.py` — HalmosRunner
- [x] `04d-scanner-halmos/src/intelligence/` — full package
- [x] `04d-scanner-halmos/Dockerfile` — Python 3.12 + Foundry + Halmos
- [x] `04d-scanner-halmos/requirements.txt`
- [x] Update `docker-compose.yml` — +1 service + volume
- [x] Update `services/11-orchestrator/src/config.py` — tambah `scanner_halmos_url`
- [x] Update `services/11-orchestrator/src/pipeline.py` — tambah `_call_scanner_halmos`
- [x] Update `tests/conftest.py` — fixture `scanner_halmos_url`
- [x] Update `tests/test_services.py` — test health check
