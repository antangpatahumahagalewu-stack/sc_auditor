# Agenda 12 — Autonomous Agent Intelligence (Self-Learning & Auto-Hunt)

> **Project**: sc_auditor (Vyper — Smart Contract Bug Hunter)
> **Status**: 🔴 OPEN
> **Severity**: CRITICAL — Agent service ada tapi memory kosong, tidak ada autonomous decision-making
> **Dependensi**: Agenda 05 (Case Management), Agenda 10 (Memory System)

---

## 1. Latar Belakang

Service `14-agent` sudah punya ReAct loop + skill registry + 8 pipeline skills, tapi:

| Gap | Dampak | Lokasi |
|-----|--------|--------|
| **Memory system kosong** (`__init__.py` only) | Agent tidak belajar dari pengalaman | `14-agent/src/memory/` |
| **No autonomous mode** | Agent hanya jalan saat di-trigger manual | `14-agent/src/agent.py` |
| **No case-based learning** | Bug pattern tidak di-capture untuk reuse | `14-agent/src/` |
| **No auto-hunt daemon** | Tidak bisa scan Immunefi 24/7 | `14-agent/src/daemon.py` |
| **No skill improvement loop** | Skill statis, tidak evolve | `14-agent/src/skills/` |
| **No feedback integration** | TP/FP dari user tidak feed ke agent learning | `14-agent/src/learning/` |

---

## 2. Detail Pekerjaan

### 2.1 Memory System Implementation (Lanjutan Agenda 10)

File: `services/14-agent/src/memory/` — implementasi penuh 3 tipe memory:

**Base Interface** (sudah ada di Agenda 10 spec):

```python
# services/14-agent/src/memory/base.py 🆕
from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Any, List, Optional

@dataclass
class MemoryEntry:
    id: str
    content: str
    metadata: dict
    timestamp: str
    embedding: Optional[List[float]] = None

class BaseMemory(ABC):
    @abstractmethod
    async def store(self, entry: MemoryEntry) -> str: ...
    @abstractmethod
    async def retrieve(self, query: str, limit: int = 5) -> List[MemoryEntry]: ...
    @abstractmethod
    async def delete(self, entry_id: str) -> bool: ...
    @abstractmethod
    async def clear(self) -> None: ...
```

**Vector Memory — Semantic Search:**

```python
# services/14-agent/src/memory/vector_store.py 🆕
"""Vector memory — cari kasus mirip via embedding similarity.
Storage: /data/agent/memory/vector_index.json

Digunakan untuk:
- Matching: "bug ini mirip dengan CASE-012 yang bounty $10k"
- Pattern recognition: "vulnerability pattern ini sudah pernah terlihat"
"""

class VectorMemory(BaseMemory):
    def __init__(self, model_name: str = "all-MiniLM-L6-v2"):
        self.model = SentenceTransformer(model_name)
        self.index: List[MemoryEntry] = []

    async def store(self, entry: MemoryEntry) -> str:
        entry.embedding = self.model.encode(entry.content).tolist()
        self.index.append(entry)
        return entry.id

    async def retrieve(self, query: str, limit: int = 5) -> List[MemoryEntry]:
        query_emb = self.model.encode(query)
        scores = [
            (np.dot(query_emb, e.embedding) / 
             (np.linalg.norm(query_emb) * np.linalg.norm(e.embedding)), e)
            for e in self.index if e.embedding
        ]
        scores.sort(key=lambda x: x[0], reverse=True)
        return [e for _, e in scores[:limit]]
```

**Episodic Memory — Experience Recall:**

```python
# services/14-agent/src/memory/episodic.py 🆕
"""Episodic memory — simpan pengalaman audit.
Setiap episode = satu siklus audit:
  {contract, findings, actions, outcome, bounty}
"""

class EpisodicMemory(BaseMemory):
    def __init__(self):
        self.episodes: List[dict] = []

    async def store_episode(self, episode: dict) -> str:
        episode["timestamp"] = datetime.now(timezone.utc).isoformat()
        self.episodes.append(episode)
        return episode.get("id", str(uuid.uuid4()))

    async def retrieve_similar(self, contract: str) -> List[dict]:
        """Cari episode audit sebelumnya untuk contract yang sama."""
        return sorted(
            [e for e in self.episodes if e.get("contract") == contract],
            key=lambda e: e["timestamp"], reverse=True
        )[:5]
```

