# Intelligence Engine API Reference

> Dokumentasi endpoint intelligence untuk service 04a (Slither), 04b (Echidna), 04c (Forge), 05 (Mythril), dan 04d (Halmos).

Setiap service FastAPI juga menyediakan OpenAPI docs otomatis di `/docs` (Swagger UI) dan `/redoc` (ReDoc).

---

## Daftar Service

| Port | Service | Tool | Intel Engine |
|------|---------|------|-------------|
| 8014 | 04a-scanner-slither | Slither static analysis | Full L2-L4 |
| 8015 | 04b-scanner-echidna | Echidna fuzzing | Full L2-L4 |
| 8016 | 04c-scanner-forge | Forge build compiler | L2 + L4 (lightweight) |
| 8013 | 05-scanner-mythril | Mythril symbolic exec | Full L2-L4 (standalone) |
| 8017 | 04d-scanner-halmos | Halmos symbolic test | Full L2-L4 |

---

## Common Intelligence Endpoints

### `POST /intel/classify`
Klasifikasi finding/error ke dalam kategori.

**Request** (04a/04b/05/04d — security findings):
```json
{
  "findings": [
    {
      "title": "Reentrancy in withdraw()",
      "description": "External call before state update...",
      "severity": "high",
      "swc_id": "SWC-107"
    }
  ]
}
```

**Request** (04c — compiler errors):
```json
{
  "errors": [
    "Expected ';' at line 42",
    "Type uint256 is not implicitly convertible to address"
  ]
}
```

**Response**:
```json
{
  "ok": true,
  "data": {
    "enriched_findings": [
      {
        "title": "Reentrancy in withdraw()",
        "category": "reentrancy",
        "severity": "critical",
        "confidence": 0.95,
        "label": "Reentrancy"
      }
    ],
    "categories": { "reentrancy": 1 },
    "severity_counts": { "critical": 1 },
    "total": 1
  }
}
```

---

### `POST /intel/score`
Scoring findings/errors berdasarkan severity, category weight, dan konteks.

**Request**:
```json
{
  "findings": [
    { "title": "...", "severity": "high", "swc_id": "SWC-107", "function": "withdraw" }
  ]
}
```

**Response**:
```json
{
  "ok": true,
  "data": {
    "scores": [
      {
        "title": "Reentrancy in withdraw()",
        "adjusted_score": 97.5,
        "risk_label": "critical",
        "priority": 1,
        "recommendation": "CRITICAL: reentrancy — immediate action required."
      }
    ],
    "aggregate": {
      "overall_score": 97.5,
      "overall_label": "critical",
      "critical_count": 1,
      "high_count": 0
    }
  }
}
```

---

### `POST /intel/fix`
Generate fix suggestion templates.

**Request**:
```json
{
  "findings": [
    { "title": "...", "swc_id": "SWC-107", "severity": "critical" }
  ]
}
```

**Response**:
```json
{
  "ok": true,
  "data": {
    "fixes": {
      "SWC-107": [
        {
          "swc_id": "SWC-107",
          "title": "Reentrancy",
          "description": "External call before state update.",
          "before": "function withdraw(uint256 a) external { ... }",
          "after": "// Checks-Effects-Interactions pattern\nfunction withdraw(uint256 a) external { ... }",
          "solidity_example": "...",
          "confidence": 0.95
        }
      ]
    },
    "template_stats": { "known_templates": 6, "swc_ids": ["SWC-101", "SWC-104", ...] }
  }
}
```

---

### `POST /intel/paths`
Prediksi exploit chain dari kombinasi findings. Tersedia di 04a, 04b, 05, 04d.

**Request**:
```json
{
  "findings": [
    { "swc_id": "SWC-112", "category": "access_control" },
    { "swc_id": "SWC-107", "category": "reentrancy" }
  ]
}
```

**Response**:
```json
{
  "ok": true,
  "data": {
    "chains": [
      {
        "name": "contract_takeover",
        "severity": "critical",
        "confidence": 0.9,
        "steps": [
          "Attacker provides malicious implementation address",
          "delegatecall executes arbitrary code in proxy context",
          "Full contract takeover"
        ],
        "impact": "Complete contract compromise — all funds lost"
      }
    ],
    "summary": {
      "total_chains": 1,
      "worst_severity": "critical",
      "top_concern": {
        "name": "contract_takeover",
        "impact": "Complete contract compromise — all funds lost",
        "confidence": 0.9
      }
    }
  }
}
```

---

### `POST /intel/ask`
Natural language query tentang hasil analisis. Tersedia di semua service.

**Request**:
```json
{
  "query": "show me critical issues",
  "findings": [
    { "title": "...", "severity": "critical", "category": "reentrancy" },
    { "title": "...", "severity": "low", "category": "warning" }
  ]
}
```

**Response**:
```json
{
  "ok": true,
  "data": {
    "query": "show me critical issues",
    "intent": "critical",
    "answer": "Found **1** critical/high issues:\n  1. Reentrancy... (critical)",
    "context": { "total_findings": 2 },
    "follow_up_questions": ["How to fix?", "Exploit chains"]
  }
}
```

