# VYPER Dashboard — Localhost Web UI

> **Tampilan**: Via browser di `http://localhost:3000`
> **Stack**: FastAPI + Jinja2 + CSS (Tailwind CDN) + vanilla JS
> **Data**: Semua dari `~/.vyper/*.json` — readonly, no write

---

## 1. Layout Global

### Route Map

| Route | Page | Method | Data Source |
|-------|------|--------|-------------|
| `/` | Dashboard overview | GET | `metrics.json`, all findings |
| `/programs` | Program list | GET | `immunefi/programs.json` |
| `/programs/{slug}` | Program detail | GET | `immunefi/programs/{slug}.json` |
| `/audits` | Audit history | GET | Scan `audits/` directory |
| `/audits/{id}` | Audit detail | GET | `audits/{id}/findings.json` |
| `/audits/{id}/report` | Immunefi report | GET | → HTML render |
| `/audits/{id}/report/full` | Full report | GET | → HTML render |
| `/submissions` | Submission tracker | GET | `submissions.json` |
| `/metrics` | Platform metrics | GET | `metrics.json` |
| `/settings` | Config viewer | GET | `config.json` |
| `/api/metrics` | Metrics raw JSON | GET | JSON response |
| `/api/events` | SSE stream | GET | Live events |
| `/api/feedback` | Submit feedback | POST | Write to learning/ |

```
┌─────────────────────────────────────────────────────────────┐
│  HEADER                                                     │
│  ┌──────┐  VYPER          [Programs] [Audits] [Metrics]    │
│  │ logo │  Bug Hunter     [Settings]           status: ✅  │
│  └──────┘                                                    │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│  ┌─SIDEBAR──────────────┐  ┌─MAIN CONTENT───────────────┐  │
│  │                      │  │                             │  │
│  │  📊 Dashboard        │  │  (Dynamic per page)         │  │
│  │  📋 Programs         │  │                             │  │
│  │  🔍 Audits           │  │                             │  │
│  │  💰 Submissions      │  │                             │  │
│  │  📈 Metrics          │  │                             │  │
│  │  🔄 Updates          │  │                             │  │
│  │  💾 Backups          │  │                             │  │
│  │  ⚙️ Settings         │  │                             │  │
│  │                      │  │                             │  │
│  │  ─────────────       │  │                             │  │
│  │  Last Sync: 2h ago   │  │                             │  │
│  │  Total Audits: 47    │  │                             │  │
│  │  Docker: ✅ Running   │  │                             │  │
│  └──────────────────────┘  └─────────────────────────────┘  │
│                                                             │
├─────────────────────────────────────────────────────────────┤
│  FOOTER — Vyper v0.1.0 — Local — ~/.vyper/ — 5.2 GB       │
└─────────────────────────────────────────────────────────────┘
```

**File structure untuk UI:**

```
vyper/web/
├── app.py                    # FastAPI app (uvicorn)
├── routes/
│   ├── __init__.py
│   ├── dashboard.py          # GET /
│   ├── programs.py           # GET /programs, /programs/{slug}
│   ├── audits.py             # GET /audits, /audits/{id}
│   ├── reports.py            # GET /audits/{id}/report
│   └── metrics.py            # GET /metrics
├── templates/
│   ├── base.html             # Layout utama (header + sidebar)
│   ├── dashboard.html        # Overview cards + recent
│   ├── programs.html         # Program list
│   ├── program_detail.html   # Single program
│   ├── audits.html           # Audit history list
│   ├── audit_detail.html     # Finding detail + exploit
│   ├── report.html           # Immunefi report view
│   ├── report_full.html      # Full internal report
│   ├── metrics.html          # Charts + confusion matrix
│   └── settings.html         # Config editor
└── static/
    └── style.css             # Custom styles
```

---

## 2. Route Map

| Route | Page | Method | Data Source |
|-------|------|--------|-------------|
| `/` | Dashboard overview | GET | `metrics.json`, recent audits |
| `/programs` | Program list | GET | `immunefi/programs.json` |
| `/programs/{slug}` | Program detail | GET | `immunefi/programs/{slug}.json` |
| `/audits` | Audit history | GET | Scan `audits/` directory |
| `/audits/{id}` | Audit detail | GET | `audits/{id}/findings.json` |
| `/audits/{id}/report` | Immunefi report | GET | `audits/{id}/reports/immunefi.md` → HTML |
| `/audits/{id}/report/full` | Full report | GET | `audits/{id}/reports/full.md` → HTML |
| `/metrics` | Platform metrics | GET | `metrics.json` |
| `/settings` | Config | GET | `config.json` |
| `/api/programs` | Programs JSON | GET | Raw JSON data |
| `/api/audits` | Audits JSON | GET | Raw JSON data |
| `/api/metrics` | Metrics JSON | GET | Raw JSON data |

---

## 3. Design System

### Warna

```
🎨 PALETTE:
═══════════════════════════════════════════════════════════

  Background:  #0a0a0f  (dark) / #f8f9fa (light) 
  Surface:     #14141f  (dark) / #ffffff (light)
  Border:      #2a2a3a  (dark) / #e2e8f0 (light)
  
  Accent:      #a855f7  (purple-500)  → logo, highlights
  Success:     #22c55e  (green-500)   → TP, exploit OK
  Warning:     #eab308  (yellow-500)  → TN, pending
  Danger:      #ef4444  (red-500)     → FN, critical bugs
  Info:        #3b82f6  (blue-500)    → FP, info messages
  
  Text:        #e2e8f0  (dark) / #1e293b (light)
  Muted:       #64748b  (slate-500)
```

### CSS Framework

Pakai **Tailwind CDN** (no build step — satu baris di HTML):

```html
<script src="https://cdn.tailwindcss.com"></script>
<script>
tailwind.config = {
  darkMode: 'class',
  theme: {
    extend: {
      colors: {
        vyper: { DEFAULT: '#a855f7', dark: '#7c3aed' }
      }
    }
  }
}
</script>
```

Dark/light mode toggle via `localStorage` + class `dark` di `<html>`.

---

## 4. Halaman Dashboard `/` — SEMUA ADA DI SINI

Dashboard adalah **halaman utama**. Isinya: stat cards + list semua findings dari semua audit + expandable detail untuk tiap finding.

### Layout

