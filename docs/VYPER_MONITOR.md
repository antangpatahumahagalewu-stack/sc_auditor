# Vyper Monitor — Terminal Live Dashboard

> **Satu perintah. Semua proses terpantau. Real-time di terminal.**

```
┌─────────────────────────────────────────────────────────────────────────┐
│  ◆ VYPER Monitor — 19/19 ✅  Pipeline: 1 active  Queue: 2      Ctrl+Q  │
├─────────────────────────────────────────────────────────────────────────┤
│                                                                         │
│  📋 LIVE EVENTS (auto-scroll):                                         │
│  ───────────────────────────────────────────────────────────────────    │
│  10:23:45  ✅ Scan #47 selesai — 3 findings (1 TP, 2 FP)              │
│  10:23:42  🟢 Scanner: Analyzing USDe.sol...                          │
│  10:23:40  🟢 AI: Klasifikasi finding F-045 ✅ TP                     │
│  10:23:38  🟡 Scheduler: Menjadwalkan audit Ethena #48                │
│  10:23:35  🟢 Slither: 8 detectors aktif                              │
│  10:23:30  ❌ Notifier: Discord rate limit (retry in 5s)              │
│  10:23:28  🟢 Orchestrator: Pipeline #47 → STEP 4 (AI Analysis)       │
│  10:23:25  🟢 Exploit: PoC untuk F-003 ✅ success                    │
│  10:23:20  🟢 Scanner: Download kontrak dari Etherscan                │
│  10:23:15  🟢 Config: API key untuk Etherscan valid                  │
│  10:23:10  🟢 AI: Menganalisis finding F-045                         │
│  10:23:05  ✅ Audit #47 initiated — Ethena (USDe.sol)                │
│  ... (scroll ke atas untuk lihat history)                             │
│                                                                         │
├─ SUMMARY ───────────────────────────────────────────────────────────────┤
│  📊 47 audits · 312 findings · TP 89 · FP 45 · FN 22 · Precision 72%   │
│  🖥️ 🟢🟢🟢🟢🟢🟢🟢🟢🟢🟢🟢🟢🟢🟢🟢🟢🟢⚪  ●●●●●●●●●●●●●●●●●●⚪         │
├─ SHORTCUTS ─────────────────────────────────────────────────────────────┤
│  [/] Search  [Space] Pause  [1-6] Filter level  [↑↓] Scroll  [Q] Exit  │
└─────────────────────────────────────────────────────────────────────────┘
```

---

## 1. Filosofi

`vyper monitor` adalah **pengganti web dashboard** yang berjalan langsung di terminal.
Cukup satu perintah, tanpa browser, tanpa build step, tanpa dependency berat.

| Web Dashboard (lama) | vyper monitor (baru) |
|----------------------|----------------------|
| Butuh browser | Langsung di terminal |
| React 19 + TypeScript + Vite | Python + Textual |
| Build step (tsc, vite) | Zero build — langsung jalan |
| 26 halaman navigasi | Satu layar, live events |
| Perlu refresh manual | Auto-refresh real-time |
| Pisah service (port 8000) | Bisa jalan standalone |

---

## 2. Cara Kerja

```
$ vyper monitor
```

Saat dijalankan:

1. **Konek ke API services** → Polling health & stats dari service-service sc_auditor
2. **Subscribe ke event stream** → SSE dari orchestrator untuk real-time updates
3. **Tampilkan live events** → Auto-scrolling log di terminal
4. **Update summary bar** → Health status, pipeline stats tiap 5 detik
5. **Tunggu interaksi user** → Search, filter, pause, scroll, exit

### Data Sources

| Data | Sumber | Interval |
|------|--------|----------|
| Service health | `GET /health` tiap service (port 8001-8018) | 5 detik |
| Pipeline status | `GET /api/stats` (orchestrator port 8009) | 10 detik |
| Live events | `GET /api/events` SSE stream (orchestrator) | Real-time |
| Finding metrics | `GET /api/metrics` (classifier port 8005) | 30 detik |

