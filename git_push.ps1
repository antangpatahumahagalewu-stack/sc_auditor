# Git Push Script — Service 08 Mathematics Engine (Tahap 1-6)
# Jalankan: powershell -ExecutionPolicy Bypass -File git_push.ps1

$ErrorActionPreference = "Stop"

Write-Host "=== Git Push: Service 08 Mathematics Engine ===" -ForegroundColor Cyan

# 1. Check status
Write-Host "`n[1/5] Checking status..." -ForegroundColor Yellow
git status

# 2. Add all changes
Write-Host "`n[2/5] Staging all changes..." -ForegroundColor Yellow
git add -A

# 3. Show what's staged
Write-Host "`n[3/5] Staged files:" -ForegroundColor Yellow
git diff --cached --name-status

# 4. Commit
Write-Host "`n[4/5] Committing..." -ForegroundColor Yellow
git commit -m "feat(08-exploit): Mathematics Engine + Tahap 1-6 selesai

Tahap 1: src/maths/ engine - 10 files (z3 SAT, LLL lattice, fixed-point,
AMM V2/V3, modular arithmetic, MEV optimizer, statistical, game theory)

Tahap 2: 5 math primitives baru - sat_solve, fixed_point_attack,
lattice_reduce, concentrated_liquidity, modular_inversion

Tahap 3: Enhanced planner - graph_explore, combi_gen, mutation,
18 heuristic rules (R07-R18, mencakup semua 11 bugs)

Tahap 4: Enhanced analyzer - math vulnerability detection, precision
loss oracle dependency, storage layout, Uniswap patterns

Tahap 5: Enhanced engine - MathEngine integration ke exploit pipeline
(_math_exploit_pipeline sebelum compose)

Tahap 6: app.py +4 endpoints (POST /math/sat-solve, /math/fixed-point,
/math/mev-calc, GET /math/status), 6 Pydantic models baru"

# 5. Push
Write-Host "`n[5/5] Pushing to remote..." -ForegroundColor Yellow
git push

Write-Host "`n=== Done! ===" -ForegroundColor Green