```
┌──────────────────────────────────────────────────────────────────┐
│  📊 DASHBOARD                                           [dark]  │
│                                                                    │
│  ┌────────┐  ┌────────┐  ┌────────┐  ┌────────┐  ┌────────┐    │
│  │ ✅ TP  │  │ ❌ FP  │  │ ✅ TN  │  │ ⚠️ FN  │  │ 🏆 SKOR│    │
│  │   89   │  │   45   │  │  156   │  │   22   │  │  7.2   │    │
│  │ semua  │  │ semua  │  │ semua  │  │ 🔴 ↑5  │  │  B     │    │
│  └────────┘  └────────┘  └────────┘  └────────┘  └────────┘    │
│                                                                    │
│  ┌─FILTER──────────────────────────────────────────────────────┐  │
│  │  🔍 [Cari bug...]                                            │  │
│  │  Klasifikasi: [✅All] [🟢TP] [❌FP] [✅TN] [⚠️FN]          │  │
│  │  Severity:    [✅All] [🔴Critical] [🟠High] [🟡Med] [ℹ️Low]│  │
│  │  Program:     [All Programs ▾]  Sort: [Newest ▾]           │  │
│  └──────────────────────────────────────────────────────────────┘  │
│                                                                    │
│  ┌────────────────────────────────────────────────────────────┐  │
│  │  🟢 TRUE POSITIVES (89) — Akan di-submit ke Immunefi       │  │
│  │  ─────────────────────────────────────────────             │  │
│  │                                                             │  │
│  │  ┌──────────────────────────────────────────────────────┐  │  │
│  │  │ ▶ F-001  🔴 CRITICAL  Reentrancy in withdraw()      │  │  │
│  │  │   Ethena — USDe.sol — Ethereum                       │  │  │
│  │  │   Slither │ AI: 95% │ Exploit: ✅ $1.25M at risk    │  │  │
│  │  │                                    [Detail ▾] [Report]│  │  │
│  │  └──────────────────────────────────────────────────────┘  │  │
│  │  │                                                             │
│  │  │  (klik ▶ atau [Detail] untuk expand)                       │  │
│  │  │                                                             │  │
│  │  │  ┌─EXPANDED DETAIL─────────────────────────────────────┐  │  │
│  │  │  │                                                     │  │  │
│  │  │  │  📋 DESCRIPTION                                     │  │  │
│  │  │  │  The withdraw() function makes external call        │  │  │
│  │  │  │  before updating state...                            │  │  │
│  │  │  │                                                     │  │  │
│  │  │  │  ```solidity                                       │  │  │
│  │  │  │  function withdraw(uint amount) {                    │  │  │
│  │  │  │      (bool ok,) = msg.sender.call{value: amount}(); │  │  │
│  │  │  │      balances[msg.sender] -= amount;                │  │  │
│  │  │  │  }                                                   │  │  │
│  │  │  │  ```                                                │  │  │
│  │  │  │                                                     │  │  │
│  │  │  │  🤖 AI REASONING                                     │  │  │
│  │  │  │  "Confirmed reentrancy. External call before        │  │  │
│  │  │  │  state update allows attacker to drain all funds.   │  │  │
│  │  │  │  SWC-107, CWE-841. Severity: Critical."             │  │  │
│  │  │  │                                                     │  │  │
│  │  │  │  💥 EXPLOIT RESULT                                   │  │  │
│  │  │  │  ├─ Status: ✅ SUCCESS                               │  │  │
│  │  │  │  ├─ Method: Reentrancy via fallback                 │  │  │
│  │  │  │  ├─ Impersonated: 0xcb40... (contract owner)       │  │  │
│  │  │  │  ├─ Tx hash: 0xabcd...1234                          │  │  │
│  │  │  │  ├─ Gas used: 89,432                                │  │  │
│  │  │  │  └─ Value at risk: $1,250,000                       │  │  │
│  │  │  │                                                     │  │  │
│  │  │  │  🔧 FIX RECOMMENDATION                               │  │  │
│  │  │  │  ```solidity                                       │  │  │
│  │  │  │  function withdraw(uint amount) nonReentrant {       │  │  │
│  │  │  │      balances[msg.sender] -= amount;                │  │  │
│  │  │  │      (bool ok,) = msg.sender.call{value: amount}(); │  │  │
│  │  │  │  }                                                   │  │  │
│  │  │  │  ```                                                │  │  │
│  │  │  │                                                     │  │  │
│  │  │  │  📎 REFERENCES                                       │  │  │
│  │  │  │  ├─ SWC-107: https://swcregistry.io/docs/SWC-107    │  │  │
│  │  │  │  ├─ CWE-841: https://cwe.mitre.org/...              │  │  │
│  │  │  │  └─ PoC: [view poc.sol]                             │  │  │
│  │  │  │                                                     │  │  │
│  │  │  │  💬 FEEDBACK — Apakah klasifikasi ini benar?        │  │  │
│  │  │  │  [✅ Confirm TP] [❌ Reject — ini FP] [⚠️ Ini FN]  │  │  │
│  │  │  │  [✏️ Add Notes...]                                  │  │  │
│  │  │  │  ─────────────────────────────────────────           │  │  │
│  │  │  │  Status: ✅ Confirmed as TP (3 feedback, 100% agree) │  │  │
│  │  │  │                                                     │  │  │
│  │  │  │  riwayat feedback:                                   │  │  │
│  │  │  │  ├─ You: ✅ Confirmed TP — "Exploit confirmed"      │  │  │
│  │  │  │  └─ vyper: ✅ Auto-confirmed (exploit success)     │  │  │
│  │  │  │                                                     │  │  │
│  │  │  │  [📋 Copy to Clipboard] [📤 Buka Report Lengkap]   │  │  │
│  │  │  └─────────────────────────────────────────────────────┘  │  │
│  │                                                             │  │
│  │  ┌──────────────────────────────────────────────────────┐  │  │
│  │  │ ▶ F-002  🟠 HIGH  Flash loan oracle manipulation     │  │  │
│  │  │   Lido — stETH.sol — Ethereum                        │  │  │
│  │  │   Mythril │ AI: 87% │ Exploit: ✅ $890K at risk     │  │  │
│  │  │                                    [Detail ▾] [Report]│  │  │
│  │  └──────────────────────────────────────────────────────┘  │  │
│  │                                                             │  │
│  │  ... (semua TP listings)                                    │  │
│  └────────────────────────────────────────────────────────────┘  │
│                                                                    │
│  ┌────────────────────────────────────────────────────────────┐  │
│  │  ❌ FALSE POSITIVES (45) — Dicatat, tidak di-submit         │  │
│  │  ──────────────────────────────────────────────            │  │
│  │                                                             │  │
│  │  ┌──────────────────────────────────────────────────────┐  │  │
│  │  │ ▶ F-012  🟡 MEDIUM  Unused return value               │  │  │
│  │  │   Aave — aToken.sol — Ethereum                        │  │  │
│  │  │   Slither │ AI: "False alarm, safe in context"       │  │  │
│  │  │                                    [Detail ▾]          │  │  │
│  │  └──────────────────────────────────────────────────────┘  │  │
│  │  │                                                             │  │
│  │  │  (klik expand → lihat kenapa AI bilang FP)                │  │  │
│  │  │                                                             │  │
│  │  ... (semua FP listings)                                    │  │
│  └────────────────────────────────────────────────────────────┘  │
│                                                                    │
│  ┌────────────────────────────────────────────────────────────┐  │
│  │  ✅ TRUE NEGATIVES (156) — Dikonfirmasi aman                │  │
│  │  ────────────────────────────────────────────               │  │
│  │                                                             │  │
│  │  ┌──────────────────────────────────────────────────────┐  │  │
│  │  │ ▶ F-023  ℹ️ INFO  Low-level calls in safe context    │  │  │
│  │  │   Uniswap — swap.sol — Ethereum                      │  │  │
│  │  │   AI: "Safe — uses checks-effects-interactions"     │  │  │
│  │  │                                    [Detail ▾]          │  │  │
│  │  └──────────────────────────────────────────────────────┘  │  │
│  │                                                             │  │
│  │  ... (semua TN listings, bisa di-collapse)                 │  │
│  │                                                             │  │
│  │  [Show all 156 ▼] [Collapse all ▲]                          │  │
│  └────────────────────────────────────────────────────────────┘  │
│                                                                    │
│  ┌────────────────────────────────────────────────────────────┐  │
│  │  ⚠️ FALSE NEGATIVES (22) — 🔴 PRIORITAS PEMBELAJARAN       │  │
│  │  ───────────────────────────────────────────────           │  │
│  │                                                             │  │
│  │  ┌──────────────────────────────────────────────────────┐  │  │
│  │  │ ▶ FN-003  🔴 CRITICAL  Oracle Manipulation           │  │  │
│  │  │   Ethena — USDe.sol — Ethereum                       │  │  │
│  │  │   Terlewat oleh: Slither                             │  │  │
│  │  │   Ditemukan oleh: Immunefi Rejection                 │  │  │
│  │  │                                    [Detail ▾] [Fix]   │  │  │
│  │  └──────────────────────────────────────────────────────┘  │  │
│  │  │                                                             │  │
│  │  │  (klik expand → lihat root cause + improvement)            │  │  │
│  │  │                                                             │  │
│  │  ┌─EXPANDED DETAIL──────────────────────────────────────┐  │  │
│  │  │  🔍 ROOT CAUSE                                       │  │  │
│  │  │  "Slither tidak memiliki detector untuk oracle       │  │  │
│  │  │  price validation. Contract menggunakan Chainlink    │  │  │
│  │  │  price feed tanpa validasi batas harga."             │  │  │
│  │  │                                                       │  │  │
│  │  │  🛠️ IMPROVEMENT                                      │  │  │
│  │  │  ├─ Status: ✅ Pattern added                          │  │  │
│  │  │  ├─ Pattern: `oracle-manipulation` ditambahkan ke     │  │  │
│  │  │  │  Vuln DB dengan rule Chainlink price validation    │  │  │
│  │  │  └─ Re-verify: re-run audit untuk kontrak serupa     │  │  │
│  │  │                                                       │  │  │
│  │  │  [📋 Copy Lesson] [✅ Tandai Selesai]                │  │  │
│  │  └───────────────────────────────────────────────────────┘  │  │
│  │                                                             │  │
│  │  ┌──────────────────────────────────────────────────────┐  │  │
│  │  │ ▶ FN-001  🟠 HIGH  Integer Overflow                  │  │  │
│  │  │   Uniswap — pair.sol — Ethereum                      │  │  │
│  │  │   Terlewat oleh: Echidna                             │  │  │
│  │  │   Ditemukan oleh: Manual Review                      │  │  │
│  │  │                                    [Detail ▾] [Fix]   │  │  │
│  │  └──────────────────────────────────────────────────────┘  │  │
│  │                                                             │  │
│  │  ... (semua FN listings)                                   │  │
│  └────────────────────────────────────────────────────────────┘  │
│                                                                    │
│  ┌────────────────────────────────────────────────────────────┐  │
│  │  📊 Precision by Tool                                       │  │
│  │  Slither ████████████ 69% │ Mythril ██████████ 68%        │  │
│  │  Echidna ██████      46% │ AI      ████████████ 82%      │  │
│  └────────────────────────────────────────────────────────────┘  │
│                                                                    │
│  Page 1 of 12 — Menampilkan 20 dari 312 findings                │  │
│                                                                    │
└──────────────────────────────────────────────────────────────────┘
```

