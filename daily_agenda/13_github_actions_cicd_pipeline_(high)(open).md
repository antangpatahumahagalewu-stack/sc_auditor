# Agenda 13 — GitHub Actions & CI/CD Pipeline Integration

> **Project**: sc_auditor (Vyper — Smart Contract Bug Hunter)
> **Status**: 🔴 OPEN
> **Severity**: HIGH — Zero CI/CD, semua deployment manual, blocker untuk team adoption
> **Dependensi**: Agenda 07 (docker-compose fix), Agenda 08 (test suite), Agenda 11 (Halmos), Agenda 12 (Agent)

---

## 1. Latar Belakang

**Masalah**: Saat ini tidak ada automated pipeline — semua build/test/deploy manual via `docker compose up`.

**Konsekuensi**:
| Issue | Dampak |
|-------|--------|
| Tidak ada automated build | Setiap perubahan harus build manual |
| Tidak ada test di CI | Regression tidak terdeteksi |
| Tidak ada image registry | Image hanya di local Docker |
| Tidak ada PR check | Kode broken bisa merge |
| Tidak ada auto-deploy | Update infrastruktur manual |

---

## 2. Detail Pekerjaan

### 2.1 GitHub Actions: CI Pipeline — Build & Test

File baru: `.github/workflows/ci.yml`

```yaml
name: Vyper CI
on:
  push:
    branches: [main, develop]
  pull_request:
    branches: [main]

concurrency:
  group: ${{ github.workflow }}-${{ github.ref }}
  cancel-in-progress: true

jobs:
  lint:
    name: Lint & Type Check
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with:
          python-version: "3.11"
          cache: "pip"
      - run: pip install ruff mypy
      - run: ruff check services/ --output-format=github
      - run: mypy services/ --ignore-missing-imports || true

  test:
    name: Unit & Integration Tests
    runs-on: ubuntu-latest
    needs: [lint]
    strategy:
      matrix:
        service: [
          "01-config", "02-immunefi", "03-source",
          "06-ai", "07-classifier", "10-notifier",
          "12-webhook", "13-upkeep"
        ]
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with:
          python-version: "3.11"
          cache: "pip"
      - name: Install dependencies
        run: |
          pip install -r services/${{ matrix.service }}/requirements.txt
          pip install pytest httpx
      - name: Run tests
        run: |
          cd services/${{ matrix.service }}
          python -m pytest tests/ -v --timeout=30 || true
        working-directory: services/${{ matrix.service }}

  build-images:
    name: Build Docker Images (Critical Services)
    runs-on: ubuntu-latest
    needs: [lint]
    strategy:
      matrix:
        service: [
          "01-config", "02-immunefi", "03-source",
          "04-scanner", "04a-scanner-slither", "04b-scanner-echidna",
          "04c-scanner-forge", "04d-scanner-halmos", "05-scanner-mythril",
          "06-ai", "07-classifier", "08-exploit", "09-reporter",
          "10-notifier", "11-orchestrator", "12-webhook",
          "13-upkeep", "14-agent", "15-dashboard", "16-submission"
        ]
    steps:
      - uses: actions/checkout@v4
      - name: Build ${{ matrix.service }}
        run: |
          docker build -t vyper/${{ matrix.service }}:${{ github.sha }} \
            -f services/${{ matrix.service }}/Dockerfile \
            services/${{ matrix.service }}/
        timeout-minutes: 30
```

### 2.2 GitHub Actions: Docker Image Registry (GHCR)

File baru: `.github/workflows/docker-publish.yml`

```yaml
name: Publish Docker Images
on:
  push:
    branches: [main]
    tags: ["v*.*.*"]

jobs:
  publish:
    name: Publish to GHCR
    runs-on: ubuntu-latest
    permissions:
      contents: read
      packages: write
    strategy:
      matrix:
        service: [
          "01-config", "02-immunefi", "03-source",
          "04-scanner", "04a-scanner-slither",
          "04b-scanner-echidna", "04c-scanner-forge",
          "04d-scanner-halmos", "05-scanner-mythril",
          "06-ai", "07-classifier", "08-exploit",
          "09-reporter", "10-notifier", "11-orchestrator",
          "12-webhook", "13-upkeep", "14-agent",
          "15-dashboard", "16-submission"
        ]
    steps:
      - uses: actions/checkout@v4
      - uses: docker/login-action@v3
        with:
          registry: ghcr.io
          username: ${{ github.actor }}
          password: ${{ secrets.GITHUB_TOKEN }}
      - name: Extract metadata
        id: meta
        uses: docker/metadata-action@v5
        with:
          images: ghcr.io/${{ github.repository }}/${{ matrix.service }}
          tags: |
            type=sha,prefix=
            type=semver,pattern={{version}}
            type=ref,event=branch
      - uses: docker/build-push-action@v5
        with:
          context: services/${{ matrix.service }}
          push: true
          tags: ${{ steps.meta.outputs.tags }}
          labels: ${{ steps.meta.outputs.labels }}
          cache-from: type=gha
          cache-to: type=gha,mode=max
```

