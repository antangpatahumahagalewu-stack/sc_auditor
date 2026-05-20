"""Skill Registry — mendaftarkan, menemukan, dan melacak skill."""

from __future__ import annotations

import time
from typing import Any

import structlog

from src.skills.base import BaseSkill
from src.models import SkillDefinition, SkillResult

log = structlog.get_logger()


class SkillCallMetrics:
    """Metrics untuk satu skill — tracking penggunaan & performa."""

    def __init__(self, skill_name: str) -> None:
        self.skill_name = skill_name
        self.call_count: int = 0
        self.success_count: int = 0
        self.error_count: int = 0
        self.total_duration_ms: float = 0.0
        self.last_called: float = 0.0
        self.last_error: str | None = None
        self.recent_calls: list[dict[str, Any]] = []  # max 20

    def record_call(
        self, duration_ms: float, success: bool, error: str | None = None
    ) -> None:
        self.call_count += 1
        self.total_duration_ms += duration_ms
        self.last_called = time.time()

        if success:
            self.success_count += 1
        else:
            self.error_count += 1
            self.last_error = error

        self.recent_calls.append({
            "timestamp": time.time(),
            "duration_ms": round(duration_ms, 1),
            "success": success,
            "error": error,
        })
        if len(self.recent_calls) > 20:
            self.recent_calls.pop(0)

    @property
    def avg_duration_ms(self) -> float:
        if self.call_count == 0:
            return 0.0
        return round(self.total_duration_ms / self.call_count, 1)

    @property
    def success_rate(self) -> float:
        if self.call_count == 0:
            return 1.0
        return round(self.success_count / self.call_count, 2)

    def to_dict(self) -> dict[str, Any]:
        return {
            "skill_name": self.skill_name,
            "call_count": self.call_count,
            "success_count": self.success_count,
            "error_count": self.error_count,
            "success_rate": self.success_rate,
            "avg_duration_ms": self.avg_duration_ms,
            "last_called": self.last_called,
            "last_error": self.last_error,
        }


class SkillRegistry:
    """Registry untuk semua skill yang tersedia.

    Agent menggunakan registry ini untuk:
    1. Menemukan skill berdasarkan nama
    2. Mendapatkan daftar skill untuk LLM prompt
    3. Memanggil skill dengan parameter
    4. Melacak metrics penggunaan skill
    """

    def __init__(self) -> None:
        self._skills: dict[str, BaseSkill] = {}
        self._metrics: dict[str, SkillCallMetrics] = {}
        log.info("skill_registry_initialized")

    def register(self, skill: BaseSkill) -> None:
        """Daftarkan satu skill.

        Args:
            skill: Instance skill yang akan didaftarkan
        """
        if skill.name in self._skills:
            log.warning("skill_overwrite", name=skill.name)
        self._skills[skill.name] = skill
        self._metrics[skill.name] = SkillCallMetrics(skill.name)
        log.info("skill_registered", name=skill.name)

    def get(self, name: str) -> BaseSkill | None:
        return self._skills.get(name)

    def list_skills(self) -> list[SkillDefinition]:
        """Dapatkan daftar semua skill untuk LLM prompt."""
        return [s.get_definition() for s in self._skills.values()]

    def format_for_prompt(self) -> str:
        """Format skill descriptions untuk system prompt LLM."""
        parts: list[str] = []
        for skill in self._skills.values():
            params_desc = []
            for param_name, param_info in skill.parameters.items():
                required = "(required)" if param_info.get("required") else "(optional)"
                ptype = param_info.get("type", "string")
                desc = param_info.get("description", "")
                params_desc.append(f"    - {param_name} ({ptype}) {required}: {desc}")

            params_str = "\n".join(params_desc) if params_desc else "    (no parameters)"

            # Tambah metrics ke prompt
            metrics = self._metrics.get(skill.name)
            metrics_str = ""
            if metrics and metrics.call_count > 0:
                metrics_str = (
                    f" [called {metrics.call_count}x, "
                    f"{metrics.success_rate*100:.0f}% success, "
                    f"avg {metrics.avg_duration_ms:.0f}ms]"
                )

            parts.append(
                f"- {skill.name}{metrics_str}: {skill.description}\n{params_str}"
            )

        return "\n\n".join(parts)

    @property
    def count(self) -> int:
        return len(self._skills)

    async def execute(self, name: str, **kwargs: Any) -> SkillResult:
        """Execute skill by name dengan metrics tracking.

        Args:
            name: Skill name
            **kwargs: Arguments to pass

        Returns:
            SkillResult
        """
        skill = self.get(name)
        if skill is None:
            return SkillResult(success=False, error=f"Skill '{name}' not found")

        import time
        t0 = time.monotonic()
        result = await skill.execute(**kwargs)
        duration = (time.monotonic() - t0) * 1000

        # Record metrics
        metrics = self._metrics.get(name)
        if metrics:
            metrics.record_call(
                duration_ms=duration,
                success=result.success,
                error=result.error,
            )

        return result

    # ── Metrics ──────────────────────────────────────────────

    def get_metrics(self, name: str) -> dict[str, Any] | None:
        """Dapatkan metrics untuk satu skill."""
        metrics = self._metrics.get(name)
        if metrics is None:
            return None
        return metrics.to_dict()

    def get_all_metrics(self) -> list[dict[str, Any]]:
        """Dapatkan metrics semua skill."""
        return [m.to_dict() for m in self._metrics.values()]

    def get_top_skills(self, n: int = 5) -> list[dict[str, Any]]:
        """Dapatkan N skill paling sering dipanggil."""
        sorted_metrics = sorted(
            self._metrics.values(),
            key=lambda m: m.call_count,
            reverse=True,
        )
        return [m.to_dict() for m in sorted_metrics[:n]]

    def get_failing_skills(self) -> list[dict[str, Any]]:
        """Dapatkan skill dengan error rate > 20%."""
        return [
            m.to_dict()
            for m in self._metrics.values()
            if m.call_count > 2 and m.success_rate < 0.8
        ]