**Graph Memory — Knowledge Graph:**

```python
# services/14-agent/src/memory/graph_memory.py 🆕
"""Graph memory — knowledge graph of vulnerabilities.
Nodes: Contract, Function, Vulnerability, Fix
Edges: HAS_FUNCTION, HAS_VULN, FIXED_BY, SIMILAR_TO
"""

class GraphMemory:
    def __init__(self):
        self.nodes: dict = {}
        self.edges: List[tuple] = []

    def add_node(self, node_id: str, node_type: str, properties: dict):
        self.nodes[node_id] = {"type": node_type, "properties": properties}

    def add_edge(self, from_id: str, to_id: str, rel: str):
        self.edges.append((from_id, to_id, rel))

    def find_similar_vulnerabilities(self, vuln_type: str) -> List:
        """Find vulnerabilities of similar type across contracts."""
        vuln_nodes = [nid for nid, n in self.nodes.items()
                      if n["type"] == "vulnerability" 
                      and n["properties"].get("pattern") == vuln_type]
        return [self.nodes[v]["properties"] for v in vuln_nodes]
```

**Integrasi AgentMemory:**

```python
# services/14-agent/src/memory/__init__.py ✏️ (enhance)
class AgentMemory:
    def __init__(self):
        self.vector = VectorMemory()
        self.episodic = EpisodicMemory()
        self.graph = GraphMemory()

    async def learn_from_case(self, case_data: dict):
        """Belajar dari case yang sudah di-close."""
        # Vector: semantic search
        await self.vector.store(MemoryEntry(
            id=case_data["case_id"],
            content=f"{case_data['description']} {case_data.get('recommendation', '')}",
            metadata={"severity": case_data['severity'], 
                      "bounty": case_data.get('bounty_amount')},
            timestamp=case_data.get('closed_at', 
                       datetime.now(timezone.utc).isoformat()),
        ))
        # Graph: vulnerability pattern
        self.graph.add_node(
            case_data["case_id"], "vulnerability",
            {"title": case_data["title"], "severity": case_data["severity"],
             "pattern": case_data.get("vulnerability_pattern", "unknown")}
        )

    async def find_similar_cases(self, description: str, limit: int = 5) -> List:
        return await self.vector.retrieve(description, limit=limit)
```

### 2.2 Agent Skill Self-Improvement Loop

File: `services/14-agent/src/skills/registry.py` (enhance)

```python
"""Skill registry dengan learning capability.
Setiap skill punya metrics: success_rate, avg_duration, improvement_log.
"""

class SkillMetrics:
    def __init__(self):
        self.execution_count: int = 0
        self.success_count: int = 0
        self.total_duration: float = 0.0
        self.error_log: List[dict] = []

    @property
    def success_rate(self) -> float:
        return self.success_count / max(self.execution_count, 1)

    def record_execution(self, success: bool, duration: float, error: str = None):
        self.execution_count += 1
        if success:
            self.success_count += 1
        self.total_duration += duration
        if error:
            self.error_log.append({
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "error": error,
            })

class SkillRegistry:
    def __init__(self):
        self._skills: dict[str, BaseSkill] = {}
        self._metrics: dict[str, SkillMetrics] = {}

    def get_underperforming_skills(self, threshold: float = 0.7) -> List[str]:
        """Return skills with success_rate below threshold."""
        return [
            name for name, m in self._metrics.items()
            if m.execution_count >= 5 and m.success_rate < threshold
        ]

    def get_improvement_recommendations(self) -> List[str]:
        """Generate recommendations based on error patterns."""
        # Analisis error log → rekomendasi perbaikan
        ...
```

### 2.3 Autonomous Daemon (Auto-Hunt Mode)

File baru: `services/14-agent/src/daemon.py`