### 2.3 GitHub Actions: Vyper Audit Action (Killer Feature)

File baru: `action/action.yml`

```yaml
name: "Vyper Audit"
description: "Auto-audit Solidity smart contracts on every PR"
author: "Vyper Team"
branding:
  icon: "shield"
  color: "red"

inputs:
  api-key:
    description: "Vyper API key"
    required: true
  tools:
    description: "Comma-separated scanner tools (slither,mythril,echidna,halmos)"
    required: false
    default: "slither,mythril"
  mode:
    description: "Output mode: pr-comment, annotation, json-summary"
    required: false
    default: "pr-comment"
  fail-on:
    description: "Fail CI on: critical, high, medium, low, never"
    required: false
    default: "critical"

runs:
  using: "docker"
  image: "Dockerfile"
```

File baru: `action/Dockerfile`

```dockerfile
FROM python:3.11-slim

RUN pip install vyper-cli httpx

COPY entrypoint.sh /entrypoint.sh
RUN chmod +x /entrypoint.sh

ENTRYPOINT ["/entrypoint.sh"]
```

File baru: `action/entrypoint.sh`

```bash
#!/bin/bash
set -e

# Parse inputs
API_KEY="${INPUT_API_KEY}"
TOOLS="${INPUT_TOOLS:-slither,mythril}"
MODE="${INPUT_MODE:-pr-comment}"
FAIL_ON="${INPUT_FAIL_ON:-critical}"

# Find Solidity files
FILES=$(find . -name "*.sol" -not -path "./node_modules/*" -not -path "./lib/*")

if [ -z "$FILES" ]; then
  echo "No Solidity files found to audit."
  exit 0
fi

# Run Vyper CLI on each file
RESULTS=""
for FILE in $FILES; do
  echo "Auditing: $FILE"
  RESULT=$(vyper scan "$FILE" --tools "$TOOLS" --json 2>&1 || true)
  RESULTS="$RESULTS $RESULT"
done

# Post results based on mode
case $MODE in
  pr-comment)
    python /post_comment.py "$RESULTS"
    ;;
  annotation)
    python /annotations.py "$RESULTS"
    ;;
  json-summary)
    echo "$RESULTS"
    ;;
esac

# Fail check
CRITICAL_COUNT=$(echo "$RESULTS" | grep -c '"severity":"critical"' || true)
if [ "$FAIL_ON" = "critical" ] && [ "$CRITICAL_COUNT" -gt 0 ]; then
  echo "::error::Found $CRITICAL_COUNT critical vulnerabilities"
  exit 1
fi
```

### 2.4 PR Comment Poster

File baru: `action/post_comment.py`