### Dashboard Route

```python
# vyper/web/routes/dashboard.py

@router.get("/")
async def dashboard(
    request: Request,
    classification: str = "all",
    severity: str = "all",
    program: str = "all",
    search: str = "",
    sort: str = "newest",
    page: int = 1
):
    metrics = load_json("metrics.json")
    
    # Load semua findings dari semua audit
    all_findings = load_all_findings()  # scan audits/ dir
    
    # Filter
    filtered = filter_findings(all_findings, classification, severity, program, search)
    
    # Sort
    filtered = sort_findings(filtered, sort)
    
    # Paginate
    total = len(filtered)
    page_size = 20
    paged = filtered[(page-1)*page_size : page*page_size]
    
    # Group by classification
    tp = [f for f in paged if f.classification == "true_positive"]
    fp = [f for f in paged if f.classification == "false_positive"]
    tn = [f for f in paged if f.classification == "true_negative"]
    fn = [f for f in paged if f.classification == "false_negative"]
    
    return templates.TemplateResponse("dashboard.html", {
        "request": request,
        "metrics": metrics,
        "tp": tp,
        "fp": fp,
        "tn": tn,
        "fn": fn,
        "total": total,
        "page": page,
        "pages": (total // page_size) + 1,
        "filters": {
            "classification": classification,
            "severity": severity,
            "program": program,
            "search": search,
            "sort": sort
        },
        "programs": get_all_programs(),
        "docker_status": check_docker(),
        "last_sync": get_last_sync_time()
    })

```

---

## 5. Halaman Programs `/programs`

```
┌──────────────────────────────────────────────────────────────────┐
│  📋 Immunefi Programs                                   [sync] │
│                                                                    │
│  🔍 [Search programs...]      [Chain: All ▾]  [Sort: Bounty ▾]  │
│                                                                    │
│  ┌────────┬──────────────┬────────┬─────────┬────────┬─────────┐│
│  │ Status │ Program      │ Chain  │ Bounty  │ Scanned│ Action  ││
│  ├────────┼──────────────┼────────┼─────────┼────────┼─────────┤│
│  │ 🟢     │ Ethena       │ ETH    │ $3,000K │ 2/26   │ ▶ Audit ││
│  │ 🟢     │ Lido         │ ETH    │ $2,000K │ 4/12   │ ▶ Audit ││
│  │ 🟡     │ Aave         │ ETH    │ $1,500K │ 1/8    │ ▶ Audit ││
│  │ 🟢     │ Uniswap      │ ETH    │ $1,000K │ 3/15   │ ▶ Audit ││
│  │ ⚪     │ Solana       │ SOL    │ $500K   │ 0/5    │ ▶ Audit ││
│  │ 🟢     │ PancakeSwap  │ BSC    │ $750K   │ 6/6    │ ✅ Done ││
│  │ 🔴     │ Euler        │ ETH    │ $250K   │ 0/3    │ Closed  ││
│  └────────┴──────────────┴────────┴─────────┴────────┴─────────┘│
│                                                                    │
│  Page 1 of 12 — Showing 7 of 234 programs                        │
│                                                                    │
│  📊 Stats: 234 total │ 189 active │ 45 closed │ 1,247 contracts  │
│  Total Max Bounty: $94,500,000                                    │
└──────────────────────────────────────────────────────────────────┘
```

---

## 6. Halaman Audit Detail — Paling Penting