```python
"""Autonomous daemon — 24/7 auto-hunt mode.
Tanpa intervensi user, agent:
1. Polling Immunefi untuk program baru
2. Prioritize kontrak bernilai tinggi
3. Run pipeline penuh
4. Notify jika menemukan TP

Siklus hidup:
    SLEEP → CHECK_IMMUNEFI → PRIORITIZE → PIPELINE → NOTIFY → SLEEP
"""

class AutonomousDaemon:
    def __init__(self, agent_memory: AgentMemory):
        self.memory = agent_memory
        self.is_running = False
        self.cycle_count = 0
        self.last_cycle = None

    async def run_cycle(self):
        """Satu siklus autonomous hunting."""
        self.cycle_count += 1
        self.last_cycle = datetime.now(timezone.utc)
        
        # 1. CHECK: Program baru dari Immunefi
        new_programs = await self._check_immunefi_updates()
        if not new_programs:
            log.info("daemon.no_new_programs", cycle=self.cycle_count)
            return

        # 2. PRIORITIZE: Berdasarkan bounty + similarity
        targets = await self._prioritize_targets(new_programs)
        
        # 3. PIPELINE: Scan kontrak paling bernilai
        for target in targets[:3]:  # Max 3 per cycle
            await self._run_pipeline(target)

    async def _prioritize_targets(self, programs: List[dict]) -> List[dict]:
        """Prioritize berdasarkan: bounty, similarity dengan case sukses, complexity."""
        scored = []
        for prog in programs:
            # Cari case sukses serupa dari memory
            similar = await self.memory.find_similar_cases(
                f"{prog['name']} {prog.get('description', '')}", limit=3
            )
            similarity_score = len(similar) / 3.0
            
            bounty = prog.get("max_bounty", 0)
            if isinstance(bounty, str):
                bounty = float(bounty.replace("$", "").replace(",", ""))
            
            scored.append({
                **prog,
                "priority_score": (bounty / 10000) * 0.6 + similarity_score * 0.4,
                "similar_cases": similar,
            })
        
        return sorted(scored, key=lambda x: x["priority_score"], reverse=True)
```

### 2.4 Feedback Loop Integration

File baru: `services/14-agent/src/learning/feedback.py`

```python
"""Feedback loop — belajar dari TP/FP user feedback.

Alur:
1. User mark finding sebagai TP atau FP
2. Feedback disimpan di memory
3. Agent adjust priority scoring berdasarkan pola
4. Pattern baru otomatis terdeteksi
"""

class FeedbackLearner:
    def __init__(self, memory: AgentMemory):
        self.memory = memory
        
    async def process_feedback(self, feedback: dict):
        """Process user feedback dan update learning."""
        if feedback["type"] == "FP":
            # False Positive — jangan ulangi
            await self.memory.vector.store(MemoryEntry(
                id=f"fp-{feedback['finding_id']}",
                content=f"FALSE POSITIVE: {feedback['description']}",
                metadata={"type": "fp_pattern", "severity": "ignored"},
                timestamp=datetime.now(timezone.utc).isoformat(),
            ))
            # Update graph: kurangi bobot pattern ini
            self.memory.graph.add_node(
                feedback["finding_id"], "fp_pattern",
                {"pattern": feedback.get("pattern"), "scanner": feedback.get("scanner")}
            )
        elif feedback["type"] == "TP":
            # True Positive — prioritaskan pattern ini
            await self.memory.episodic.store_episode({
                "id": f"tp-{feedback['finding_id']}",
                "type": "successful_finding",
                "contract": feedback.get("contract"),
                "vulnerability": feedback.get("vulnerability"),
                "bounty": feedback.get("bounty_amount"),
            })
```

### 2.5 Daemon API Endpoints

File: `services/14-agent/app.py` (enhance)

```python
# Endpoints baru:

@router.post("/daemon/start")
async def daemon_start(interval: int = 3600):
    """Start autonomous daemon dengan interval detik."""

@router.post("/daemon/stop")
async def daemon_stop():
    """Stop autonomous daemon."""

@router.get("/daemon/status")
async def daemon_status():
    """Get daemon status: running, cycle_count, last_cycle, targets_found."""

@router.get("/memory/search")
async def memory_search(query: str, limit: int = 5):
    """Semantic search di agent memory."""

@router.post("/feedback")
async def submit_feedback(feedback: dict):
    """Submit TP/FP feedback untuk agent learning."""

@router.get("/learning/stats")
async def learning_stats():
    """Get learning metrics: skills success rate, patterns detected, memory usage."""
```

### 2.6 Dashboard: Agent Intelligence Page

File baru: `services/15-dashboard/frontend/src/pages/AgentIntelligence.tsx`

Halaman untuk memonitor agent:
1. **Daemon Status** — running/idle, cycle count, last scan
2. **Memory Browser** — vector index size, recent episodes, graph visualization
3. **Skill Performance** — success rate per skill, improvement recommendations
4. **Feedback Log** — history TP/FP dari user
5. **Learning Progress** — patterns discovered over time