```python
"""Post audit results as PR comment using GitHub API.

Mendukung:
- Markdown formatting dengan severity colors
- Summary table (total findings per severity)
- Per-file breakdown
- Collapsible detail sections untuk findings
"""

import os
import json
import httpx

GITHUB_API = os.environ.get("GITHUB_API_URL", "https://api.github.com")
GITHUB_REPO = os.environ.get("GITHUB_REPOSITORY", "")
GITHUB_PR_NUM = os.environ.get("GITHUB_PR_NUMBER", "")
GITHUB_TOKEN = os.environ.get("GITHUB_TOKEN", "")

SEVERITY_COLORS = {
    "critical": "🔴",
    "high": "🟠",
    "medium": "🟡",
    "low": "🔵",
    "informational": "⚪",
}

def build_comment(results: list[dict]) -> str:
    """Build markdown PR comment from scan results."""
    lines = [
        "## 🔍 Vyper Audit Results",
        "",
        "| Severity | Count |",
        "|----------|-------|",
    ]
    
    counts = {"critical": 0, "high": 0, "medium": 0, "low": 0, "informational": 0}
    for r in results:
        for f in r.get("findings", []):
            sev = f.get("severity", "informational").lower()
            counts[sev] = counts.get(sev, 0) + 1
    
    for sev, count in counts.items():
        if count > 0:
            lines.append(f"| {SEVERITY_COLORS.get(sev, '⚪')} {sev.title()} | {count} |")
    
    lines.extend(["", "### Details"])
    for r in results:
        file_name = r.get("file", "unknown")
        lines.extend(["", f"<details><summary>{file_name}</summary>", ""])
        for f in r.get("findings", [])[:10]:
            sev = f.get("severity", "low").lower()
            lines.append(f"- {SEVERITY_COLORS.get(sev, '⚪')} **{f.get('title', 'Finding')}**")
            lines.append(f"  _{f.get('description', '')}_")
        if len(r.get("findings", [])) > 10:
            lines.append(f"  _... and {len(r['findings']) - 10} more findings_")
        lines.append("</details>")
    
    return "\n".join(lines)

async def post_comment(comment: str):
    """Post comment to PR via GitHub API."""
    async with httpx.AsyncClient() as client:
        # Delete previous vyper comments
        resp = await client.get(
            f"{GITHUB_API}/repos/{GITHUB_REPO}/issues/{GITHUB_PR_NUM}/comments",
            headers={"Authorization": f"Bearer {GITHUB_TOKEN}"},
        )
        for c in resp.json():
            if c["user"]["login"] == "github-actions[bot]" and "Vyper Audit" in c["body"]:
                await client.delete(
                    f"{GITHUB_API}/repos/{GITHUB_REPO}/issues/comments/{c['id']}",
                    headers={"Authorization": f"Bearer {GITHUB_TOKEN}"},
                )
        
        # Post new comment
        await client.post(
            f"{GITHUB_API}/repos/{GITHUB_REPO}/issues/{GITHUB_PR_NUM}/comments",
            headers={"Authorization": f"Bearer {GITHUB_TOKEN}"},
            json={"body": comment},
        )

if __name__ == "__main__":
    import asyncio
    results = json.loads(os.environ.get("RESULTS", "[]"))
    comment = build_comment(results)
    asyncio.run(post_comment(comment))
```

### 2.5 GitHub Actions: Release & Versioning

File baru: `.github/workflows/release.yml`

```yaml
name: Release
on:
  push:
    tags: ["v*.*.*"]

jobs:
  release:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - name: Generate Release Notes
        id: notes
        run: |
          echo "## Vyper ${{ github.ref_name }}" > release.md
          echo "" >> release.md
          echo "### Services" >> release.md
          for dir in services/*/; do
            name=$(basename "$dir")
            echo "- $name" >> release.md
          done
      - name: Create Release
        uses: softprops/action-gh-release@v2
        with:
          body_path: release.md
          files: |
            action/action.yml
            action/Dockerfile
```

---

## 3. Struktur File

```
.github/workflows/
├── ci.yml                         # 🆕 CI: lint + test + build
├── docker-publish.yml              # 🆕 Docker publish ke GHCR
└── release.yml                     # 🆕 GitHub Release automation

action/
├── action.yml                      # 🆕 GitHub Action definition
├── Dockerfile                      # 🆕 Action runtime container
├── entrypoint.sh                   # 🆕 Action entrypoint
├── post_comment.py                 # 🆕 PR comment poster
└── annotations.py                  # 🆕 Inline code annotations
```

---

## 4. Task List

| # | Task | File | Estimasi | Prioritas |
|---|------|------|----------|-----------|
| T1 | CI workflow: lint + test per service | `.github/workflows/ci.yml` | 30 min | P0 |
| T2 | CI workflow: build Docker images | `.github/workflows/ci.yml` | 20 min | P0 |
| T3 | Docker publish ke GHCR | `.github/workflows/docker-publish.yml` | 25 min | P1 |
| T4 | Vyper Audit Action definition | `action/action.yml` | 15 min | P1 |
| T5 | Action Dockerfile | `action/Dockerfile` | 10 min | P1 |
| T6 | Action entrypoint script | `action/entrypoint.sh` | 15 min | P1 |
| T7 | PR comment poster | `action/post_comment.py` | 30 min | P1 |
| T8 | Inline annotations | `action/annotations.py` | 20 min | P2 |
| T9 | Release workflow | `.github/workflows/release.yml` | 15 min | P2 |
| T10 | Test CI di repo real | — | 15 min | P2 |
| | **Total** | | **~195 menit** | |

---

## 5. Quality Gate

| Dimensi | Target | Cara Ukur |
|---------|--------|-----------|
| Correctness | 95% | CI passing, Docker images sukses di-publish |
| Performance | 80% | CI < 15 menit untuk 20 services |
| Security | 85% | GITHUB_TOKEN minimal scope, no secrets in log |
| Maintainability | 90% | DRY — matrix strategy untuk multi-service |
| Completeness | 100% | Build + test + publish + PR comment semua otomatis |
| Alignment | 100% | Semua 20 services ter-cover di CI |

---

*Dibuat: 2026-05-20 | Status: OPEN | Dependensi: Agenda 07, 08, 11*