```
┌──────────────────────────────────────────────────────────────────┐
│  🔍 Audit: ethena-USDe-2026-05-17                            [..]│
│                                                                    │
│  Program: Ethena           Chain: Ethereum                        │
│  Contract: 0x4c9edd...    Block: 21,345,678                     │
│  Status: ✅ Completed      Duration: 14m 22s                     │
│                                                                    │
│  ┌────────────────────────────────────────────────────────────┐  │
│  │  CLASSIFICATION MATRIX                                     │  │
│  │                                                             │  │
│  │          │ ACTUAL YES │ ACTUAL NO │                         │  │
│  │  ─────── ┼────────────┼───────────                          │  │
│  │  TEST OK │  TP  2 🟢  │  FP  1 ❌  │  Precision: 66.7%    │  │
│  │  TEST NO │  FN  0 ⚠️  │  TN  3 ✅  │  Recall: 100%        │  │
│  │          │            │           │  F1 Score: 80%        │  │
│  │          │            │           │  Overall: 7.2/10      │  │
│  └────────────────────────────────────────────────────────────┘  │
│                                                                    │
│  ┌────────────────────────────────────────────────────────────┐  │
│  │  🟢 TRUE POSITIVES — Akan di-submit ke Immunefi            │  │
│  │                                                             │  │
│  │  ┌──────────────────────────────────────────────────────┐  │  │
│  │  │ F-001  🔴 CRITICAL  Reentrancy in withdraw()         │  │  │
│  │  │        Tool: Slither │ Confidence: 95%                │  │  │
│  │  │        Source: 📦 GitHub (full repo)                  │  │  │
│  │  │        AI: "Confirmed — external call before state"   │  │  │
│  │  │        ────────────────────────────────────────────   │  │  │
│  │  │        💥 Exploit: ✅ SUCCESS                         │  │  │
│  │  │        ├─ Method: Reentrancy via fallback            │  │  │
│  │  │        ├─ Account impersonated: 0xcb40... (owner)    │  │  │
│  │  │        ├─ Tx hash: 0xabcd...1234                     │  │  │
│  │  │        ├─ Gas used: 89,432                           │  │  │
│  │  │        └─ Value at risk: $1,250,000                  │  │  │
│  │  │        ────────────────────────────────────────────   │  │  │
│  │  │        📄 PoC: [view poc.sol]  📝 Fix: [view fix]   │  │  │
│  │  │        📋 SWC: SWC-107  📎 CWE: CWE-841             │  │  │
│  │  └──────────────────────────────────────────────────────┘  │  │
│  │                                                             │  │
│  │  ┌──────────────────────────────────────────────────────┐  │  │
│  │  │ F-002  🟠 HIGH  Flash loan oracle manipulation        │  │  │
│  │  │        Tool: Mythril │ Confidence: 87%                │  │  │
│  │  │        AI: "Potential — price feed not validated"    │  │  │
│  │  │        ────────────────────────────────────────────   │  │  │
│  │  │        💥 Exploit: ✅ SUCCESS                         │  │  │
│  │  │        ├─ Value at risk: $890,000                    │  │  │
│  │  │        └─ PoC: [view poc.sol]                       │  │  │
│  │  └──────────────────────────────────────────────────────┘  │  │
│  └────────────────────────────────────────────────────────────┘  │
│                                                                    │
│  ┌────────────────────────────────────────────────────────────┐  │
│  │  ❌ FALSE POSITIVES — Dicatat, tidak di-submit              │  │
│  │                                                             │  │
│  │  ┌──────────────────────────────────────────────────────┐  │  │
│  │  │ F-003  🟡 MEDIUM  Unused return value                 │  │  │
│  │  │        Tool: Slither │ Confidence: 45%                │  │  │
│  │  │        AI: "False alarm — return value safe in ctx"  │  │  │
│  │  │        🔬 Exploit: Not attempted (low severity)       │  │  │
│  │  │        📝 Lesson: Pattern terlalu agresif, adjust    │  │  │
│  │  │        💬 [✅ Confirm FP] [❌ Actually ini TP]       │  │  │
│  │  └──────────────────────────────────────────────────────┘  │  │
│  └────────────────────────────────────────────────────────────┘  │
│                                                                    │
│  ┌────────────────────────────────────────────────────────────┐  │
│  │  ✅ TRUE NEGATIVES — Dikonfirmasi aman                      │  │
│  │                                                             │  │
│  │  F-004  ℹ️ INFO  Low-level calls — AI: safe, no exploit   │  │
│  │  F-005  ℹ️ INFO  Timestamp dependency — AI: safe context  │  │
│  │  F-006  ℹ️ INFO  Floating pragma — AI: safe               │  │
│  └────────────────────────────────────────────────────────────┘  │
│                                                                    │
│  ┌────────────────────────────────────────────────────────────┐  │
│  │  ⚠️ FALSE NEGATIVES — Tidak ada, 0 missed bugs 🎉          │  │
│  └────────────────────────────────────────────────────────────┘  │
│                                                                    │
│  ┌────────────────────────────────────────────────────────────┐  │
│  │  📊 Tool Performance — Audit Ini                           │  │
│  │                                                             │  │
│  │  Slither ████████████ 3 TP, 1 FP — 75% precision          │  │
│  │  Mythril ██████████████ 2 TP, 0 FP — 100% precision        │  │
│  │  AI      ████████████ 2 TP, 1 FP — 66% precision          │  │
│  └────────────────────────────────────────────────────────────┘  │
│                                                                    │
│  📄 Reports: [Immunefi Submission] [Full Internal]              │
└──────────────────────────────────────────────────────────────────┘
```

---

## 7. Halaman Report `/audits/{id}/report`

```
┌──────────────────────────────────────────────────────────────────┐
│  📄 Immunefi Vulnerability Report                          [..] │
│                                                                    │
│  ┌────────────────────────────────────────────────────────────┐  │
│  │  📋 SUBMISSION INFO                                         │  │
│  │  Program:  Ethena                                           │  │
│  │  Contract: USDe.sol (0x4c9edd...)                          │  │
│  │  Chain:    Ethereum                                         │  │
│  │  Severity: Critical                                         │  │
│  │                                                             │  │
│  │  [📋 Copy to Clipboard]  [📥 Download .md]  [📤 Open File] │  │
│  └────────────────────────────────────────────────────────────┘  │
│                                                                    │
│  ──────────────────────────────────────────────────────────────  │
│                                                                    │
│  ## Vulnerability: Reentrancy in withdraw()                       │
│                                                                    │
│  **Severity**: Critical                                           │
│  **SWC ID**: SWC-107                                             │
│  **CWE ID**: CWE-841                                             │
│                                                                    │
│  ### Description                                                  │
│  The `withdraw()` function in USDe.sol makes an external          │
│  call before updating state:                                      │
│                                                                    │
│  ```solidity                                                    │
│  function withdraw(uint amount) external {                        │
│      require(balances[msg.sender] >= amount);                    │
│      (bool ok,) = msg.sender.call{value: amount}("");            │
│      balances[msg.sender] -= amount;                              │
│  }                                                               │
│  ```                                                              │
│                                                                    │
│  ### Impact                                                       │
│  An attacker can drain all ETH from the contract by calling       │
│  withdraw() from a malicious contract that re-enters the          │
│  function before state is updated.                                │
│                                                                    │
│  Estimated value at risk: **$1,250,000**                          │
│                                                                    │
│  ### Proof of Concept                                            │
│  [View PoC Script →]                                             │
│                                                                    │
│  ### Recommended Fix                                              │
│  Follow checks-effects-interactions pattern:                      │
│                                                                    │
│  ```solidity                                                    │
│  function withdraw(uint amount) external {                        │
│      require(balances[msg.sender] >= amount);                    │
│      balances[msg.sender] -= amount;                              │
│      (bool ok,) = msg.sender.call{value: amount}("");            │
│  }                                                               │
│  ```                                                              │
│                                                                    │
│  Or use OpenZeppelin ReentrancyGuard:                             │
│                                                                    │
│  ```solidity                                                    │
│  function withdraw(uint amount) external nonReentrant {           │
│      // ...                                                       │
│  }                                                               │
│  ```                                                              │
│                                                                    │
│  ### References                                                    │
│  - SWC-107: https://swcregistry.io/docs/SWC-107                 │
│  - OpenZeppelin: https://docs.openzeppelin.com/...               │
│                                                                    │
│  ──────────────────────────────────────────────────────────────  │
│                                                                    │
│  [📋 Copy to Clipboard — Full Report]                            │
└──────────────────────────────────────────────────────────────────┘
```

Format report **persis** mengikuti format yang Immunefi harapkan: title, severity, description, impact, PoC, fix, references.

---

## 8. Halaman Metrics `/metrics`