---

## 3. Struktur File

```
services/14-agent/src/
├── memory/
│   ├── __init__.py                    # ✏️ Enhanced AgentMemory
│   ├── base.py                        # 🆕 Base memory interface
│   ├── vector_store.py                # 🆕 Vector memory (semantic)
│   ├── episodic.py                    # 🆕 Episodic memory (experience)
│   └── graph_memory.py               # 🆕 Graph memory (knowledge graph)
├── daemon.py                          # 🆕 Autonomous daemon
├── learning/
│   ├── __init__.py                    # 🆕 Package init
│   └── feedback.py                    # 🆕 Feedback loop learner
├── skills/
│   └── registry.py                    # ✏️ + SkillMetrics, improvement loop
├── agent.py                           # ✏️ + Memory integration
├── app.py                             # ✏️ + Daemon + memory + feedback endpoints

services/15-dashboard/frontend/src/
├── App.tsx                            # ✏️ + /agent-intelligence route
├── pages/
│   └── AgentIntelligence.tsx           # 🆕 Agent monitoring dashboard

services/14-agent/requirements.txt     # ✏️ + sentence-transformers, numpy
```

---

## 4. Task List

| # | Task | File | Estimasi | Prioritas |
|---|------|------|----------|-----------|
| T1 | Base memory interface | `14-agent/src/memory/base.py` | 10 min | P0 |
| T2 | Vector memory implementation | `14-agent/src/memory/vector_store.py` | 25 min | P0 |
| T3 | Episodic memory implementation | `14-agent/src/memory/episodic.py` | 20 min | P0 |
| T4 | Graph memory implementation | `14-agent/src/memory/graph_memory.py` | 25 min | P0 |
| T5 | AgentMemory integration | `14-agent/src/memory/__init__.py` | 15 min | P0 |
| T6 | Integrasi memory ke AgentLoop | `14-agent/src/agent.py` | 20 min | P0 |
| T7 | Skill Metrics & improvement loop | `14-agent/src/skills/registry.py` | 20 min | P1 |
| T8 | Autonomous daemon | `14-agent/src/daemon.py` | 40 min | P1 |
| T9 | Feedback loop learner | `14-agent/src/learning/feedback.py` | 25 min | P1 |
| T10 | Daemon API endpoints | `14-agent/app.py` | 20 min | P1 |
| T11 | Memory search endpoint | `14-agent/app.py` | 10 min | P1 |
| T12 | Feedback endpoint | `14-agent/app.py` | 10 min | P1 |
| T13 | Agent Intelligence dashboard page | `frontend/src/pages/AgentIntelligence.tsx` | 30 min | P2 |
| T14 | Learning stats endpoint | `14-agent/app.py` | 10 min | P2 |
| T15 | Tambah dependencies (sentence-transformers) | `14-agent/requirements.txt` | 5 min | P0 |
| | **Total** | | **~285 menit** | |

---

## 5. Quality Gate

| Dimensi | Target | Cara Ukur |
|---------|--------|-----------|
| Correctness | 90% | Memory store & retrieve berfungsi, daemon cycle sukses |
| Performance | 85% | Vector search < 500ms untuk 1000 entries |
| Security | 85% | Memory data tidak expose via API tanpa filter |
| Maintainability | 90% | Memory interface abstraction, daemon terisolasi dari pipeline |
| Completeness | 100% | Agent bisa belajar dari case, auto-hunt, dan improve skills |
| Alignment | 100% | Terintegrasi dengan Case Management (Agenda 05) & Pipeline |

---

## 6. Risiko & Mitigasi

| Risiko | Likelihood | Dampak | Mitigasi |
|--------|-----------|--------|----------|
| sentence-transformers model besar (~500MB) | Tinggi | Docker image size | Download on first use, cache di volume |
| Vector search O(n) tanpa index | Sedang | Slow dengan banyak entries | ANN index (faiss) opsional untuk >10k entries |
| Daemon consume resource 24/7 | Sedang | Laptop panas | Configurable interval + resource governor |
| Memory data hilang setelah restart | Tinggi | Learning lost | Persist ke JSON file di volume setiap N entries |
| Feedback loop overfit | Rendah | Agent terlalu bias ke pola lama | Decay factor: bobot lama berkurang seiring waktu |

---

*Dibuat: 2026-05-20 | Status: OPEN | Dependensi: Agenda 05, 10*