Jika service tidak reachable, monitor akan menampilkan status **❌ DOWN**
dan terus mencoba reconnect secara otomatis.

---

## 3. Layout & Komponen

### 3.1 Status Bar (Header)

```
◆ VYPER Monitor — 19/19 ✅  Pipeline: 1 active  Queue: 2      Ctrl+Q
```

| Elemen | Makna |
|--------|-------|
| `◆ VYPER Monitor` | Branding |
| `19/19 ✅` | Service hidup / total (🟢 semua = ✅, ada merah = ❌) |
| `Pipeline: 1 active` | Audit sedang berjalan |
| `Queue: 2` | Antrian audit menunggu |
| `Ctrl+Q` | Tombol exit |

Warna header berubah sesuai status:
- 🟢 **Hijau** — Semua service OK
- 🟡 **Kuning** — Ada service down tapi tidak kritis
- 🔴 **Merah** — Service kritis down (scanner, orchestrator)

### 3.2 Event Log (Body — area utama)

Bagian terbesar dari layar. Menampilkan **live event stream** dari semua service.

Setiap event punya format:

```
HH:MM:SS  [LEVEL]  [SERVICE]: [Pesan]
```

**Level dan warna:**

| Level | Warna | Contoh |
|-------|-------|--------|
| `✅` | Hijau | Audit selesai, finding diklasifikasi |
| `🟢` | Hijau | Info normal, service OK, progress |
| `🟡` | Kuning | Warning, rate limit mendekati, queue penuh |
| `❌` | Merah | Error, service down, scan gagal |
| `⚡` | Biru | Event khusus, finding kritis, exploit success |

**Event yang muncul:**

| Dari Service | Event |
|-------------|-------|
| **Scanner** | Mulai scan, progress, selesai, tool download |
| **AI** | Analisis finding, klasifikasi (TP/FP/TN/FN) |
| **Exploit** | PoC generation, success/fail |
| **Classifier** | Confusion matrix update |
| **Notifier** | Discord/Telegram/Email send status |
| **Orchestrator** | Pipeline stage change, queue update |
| **Immunefi** | Program sync, new programs |
| **Agent** | Autonomous scan, learning update |
| **Upkeep** | Backup, update, metrics |

### 3.3 Summary Bar

```
📊 47 audits · 312 findings · TP 89 · FP 45 · FN 22 · Precision 72%
🖥️ 🟢🟢🟢🟢🟢🟢🟢🟢🟢🟢🟢🟢🟢🟢🟢🟢🟢⚪
```

**Baris 1 — Statistik:**
- Total audit yang pernah dijalankan
- Total findings
- TP (True Positive) — bug nyata yang ditemukan
- FP (False Positive) — alarm palsu
- FN (False Negative) — bug terlewat
- Precision — akurasi deteksi

**Baris 2 — Service Health Dots:**
- Satu dot per service (19 total)
- 🟢 = Service hidup
- 🔴 = Service down
- ⚪ = Service tidak aktif (sengaja dimatikan)

### 3.4 Shortcuts Bar (Footer)

```
[/] Search  [Space] Pause  [1-6] Filter level  [↑↓] Scroll  [Q] Exit
```

Tombol bantuan yang selalu terlihat.

---

## 4. Keyboard Shortcuts