```
┌──────────────────────────────────────────────────────────────────┐
│  📈 Platform Metrics                                    [export] │
│                                                                    │
│  ┌────────────────────────────────────────────────────────────┐  │
│  │  OVERVIEW — All Time (47 audits)                           │  │
│  │  ┌──────┬──────┬──────┬──────┬─────────┬────────┬───────┐ │  │
│  │  │  TP  │  FP  │  TN  │  FN  │Precision│ Recall │  F1   │ │  │
│  │  ├──────┼──────┼──────┼──────┼─────────┼────────┼───────┤ │  │
│  │  │  89  │  45  │  156 │  22  │  66.4%  │ 80.2%  │ 72.7% │ │  │
│  │  └──────┴──────┴──────┴──────┴─────────┴────────┴───────┘ │  │
│  └────────────────────────────────────────────────────────────┘  │
│                                                                    │
│  ┌──────────────────────────┐  ┌───────────────────────────────┐ │
│  │  📊 Confusion Matrix      │  │  📈 Precision Trend           │ │
│  │                           │  │                               │ │
│  │          ACTUAL           │  │  90% ┤        ╭──╮            │ │
│  │        YES     NO         │  │  80% ┤ ╭──╮ ╭╯  ╰╮           │ │
│  │  TEST  TP 89   FP 45     │  │  70% ┤╭╯  ╰─╯    ╰╮           │ │
│  │  TEST  FN 22   TN 156    │  │  60% ┤╯            ╰──         │ │
│  │                           │  │      └──┬──┬──┬──┬──┬──┬──   │ │
│  │  Accuracy: 78.8%         │  │        W3 W4 W5 W6 W7 W8      │ │
│  └──────────────────────────┘  └───────────────────────────────┘ │
│                                                                    │
│  ┌────────────────────────────────────────────────────────────┐  │
│  │  🔧 Per-Tool Performance                                   │  │
│  │                                                             │  │
│  │  ┌──────────┬──────┬──────┬──────────┬────────┬──────────┐ │  │
│  │  │ Tool     │ TP   │ FP   │ Precision│ Trend  │  Score   │ │  │
│  │  ├──────────┼──────┼──────┼──────────┼────────┼──────────┤ │  │
│  │  │ Slither  │  45  │  20  │  69.2%   │  +5%   │ 🟢 Good  │ │  │
│  │  │ Mythril  │  38  │  18  │  67.9%   │  +3%   │ 🟢 Good  │ │  │
│  │  │ Echidna  │   6  │   7  │  46.2%   │  -2%   │ 🟡 Fair  │ │  │
│  │  │ AI       │  62  │  14  │  81.6%   │ +12%   │ 🟢 Best  │ │  │
│  │  └──────────┴──────┴──────┴──────────┴────────┴──────────┘ │  │
│  └────────────────────────────────────────────────────────────┘  │
│                                                                    │
│  ┌────────────────────────────────────────────────────────────┐  │
│  │  ⚠️ Learning Opportunities — 5 Open FN                      │  │
│  │                                                             │  │
│  │  🔴 FN-003  Oracle Manipulation — Ethena                   │  │
│  │     Root: Slither doesn't check Chainlink validation       │  │
│  │     Status: Pattern added ✅ → Prevent future FN           │  │
│  │                                                             │  │
│  │  🔴 FN-002  Access Control — Lido                         │  │
│  │     Root: Mythril missed role-based modifier               │  │
│  │     Status: In progress 🔄                                 │  │
│  │                                                             │  │
│  │  🟡 FN-001  Integer Overflow — Uniswap                     │  │
│  │     Root: Echidna fuzzing timeout                          │  │
│  │     Status: Fixed ⏱ timeout increased                     │  │
│  └────────────────────────────────────────────────────────────┘  │
│                                                                    │
│  ┌────────────────────────────────────────────────────────────┐  │
│  │  🏆 Top Findings by Severity                                │  │
│  │  🔴 Critical: 12   🟠 High: 34   🟡 Medium: 28   ℹ️ Low: 15 │  │
│  └────────────────────────────────────────────────────────────┘  │
└──────────────────────────────────────────────────────────────────┘
```

---

## 9. Settings Page `/settings`

```
┌──────────────────────────────────────────────────────────────────┐
│  ⚙️ Settings                                              [save] │
│                                                                    │
│  ┌────────────────────────────────────────────────────────────┐  │
│  │  🔗 RPC Endpoints                                          │  │
│  │  ┌──────────────────────────────┬────────────────────────┐ │  │
│  │  │ ethereum                     │ https://eth.llamarpc...│ │  │
│  │  │ arbitrum                     │ https://arb1.arbit...  │ │  │
│  │  │ optimism                     │ https://opt.llamarpc...│ │  │
│  │  │ base                          │ https://base.llamar...│ │  │
│  │  └──────────────────────────────┴────────────────────────┘ │  │
│  │  Health: ✅ eth ✅ arb ✅ opt ✅ base         [Auto Discover]│  │
│  └────────────────────────────────────────────────────────────┘  │
│                                                                    │
│  ┌────────────────────────────────────────────────────────────┐  │
│  │  🔑 API Keys                                               │  │
│  │  ┌──────────────────────────────┬────────────────────────┐ │  │
│  │  │ OpenAI                       │ sk-...****            │ │  │
│  │  │ Etherscan                    │ **********            │ │  │
│  │  └──────────────────────────────┴────────────────────────┘ │  │
│  └────────────────────────────────────────────────────────────┘  │
│                                                                    │
│  ┌────────────────────────────────────────────────────────────┐  │
│  │  ⚙️ Scan Configuration                                     │  │
│  │  ┌──────────────────────────────────────────────────────┐  │  │
│  │  │ Auto-exploit:  [✅] for critical/high findings        │  │  │
│  │  │ Max instances:  [2] concurrent Anvil containers       │  │  │
│  │  │ Tools:         [✅] Slither [✅] Mythril [ ] Echidna │  │  │
│  │  │ Slither config: [Default] [Aggressive] [Minimal] ▼  │  │  │
│  │  │ Sync interval: [6] hours                              │  │  │
│  │  └──────────────────────────────────────────────────────┘  │  │
│  └────────────────────────────────────────────────────────────┘  │
│                                                                    │
│  ┌────────────────────────────────────────────────────────────┐  │
│  │  🔔 Notifications                                          │  │
│  │  ┌──────────────────────────────────────────────────────┐  │  │
│  │  │ Notify on: [✅] Critical [✅] High [ ] Medium [ ] Info│  │  │
│  │  │                                                       │  │  │
│  │  │ 📱 Desktop: [✅] Enabled                              │  │  │
│  │  │ 💬 Discord: [✅] https://discord.com/api/webhooks/... │  │  │
│  │  │ ✈️ Telegram: [✅] Bot: 123456:ABC... Chat: -100...    │  │  │
│  │  │ 📧 Email:    [ ] smtp.gmail.com:587 user@...           │  │  │
│  │  └──────────────────────────────────────────────────────┘  │  │
│  └────────────────────────────────────────────────────────────┘  │
│                                                                    │
│  ┌────────────────────────────────────────────────────────────┐  │
│  │  🔗 Webhooks                                               │  │
│  │  ┌──────────────────────────────────────────────────────┐  │  │
│  │  │ URL: https://hooks.slack.com/services/T...           │  │  │
│  │  │ Events: [x] Critical [x] High [ ] Info              │  │  │
│  │  │ Secret: ********    Status: ✅ Last call: 2m ago    │  │  │
│  │  │                                          [Test] [Del]│  │  │
│  │  ├──────────────────────────────────────────────────────┤  │  │
│  │  │ URL: https://pagerduty.com/hooks/...                 │  │  │
│  │  │ Events: [x] Critical [ ] High [ ] Info              │  │  │
│  │  │ Secret: ********    Status: ✅ Last call: 5h ago    │  │  │
│  │  │                                          [Test] [Del]│  │  │
│  │  ├──────────────────────────────────────────────────────┤  │  │
│  │  │ [+ Add Webhook]                                      │  │  │
│  │  └──────────────────────────────────────────────────────┘  │  │
│  └────────────────────────────────────────────────────────────┘  │
│                                                                    │
│  ┌────────────────────────────────────────────────────────────┐  │
│  │  📁 Data — ~/.vyper/                                      │  │
│  │  Immunefi: 2.3 MB (234 programs, 1,247 contracts)          │  │
│  │  Audits:   124.5 MB (47 audits, 312 findings)              │  │
│  │  Reports:  12.8 MB (94 reports)                            │  │
│  │  Repos:    1.2 GB (12 cloned GitHub repos)                 │  │
│  │  Backups:  845 MB (4 backups)                              │  │
│  │  [🗂 Open Data Folder]  [📦 Export All]  [🗑 Clear Cache]  │  │
│  └────────────────────────────────────────────────────────────┘  │
└──────────────────────────────────────────────────────────────────┘
```

---

## 10. Updates Page `/updates`

