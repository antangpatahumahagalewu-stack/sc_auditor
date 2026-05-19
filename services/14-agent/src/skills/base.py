"""Base class for all Agent Skills."""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any

import structlog

from src.models import SkillDefinition, SkillResult

log = structlog.get_logger()


class BaseSkill(ABC):
    """Abstract base untuk semua skill agent.

    Setiap skill adalah kemampuan yang bisa dipanggil agent
    untuk melakukan satu tugas spesifik.
    """

    @property
    @abstractmethod
    def name(self) -> str:
        """Nama unik skill (digunakan agent untuk memanggil)."""
        ...

    @property
    @abstractmethod
    def description(self) -> str:
        """Deskripsi skill (untuk LLM agent prompt)."""
        ...

    @property
    @abstractmethod
    def parameters(self) -> dict[str, Any]:
        """Parameter yang dibutuhkan skill (JSON Schema format)."""
        ...

    def get_definition(self) -> SkillDefinition:
        return SkillDefinition(
            name=self.name,
            description=self.description,
            parameters=self.parameters,
        )

    async def execute(self, **kwargs: Any) -> SkillResult:
        """Eksekusi skill dengan parameter yang diberikan.

        Args:
            **kwargs: Parameter sesuai self.parameters

        Returns:
            SkillResult dengan output atau error
        """
        import time
        start = time.monotonic()
        try:
            log.info("skill_executing", skill=self.name, params=kwargs)
            output = await self.run(**kwargs)
            duration = (time.monotonic() - start) * 1000
            log.info("skill_completed", skill=self.name, duration_ms=f"{duration:.0f}")
            return SkillResult(success=True, output=output, duration_ms=duration)
        except Exception as exc:
            duration = (time.monotonic() - start) * 1000
            log.error("skill_failed", skill=self.name, error=str(exc))
            return SkillResult(
                success=False,
                error=str(exc),
                duration_ms=duration,
            )

    @abstractmethod
    async def run(self, **kwargs: Any) -> Any:
        """Implementasi skill — harus di-override oleh subclass.

        Args:
            **kwargs: Parameter yang sudah divalidasi

        Returns:
            Output dari skill (dict, list, string, dll)
        """
        ...