| Tombol | Fungsi | Saat Digunakan |
|--------|--------|----------------|
| `Q` / `Ctrl+Q` | Keluar dari monitor | Kapan saja |
| `Space` | Pause / Resume auto-scroll | Ingin lihat event lama |
| `/` | Buka search bar | Mencari event tertentu |
| `Esc` | Tutup search / kembali | Setelah selesai search |
| `1` | Filter: semua event | Default — reset filter |
| `2` | Filter: ✅ sukses aja | Lihat completed tasks |
| `3` | Filter: 🟢 info aja | Lihat progress normal |
| `4` | Filter: 🟡 warning aja | Lihat potensi masalah |
| `5` | Filter: ❌ error aja | Troubleshooting |
| `6` | Filter: ⚡ kritis aja | Lihat finding kritis |
| `↑` | Scroll ke atas 1 baris | Lihat event sebelumnya |
| `↓` | Scroll ke bawah 1 baris | Kembali ke event baru |
| `PgUp` | Scroll ke atas 1 halaman | Loncat jauh ke atas |
| `PgDn` | Scroll ke bawah 1 halaman | Loncat ke bawah |
| `r` | Refresh manual | Paksa refresh data |
| `?` / `h` | Tampilkan help | Lupa shortcut |

### Mode Search

Saat tekan `/`:

```
Search: [________________]
Mencocokkan teks di pesan event. Case-insensitive.
Hasil akan difilter real-time saat mengetik.
Tekan Esc untuk kembali ke semua event.
```

Hasil pencarian akan menampilkan hanya event yang mengandung kata kunci.
Tekan `Esc` untuk menghapus filter dan kembali ke normal.

---

## 5. Contoh Sesi

### Memantau Audit Berjalan

```bash
$ vyper monitor
```

User melihat:
```
10:23:05  ✅ Audit #47 initiated — Ethena (USDe.sol)
10:23:10  🟢 Scanner: Downloading USDe.sol dari Etherscan
10:23:15  🟢 Scanner: Menjalankan Slither...
10:23:20  🟢 Slither: 8 detectors aktif
10:23:25  🟢 Scanner: Menjalankan Mythril...
10:23:30  🟡 Mythril: Analysis mungkin lambat (>30s)
10:23:35  🟢 AI: Menganalisis findings...
10:23:40  🟢 AI: Klasifikasi finding F-045 ✅ TP
10:23:42  🟢 AI: Klasifikasi finding F-046 ❌ FP
10:23:45  ✅ Scan #47 selesai — 3 findings (1 TP, 2 FP)
```

User bisa **pause** (Space) untuk baca detail, **scroll** ke atas untuk lihat history,
lalu **resume** (Space lagi) untuk lanjut pantau.

### Investigasi Error

Terlihat event merah:
```
10:23:30  ❌ Notifier: Discord rate limit (retry in 5s)
```

User tekan `5` untuk filter error saja, lalu lihat semua error yang terjadi.
Setelah selesai, tekan `1` untuk reset filter.

### Mencari Finding Tertentu

User ingin cari finding tentang "reentrancy":

1. Tekan `/`
2. Ketik `reentrancy`
3. Layar menampilkan hanya event yang mengandung "reentrancy"
4. Tekan `Esc` untuk kembali ke semua event

---

## 6. Arsitektur Teknis

```
┌────────────────────────────────────────────────────────────┐
│                    VYPER MONITOR (TUI)                      │
│                                                            │
│  Textual App                                               │
│  ┌──────────────────────────────────────────────────────┐  │
│  │  StatusBar (Rich Static, update tiap 5 detik)         │  │
│  ├──────────────────────────────────────────────────────┤  │
│  │  EventLog (RichLog, auto-scroll, search, filter)      │  │
│  ├──────────────────────────────────────────────────────┤  │
│  │  SummaryBar (Rich Static, update tiap 10 detik)       │  │
│  ├──────────────────────────────────────────────────────┤  │
│  │  ShortcutsBar (Static, tetap)                         │  │
│  └──────────────────────────────────────────────────────┘  │
│                                                            │
│  Background Tasks (asyncio)                                │
│  ┌──────────────────────────────────────────────────────┐  │
│  │  poll_health()      → tiap 5 detik                    │  │
│  │  poll_stats()       → tiap 10 detik                   │  │
│  │  subscribe_events() → SSE real-time                   │  │
│  └──────────────────────────────────────────────────────┘  │
│                                                            │
│  HTTP Client (httpx.AsyncClient)                           │
│  ┌──────────────────────────────────────────────────────┐  │
│  │  GET /health   → 19 services                         │  │
│  │  GET /api/stats → orchestrator                       │  │
│  │  GET /api/events → SSE stream                        │  │
│  └──────────────────────────────────────────────────────┘  │
└────────────────────────────────────────────────────────────┘
```