```
┌──────────────────────────────────────────────────────────────────┐
│  🔄 UPDATES                                               [sync] │
│                                                                    │
│  ┌────────────────────────────────────────────────────────────┐  │
│  │  📦 Vyper v0.2.0                                           │  │
│  │  ┌──────────────────────────────────────────────────────┐  │  │
│  │  │ Status: ✅ Up to date                                 │  │  │
│  │  │ Local:  v0.2.0 (17 Mei 2026)                         │  │  │
│  │  │ Remote: v0.2.0                                       │  │  │
│  │  │                                          [Check Now] │  │  │
│  │  └──────────────────────────────────────────────────────┘  │  │
│  └────────────────────────────────────────────────────────────┘  │
│                                                                    │
│  ┌────────────────────────────────────────────────────────────┐  │
│  │  🧩 Vulnerability Patterns                                  │  │
│  │  ┌──────────────────────────────────────────────────────┐  │  │
│  │  │ Version: 7 → Version: 9 (+2 patterns)                │  │  │
│  │  │ Last update: 15 Mei 2026                             │  │  │
│  │  │ New patterns: flash-loan-oracle, permit-frontrun     │  │  │
│  │  │                                          [Update Now]│  │  │
│  │  └──────────────────────────────────────────────────────┘  │  │
│  └────────────────────────────────────────────────────────────┘  │
│                                                                    │
│  ┌────────────────────────────────────────────────────────────┐  │
│  │  📄 Changelog                                              │  │
│  │  ┌──────────────────────────────────────────────────────┐  │  │
│  │  │ v0.2.0 (17 Mei 2026)                                 │  │  │
│  │  │  ✨ New: Forge integration                            │  │  │
│  │  │  ✨ New: Discord/Telegram notifications               │  │  │
│  │  │  🔧 Fixed: Slither detector tuning                   │  │  │
│  │  │                                                       │  │  │
│  │  │ v0.1.0 (10 Mei 2026)                                 │  │  │
│  │  │  🎉 Initial release                                   │  │  │
│  │  └──────────────────────────────────────────────────────┘  │  │
│  │  [Full Changelog →]                                        │  │
│  └────────────────────────────────────────────────────────────┘  │
└──────────────────────────────────────────────────────────────────┘
```

---

## 11. Backups Page `/backups`

```
┌──────────────────────────────────────────────────────────────────┐
│  💾 BACKUPS                                             [+ New] │
│                                                                    │
│  ┌────────────────────────────────────────────────────────────┐  │
│  │  📊 Storage Overview                                       │  │
│  │  ┌──────────┬──────────┬──────────┬──────────┐            │  │
│  │  │ ⚡ Now    │ Total    │ Last B/U │ Auto     │            │  │
│  │  │ 2.1 GB   │ 845 MB   │ 2d ago   │ Weekly ✅│            │  │
│  │  └──────────┴──────────┴──────────┴──────────┘            │  │
│  └────────────────────────────────────────────────────────────┘  │
│                                                                    │
│  ┌────────────────────────────────────────────────────────────┐  │
│  │  📋 Backup History                                         │  │
│  │  ┌────────────────────────┬──────────┬──────────┬────────┐ │  │
│  │  │ Name                   │ Size     │ Date     │        │ │  │
│  │  ├────────────────────────┼──────────┼──────────┼────────┤ │  │
│  │  │ weekly_20260517        │ 312 MB   │ 17-05-26 │ [◇Restore][✕]│ │
│  │  │ pre_update_patterns    │ 289 MB   │ 15-05-26 │ [◇Restore][✕]│ │
│  │  │ weekly_20260510        │ 245 MB   │ 10-05-26 │ [◇Restore][✕]│ │
│  │  └────────────────────────┴──────────┴──────────┴────────┘ │  │
│  └────────────────────────────────────────────────────────────┘  │
│                                                                    │
│  ┌────────────────────────────────────────────────────────────┐  │
│  │  ⚡ Auto-Backup Settings                                    │  │
│  │  ┌──────────────────────────────────────────────────────┐  │  │
│  │  │ Auto backup: [✅] Enabled (weekly, Sun 04:00)        │  │  │
│  │  │ Keep last:   [5] backups                              │  │  │
│  │  │ Exclude:     [✅] repos [✅] solc [ ] contracts      │  │  │
│  │  └──────────────────────────────────────────────────────┘  │  │
│  └────────────────────────────────────────────────────────────┘  │
└──────────────────────────────────────────────────────────────────┘
```

---

## 10. Submission Tracker Page `/submissions`

Melacak semua submission ke Immunefi dan bounty yang didapat.

```
┌──────────────────────────────────────────────────────────────────┐
│  💰 SUBMISSIONS                 Total Earned: $245,000    [sync] │
│                                                                    │
│  ┌────────┬────────────────┬──────────┬──────────┬────────┬────┐ │
│  │ Status │ Finding        │ Program  │ Bounty   │ Date   │    │ │
│  ├────────┼────────────────┼──────────┼──────────┼────────┼────┤ │
│  │ ⏳     │ Reentrancy     │ Ethena   │ —        │ 2h ago │ ▶  │ │
│  │ ✅     │ Oracle Manip   │ Lido     │ $50,000  │ 2d ago │ ▶  │ │
│  │ ✅     │ Access Control │ Aave     │ $25,000  │ 1w ago │ ▶  │ │
│  │ ❌     │ Integer Over   │ Uniswap  │ —        │ 2w ago │ ▶  │ │
│  │ ✅     │ Flash Loan     │ Euler    │ $150,000 │ 3w ago │ ▶  │ │
│  │ ✅     │ Reentrancy     │ Maker    │ $20,000  │ 1m ago │ ▶  │ │
│  └────────┴────────────────┴──────────┴──────────┴────────┴────┘ │
│                                                                    │
│  ┌────────────────────────────────────────────────────────────┐  │
│  │  📊 STATS                                                  │  │
│  │  ┌──────────┬──────────┬──────────┬──────────┬──────────┐ │  │
│  │  │Submitted │ Accepted │ Rejected │ Pending  │ Total $  │ │  │
│  │  ├──────────┼──────────┼──────────┼──────────┼──────────┤ │  │
│  │  │   15     │   10     │    2     │    3     │  $245K   │ │  │
│  │  └──────────┴──────────┴──────────┴──────────┴──────────┘ │  │
│  └────────────────────────────────────────────────────────────┘  │
│                                                                    │
│  ┌────────────────────────────────────────────────────────────┐  │
│  │  🏆 TOP EARNINGS                                           │  │
│  │                                                             │  │
│  │  🥇 Euler — Flash Loan Attack               $150,000       │  │
│  │     📅 3 weeks ago  |  Critical  |  ✅ Paid                │  │
│  │                                                             │  │
│  │  🥈 Lido — Oracle Manipulation              $50,000        │  │
│  │     📅 2 days ago  |  High  |  ✅ Paid                     │  │
│  │                                                             │  │
│  │  🥉 Aave — Access Control Bypass            $25,000        │  │
│  │     📅 1 week ago  |  Critical  |  ✅ Paid                 │  │
│  └────────────────────────────────────────────────────────────┘  │
│                                                                    │
│  ┌────────────────────────────────────────────────────────────┐  │
│  │  📈 EARNINGS OVER TIME                                     │  │
│  │                                                             │  │
│  │  $250K ┤                                          ╭──╮     │  │
│  │  $200K ┤                                   ╭──╮ ╭╯  ╰╮    │  │
│  │  $150K ┤                            ╭──╮ ╭╯  ╰─╯    ╰╮    │  │
│  │  $100K ┤                     ╭──╮ ╭╯  ╰─╯           ╰──  │  │
│  │  $50K  ┤              ╭──╮ ╭╯  ╰─╯                       │  │
│  │  $0    ┤─╭──╮ ╭──╮ ╭─╯  ╰─╯                             │  │
│  │        └──┬──┬──┬──┬──┬──┬──┬──┬──┬──┬──┬──              │  │
│  │          W1 W2 W3 W4 W5 W6 W7 W8 W9 W10                  │  │
│  └────────────────────────────────────────────────────────────┘  │
│                                                                    │
│  [📤 Submit New] [📋 Export Report]                              │
└──────────────────────────────────────────────────────────────────┘
```

### Submission Form (Modal)

```
┌──────────────────────────────────────────────────────────┐
│  📤 Submit to Immunefi                                   │
│                                                          │
│  Finding: F-001 — Reentrancy in withdraw()              │
│  Program: Ethena                                        │
│  Severity: Critical                                     │
│                                                          │
│  Immunefi URL: [https://immunefi.com/bounty/...       ]│
│  Notes: [Optional notes...                             ]│
│                                                          │
│  [Cancel]  [✅ Mark as Submitted]                        │
└──────────────────────────────────────────────────────────┘
```