---

### `GET /intel/stats`
Statistik intelligence engine.

**Response**:
```json
{
  "ok": true,
  "data": {
    "classifier": {
      "categories": ["arithmetic", "reentrancy", "access_control", ...],
      "swc_count": 29
    },
    "scorer": {
      "factors": ["severity_base", "impact_boost", "fn_boost"]
    },
    "fixer": {
      "known_templates": 6,
      "swc_ids": ["SWC-101", "SWC-104", "SWC-105", "SWC-107", "SWC-112", "SWC-115"]
    },
    "chain_predictor": {
      "chains_defined": 5,
      "chain_names": ["contract_takeover", "fund_drain", ...]
    }
  }
}
```

---

## Service-Specific Endpoints

### 04a-scanner-slither (port 8014) + classifier `GET /intel/classify/detectors`

```json
// GET /intel/classify/detectors
{
  "ok": true,
  "data": {
    "detectors": {
      "reentrancy-eth": { "category": "reentrancy", "severity": "high", "weight": 1.0 },
      "unchecked-lowcall": { "category": "low_level", "severity": "high", "weight": 0.8 }
    },
    "total": 47
  }
}
```

### 04a-slither `POST /feedback`
Record false positive / true positive untuk pembelajaran.

```json
{
  "finding_title": "reentrancy-eth",
  "user_label": "false_positive",
  "notes": "Protected by reentrancy guard"
}
```

### 04c-scanner-forge (port 8016) — error-specific endpoints

**Compiler service — input adalah list of strings, bukan findings:**

| Method | Path | Deskripsi |
|--------|------|-----------|
| POST | `/intel/classify` | Classify raw error messages |
| GET  | `/intel/classify/categories` | List error categories |
| POST | `/intel/score` | Score compiled errors |
| POST | `/intel/fix` | Fix templates per error pattern |
| POST | `/intel/ask` | "why did the build fail?" |

### 05-scanner-mythril (port 8013) — standalone classifier info

| Method | Path | Deskripsi |
|--------|------|-----------|
| GET  | `/intel/classify/swc` | Full SWC registry with severity override |

---

## Scoring Factors per Service

| Service | Faktor Scoring |
|---------|---------------|
| **04a Slither** | exploitability, business impact per detector, function context |
| **04b Echidna** | reproducibility, sequence complexity, fund movement, category weight |
| **04c Forge** | blocking (80pt base) vs warning (30pt base), category boost (1.3 syntax, 0.5 warning) |
| **05 Mythril** | severity_base (90 critical–5 info), impact_boost (1.3 high-impact), fn_boost (1.5 high-risk fn) |
| **04d Halmos** | severity_base, category_weight (1.4 reentrancy/access), calldata complexity boost |

---

## Enrichment Otomatis

Beberapa service melakukan intelligence enrichment otomatis saat scan:

| Service | Endpoint | Enrichment |
|---------|----------|------------|
| 04a Slither | `POST /scan` | Findings di-enrich dengan `category`, `risk_score`, `risk_label`, `priority` via metadata |
| 04b Echidna | `POST /scan` | Findings di-enrich dengan `failure_category`, `failure_label`, `failure_severity`, `failure_confidence`, `risk_score`, `risk_label`, `priority` |
| 05 Mythril | `POST /analyze` | Findings di-enrich dengan `swc_id` override, `metadata.category`, `metadata.risk_score`, `metadata.risk_label`, `metadata.priority` |
| 04d Halmos | `POST /scan` | Findings di-enrich dengan `category`, `confidence` via HalmosFinding object |

---

## Pipeline Orchestrator Integration

Service 11-orchestrator memanggil semua scanner paralel via `asyncio.gather`:

```
Orchestrator
  ├─ 04a /scan    → all_findings[]
  ├─ 04b /scan    → all_findings[]
  ├─ 04c /build   → forge result (no findings)
  ├─ 05  /analyze → findings[] → all_findings[]
  └─ 04d /scan    → findings[] via Halmos result
```

Intelligence enrichment terjadi **di masing-masing service** — orchestrator hanya mengagregasi hasil.

### AI Integration (service 06-ai)

Pipeline juga memanggil 06-ai `/analyze` untuk AI verdict (jika `use_ai=True`):
- Setiap finding di-merge dengan field `ai_verdict`, `ai_confidence`, `ai_severity`, `ai_reasoning`, `suggested_fix`
- Graceful skip jika 06-ai unreachable atau `use_ai=False`

---

## Catatan Penting

1. **05 Mythril standalone** — Tidak bisa import vyper_lib karena dependency conflict. Model dan response format milik sendiri.
2. **04c Forge** — Bukan security scanner. Output berupa compiler errors, bukan security findings. Semua `all_findings=[]`.
3. **04d Halmos** — Membutuhkan Foundry terinstall di container. Menggunakan `halmos --json` untuk output terstruktur.
4. **Semua service FastAPI** — Menyediakan `/docs` (Swagger) dan `/redoc` (ReDoc) untuk eksplorasi interaktif.