### Tech Stack

| Layer | Teknologi |
|-------|-----------|
| **TUI Framework** | Textual (dari pembuat Rich) |
| **HTTP Client** | httpx.AsyncClient (reuse dari CLI) |
| **Real-time** | asyncio + set_interval + SSE |
| **Data Format** | JSON API responses |
| **Dependencies** | textual, httpx, rich (already installed) |

### File Structure

```
cli/
├── monitor/
│   ├── __init__.py          # Package init
│   ├── app.py               # Textual App — layout, key bindings, timers
│   ├── widgets.py           # Custom widgets (StatusBar, EventLog, SummaryBar)
│   └── client.py            # HTTP client — polling & SSE
├── commands/
│   └── monitor_cmd.py       # Wrapper Typer command
├── main.py                  # ✏️ Register vyper monitor
└── requirements.txt         # ✏️ + textual
```

---

## 7. Instalasi

`vyper monitor` adalah bagian dari Vyper CLI. Jika sudah install Vyper CLI,
tinggal tambah dependency:

```bash
cd cli/
pip install textual
```

Atau install ulang Vyper CLI:

```bash
pip install -e .
```

---

## 8. Perbandingan dengan Web Dashboard

| Fitur | Web Dashboard (lama) | vyper monitor (baru) |
|-------|---------------------|---------------------|
| **Startup** | `vyper dashboard` → buka browser | `vyper monitor` → langsung di terminal |
| **Real-time** | SSE via fetch | Auto-polling + SSE |
| **Search** | Search bar di halaman | `/` + keyboard |
| **Filter** | Dropdown + klik | Tekan `1`-`6` |
| **Multi-tasking** | Harus alt+tab ke browser | Tetap di terminal |
| **Dependency** | React 19, TypeScript, Vite, Tailwind | Python + Textual |
| **Build** | tsc + vite build (~30 detik) | Zero build |
| **SSH/Linux** | Butuh port forwarding | Langsung jalan di SSH |
| **Resource** | ~50MB browser tab | ~15MB terminal |

---

## 9. Tips & Troubleshooting

### Monitor tidak muncul events

```bash
# Cek apakah service berjalan
vyper health

# Cek koneksi ke orchestrator
curl http://localhost:8009/health

# Jalankan audit untuk generate events
vyper scan <file.sol>
```

### Monitor lambat

```bash
# Turunkan frekuensi polling (via env)
export VYPER_POLL_INTERVAL=10
vyper monitor
```

### Ingin reset tampilan

Tekan `r` untuk refresh manual semua data dari API.

### Ingin keluar

`Q` atau `Ctrl+Q` — langsung kembali ke terminal.

---

## 10. Roadmap

| Fitur | Status |
|-------|--------|
| Live event stream dari orchestrator | ✅ Done |
| Service health dots | ✅ Done |
| Search events dengan `/` | ✅ Done |
| Filter by level (`1`-`6`) | ✅ Done |
| Pause/Resume auto-scroll | ✅ Done |
| Summary stats bar | ✅ Done |
| Mode error-only untuk troubleshooting | 🔜 Next |
| Export events ke file (`e`) | 🔜 Next |
| Detail panel (`Enter` di event) | 🔜 Next |
| Multi-profile (monitor beberapa instance) | 🔜 Future |

---

> **Vyper Monitor** — Bagian dari Vyper Smart Contract Bug Hunter.
> Satu perintah, semua terpantau. 🎯