---

## 11. Dashboard Auto-Refresh (SSE)

Dashboard otomatis update ketika ada audit selesai atau data berubah.

### SSE (Server-Sent Events) Flow

```
BROWSER                          FASTAPI                          VYPER CLI
──────                          ──────                          ────────
                                 
[SSE Connection] ──▶  /api/events                                 
      │                   │                                        
      │                   │                                  vyper audit 0x4c9edd...
      │                   │                                      
      │                   │◀──── write_event("audit.completed") ──┘
      │                   │         (menulis ke file temp)
      │                   │                                      
      │◀── SSE: {"type":  ─┘                                      
      │     "audit.done",                                         
      │     "audit_id": "..."}                                    
      │                                                           
      ▼                                                           
[Auto-refresh halaman]                                            
  ├─ Stat cards animate ke angka baru                             
  ├─ Finding list update                                          
  └─ Notifikasi "🔔 Audit selesai: Ethena — 2 TP ditemukan!"      
```

### Implementation

```python
# vyper/web/app.py — SSE endpoint

import time
import json
from pathlib import Path

EVENT_FILE = Path("~/.vyper/.last_event").expanduser()

@router.get("/api/events")
async def event_stream(request: Request):
    """SSE endpoint — dashboard listens here"""
    
    async def event_generator():
        last_event = 0
        while True:
            # Cek file event (ditulis oleh CLI saat audit selesai)
            if EVENT_FILE.exists():
                current = EVENT_FILE.stat().st_mtime
                if current > last_event:
                    last_event = current
                    event = json.loads(EVENT_FILE.read_text())
                    yield f"data: {json.dumps(event)}\n\n"
            
            await asyncio.sleep(2)  # Poll setiap 2 detik
    
    return StreamingResponse(event_generator(), media_type="text/event-stream")

# vyper/cli.py — notify dashboard after audit

@cli.command()
@click.argument("address")
def audit(address: str):
    """Full audit pipeline"""
    result = pipeline.run(address)
    
    # Kirim event ke dashboard
    EVENT_FILE.write_text(json.dumps({
        "type": "audit.completed",
        "audit_id": result.id,
        "program": result.program,
        "tp_count": result.tp_count,
        "score": result.score,
        "timestamp": time.time()
    }))
```

### Frontend (Vanilla JS)

```javascript
// static/dashboard.js

const eventSource = new EventSource("/api/events");

eventSource.onmessage = (event) => {
    const data = JSON.parse(event.data);
    
    if (data.type === "audit.completed") {
        // 1. Notifikasi
        showNotification(`🔔 Audit selesai: ${data.program} — ${data.tp_count} TP!`);
        
        // 2. Auto-refresh cards
        refreshStatCards();
        
        // 3. Update finding list
        refreshFindings();
    }
    
    if (data.type === "immunefi.synced") {
        showNotification(`📡 Immunefi sync: ${data.new_programs} program baru`);
        refreshProgramList();
    }
};

function refreshStatCards() {
    fetch("/api/metrics")
        .then(r => r.json())
        .then(metrics => {
            document.getElementById("tp-count").textContent = metrics.tp;
            document.getElementById("fp-count").textContent = metrics.fp;
            document.getElementById("fn-count").textContent = metrics.fn;
            animateNumber("score", metrics.overall_score);
        });
}
```

### Notifikasi di Dashboard

```
┌──────────────────────────────────────────────────────────┐
│  🔔 Audit selesai: Ethena — 2 TP ditemukan!    [x]     │
│  Reentrancy (Critical) + Oracle Manip (High)            │
│  Score: 8.5/10  |  [Lihat Detail ▸]                     │
└──────────────────────────────────────────────────────────┘
```

Notifikasi muncul di pojok kanan atas, auto-hide setelah 10 detik.

---

## 12. Route Map (Lengkap)

| Route | Page | Method | Data Source |
|-------|------|--------|-------------|
| `/` | Dashboard overview | GET | `metrics.json`, all findings |
| `/programs` | Program list | GET | `immunefi/programs.json` |
| `/programs/{slug}` | Program detail | GET | `immunefi/programs/{slug}.json` |
| `/audits` | Audit history | GET | Scan `audits/` directory |
| `/audits/{id}` | Audit detail | GET | `audits/{id}/findings.json` |
| `/audits/{id}/report` | Immunefi report | GET | → HTML render |
| `/audits/{id}/report/full` | Full report | GET | → HTML render |
| `/submissions` | Submission tracker | GET | `submissions.json` |
| `/metrics` | Platform metrics | GET | `metrics.json` |
| `/settings` | Config viewer | GET | `config.json` |
| `/updates` | Update checker | GET | `update/` |
| `/backups` | Backup manager | GET | `backups/` |
| `/api/metrics` | Metrics raw JSON | GET | JSON response |
| `/api/events` | SSE stream | GET | Live events |
| `/api/feedback` | Submit feedback | POST | Write to learning/ |
| `/api/daemon/{action}` | Daemon control | POST | Process control |
| `/api/backup` | Create backup | POST | Archive manager |
| `/api/backup/{name}/restore` | Restore backup | POST | Archive manager |
| `/api/update/check` | Check updates | GET | Version check |
| `/api/update/patterns` | Update patterns | POST | Update manager |
| `/api/update/all` | Update all | POST | Update manager |
| `/api/webhook/test` | Test webhook | POST | Webhook manager |

### API Route: Submit Feedback

```python
# vyper/web/routes/feedback.py

@router.post("/api/feedback")
async def submit_feedback(data: FeedbackRequest):
    """Submit feedback dari dashboard"""
    
    # 1. Simpan feedback
    feedback = {
        "id": f"FB-{uuid4().hex[:8]}",
        "finding_id": data.finding_id,
        "type": data.feedback_type,  # confirm_tp, reject_fp, mark_fn
        "reason": data.reason,
        "source": "dashboard",
        "created_at": time.time()
    }
    append_json("~/.vyper/learning/feedback.json", feedback)
    
    # 2. Trigger improvement engine
    if data.feedback_type in ("reject_fp", "mark_fn"):
        improver = ImprovementEngine()
        improver.process_feedback(feedback)
    
    # 3. Update metrics
    metrics = MetricsTracker()
    metrics.update_from_feedback(feedback)
    
    return {"status": "ok", "feedback_id": feedback["id"]}
```

---

## 13. Daemon Live View — Di Sidebar & Dashboard

Sidebar menampilkan status daemon real-time. Dashboard punya panel daemon log.

### Sidebar — Daemon Status

```
│                      │
│  ─────────────       │
│  🟢 DAEMON ACTIVE    │
│  ├─ Uptime: 3h 24m  │
│  ├─ Audits: 7       │
│  ├─ Critical: 3 🔴  │
│  └─ Next: ~12 min   │
│                      │
│  [⏸ Pause] [⏹ Stop] │
│                      │
```

Saat daemon tidak aktif:
```
│  ⚪ DAEMON STOPPED   │
│                      │
│  [▶ Start Daemon]    │
│                      │
```

### Dashboard — Daemon Panel

Di halaman dashboard utama `/`, setelah finding list, ada panel daemon:

```
┌──────────────────────────────────────────────────────────────┐
│  🤖 DAEMON — AUTONOMOUS HUNTER                 [⏸] [⏹]     │
│  ─────────────────────────────────────────────               │
│                                                              │
│  🟢 Running since: 2026-05-17 14:00 (3h 24m)                │
│                                                              │
│  ┌──────────────────────┬────────────────────────────────┐   │
│  │  STATS               │  CURRENT AUDIT                 │   │
│  │  ┌──────┬─────────┐  │  Auditing: Lido                │   │
│  │  │ Total│   7     │  │  Contract: 0x8a9b7c...        │   │
│  │  │ TP   │  12     │  │  Progress: ████████░░ 80%     │   │
│  │  │ 🔴 Cr│   3     │  │  Step: AI Analysis            │   │
│  │  │ 💥 Ex│   3     │  │  Started: 14:35               │   │
│  │  │ 📄 Rp│   7     │  │  ETA: ~5 minutes              │   │
│  │  └──────┴─────────┘  └────────────────────────────────┘   │
│  └────────────────────────────────────────────────────────┘   │
│                                                              │
│  ┌─LIVE LOG───────────────────────────────────────────────┐  │
│  │ 14:00  🚀 Daemon started                               │  │
│  │ 14:05  📡 Synced Immunefi — 234 programs               │  │
│  │ 14:10  🔍 Auditing Ethena/0x4c9edd...                  │  │
│  │ 14:25  🔴 CRITICAL! Reentrancy — $1.25M at risk       │  │
│  │ 14:26  💥 Exploit successful — PoC generated           │  │
│  │ 14:30  📄 Report generated — immunefi.md               │  │
│  │ 14:35  🔍 Auditing Lido/0x8a9b7c...                    │  │
│  │ 14:50  🟠 HIGH! Oracle Manipulation found              │  │
│  │ 15:00  🔄 Waiting for next cycle (60 min)              │  │
│  │ 16:00  🔍 Auditing Aave/0x3e4f5a...                    │  │
│  │ 16:15  ⚠️ Mythril timeout, skipping...                 │  │
│  │ 17:00  🔍 Auditing Euler/0x1b2c3d...                   │  │
│  └────────────────────────────────────────────────────────┘  │
│                                                              │
│  [Auto-scroll ▼]                                             │
│                                                              │
│  QUEUE (Next 5):                                             │
│  ⏳ 0x1b2c3d... Euler        💤 Priority 25                  │
│  ⏳ 0x5e6f7a... Maker        💤 Priority 22                  │
│  ⏳ 0x7a8b9c... Compound     💤 Priority 18                  │
│  ⏳ 0x9d0e1f... SushiSwap    💤 Priority 15                  │
│  ⏳ 0x2a3b4c... Curve         💤 Priority 12                  │
└──────────────────────────────────────────────────────────────┘
```

### Daemon Control dari Dashboard

Tombol di daemon panel:
- **⏸ Pause** — Hentikan sementara, lanjutkan nanti
- **⏹ Stop** — Hentikan total
- **▶ Start** — Mulai daemon (jika sedang stop)
- **⚡ Skip** — Skip audit yang sedang berjalan, lanjut ke next

Semua via API call ke `POST /api/daemon/{action}`.

```python
@router.post("/api/daemon/{action}")
async def daemon_control(action: str):
    """Control daemon from dashboard"""
    if action == "start":
        subprocess.Popen(["vyper", "daemon", "start"])
        return {"status": "starting"}
    elif action == "stop":
        subprocess.Popen(["vyper", "daemon", "stop"])
        return {"status": "stopping"}
    elif action == "pause":
        write_event({"type": "daemon.pause"})
        return {"status": "paused"}
```

### SSE Events from Daemon

Daemon kirim event via file yang sama dengan audit CLI:

```python
# Daemon events yang dikirim ke dashboard:
{
  "type": "daemon.started",
  "timestamp": 1717890000
}
{
  "type": "daemon.audit_started",
  "contract": "0x8a9b7c...",
  "program": "Lido"
}
{
  "type": "daemon.critical_found",
  "finding": "Reentrancy in withdraw()",
  "program": "Ethena",
  "value_at_risk": 1250000
}
{
  "type": "daemon.cycle_complete",
  "audits_done": 3,
  "tp_found": 2,
  "next_cycle": "16:00"
}
```

---

## 14. Data Flow (Updated dengan SSE + Feedback + Daemon)

```
BROWSER                          FASTAPI                          ~/.vyper/
──────                          ──────                          ─────────

[SSE CONNECTION] ───▶  /api/events ──▶ poll .last_event file
      │                                    
[DASHBOARD LOAD] ───▶  GET / ────────▶  metrics.json
      │                   │                  audits/*/findings.json
      │                   │                  learning/false_negatives.json
      │◀── HTML ◀────────┘                  
      │                                       
[USER KLIK FEEDBACK] ──▶  POST /api/feedback
      │                      │                 
      │                      │──▶ append learning/feedback.json
      │                      │──▶ trigger ImprovementEngine
      │                      │──▶ update metrics.json
      │◀── {"status": "ok"} ◀┘
      │                                       
[AUDIT COMPLETED]  ◀──  SSE: audit.done ◀─── CLI writes .last_event
      │                                       
      ▼                                       
  Auto-refresh cards + list                   
```

**Tidak ada write dari web UI ke file audit** — feedback adalah satu-satunya pengecualian (write ke `learning/feedback.json` dan `metrics.json`). Audit sendiri tetap via CLI.

```
BROWSER                          FASTAPI                          ~/.vyper/
──────                          ──────                          ─────────
                                                                 
Request /                        │                                  
  │                              ▼                                  
  └──▶ GET /dashboard ──────▶  app.py                           metrics.json
       ◀── HTML page ◀──────    │                           recent audits dir
                                 │                                  
                                 │  read_json("metrics.json")       
                                 │  read_dir("audits/")            
                                 │  render_template("dashboard.html")
                                                                 
Request /audits/{id}             │                                  
  │                              ▼                                  
  └──▶ GET /audits/abc ──────▶  app.py                           audits/abc/
       ◀── HTML page ◀──────    │                           findings.json
                                 │  read_json(f"audits/{id}/findings.json")
                                 │  read_markdown(f"audits/{id}/reports/immunefi.md")
                                 │  render_template("audit_detail.html")
                                                                 
Request /metrics                 │                                  
  │                              ▼                                  
  └──▶ GET /metrics ────────▶  app.py                           metrics.json
       ◀── HTML page ◀──────    │                           learning/
                                 │  read_json("metrics.json")       
                                 │  read_json("learning/false_negatives.json")
                                 │  render_template("metrics.html")
```

**Tidak ada write ke disk dari web UI** — semuanya readonly. Hanya CLI yang bisa menjalankan audit.

---

## 11. File Tambahan ke Proyek

```
Tambahan ke vyper/:

vyper/web/
├── app.py                    # FastAPI: 30 baris
├── routes/
│   ├── __init__.py           # 2 baris
│   ├── dashboard.py          # 40 baris
│   ├── programs.py           # 50 baris
│   ├── audits.py             # 70 baris
│   ├── reports.py            # 40 baris
│   ├── metrics.py            # 40 baris
│   └── settings.py           # 30 baris
├── templates/
│   ├── base.html             # Layout: 80 baris
│   ├── dashboard.html        # 100 baris
│   ├── programs.html         # 80 baris
│   ├── program_detail.html   # 70 baris
│   ├── audits.html           # 60 baris
│   ├── audit_detail.html     # 150 baris (paling kompleks)
│   ├── report.html           # 100 baris
│   ├── report_full.html      # 80 baris
│   ├── metrics.html          # 120 baris
│   └── settings.html         # 60 baris
└── static/
    └── style.css             # 50 baris (kustom tambahan)

Total: ~1,200 baris tambahan
```

CLI command untuk start:
```python
# vyper/cli.py — tambah ini

@cli.command()
def ui():
    """Open Vyper dashboard in browser"""
    import uvicorn
    import webbrowser
    
    webbrowser.open("http://localhost:3000")
    uvicorn.run("vyper.web.app:app", host="127.0.0.1", port=3000)
```

---

> **Vyper Dashboard** — Localhost web UI untuk melihat hasil audit.
> Readonly dari ~/.vyper/*.json. CLI untuk proses, Browser untuk lihat hasil.
>
> *Generated by lore-master — 17 Mei 2026*
