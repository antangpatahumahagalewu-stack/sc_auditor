"""Skill Registry — mendaftarkan dan menemukan skill."""

from __future__ import annotations

from typing import Any

import structlog

from src.skills.base import BaseSkill
from src.models import SkillDefinition

log = structlog.get_logger()


class SkillRegistry:
    """Registry untuk semua skill yang tersedia.

    Agent menggunakan registry ini untuk:
    1. Menemukan skill berdasarkan nama
    2. Mendapatkan daftar skill untuk LLM prompt
    3. Memanggil skill dengan parameter
    """

    def __init__(self) -> None:
        self._skills: dict[str, BaseSkill] = {}
        log.info("skill_registry_initialized")

    def register(self, skill: BaseSkill) -> None:
        """Daftarkan satu skill.

        Args:
            skill: Instance skill yang akan didaftarkan
        """
        if skill.name in self._skills:
            log.warning("skill_overwrite", name=skill.name)
        self._skills[skill.name] = skill
        log.info("skill_registered", name=skill.name)

    def get(self, name: str) -> BaseSkill | None:
        """Cari skill berdasarkan nama."""
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

            parts.append(
                f"- {skill.name}: {skill.description}\n{params_str}"
            )

        return "\n\n".join(parts)

    @property
    def count(self) -> int:
        return len(self._skills)

    async def execute(self, name: str, **kwargs: Any) -> Any:
        """Execute skill by name.

        Args:
            name: Skill name
            **kwargs: Arguments to pass

        Returns:
            SkillResult
        """
        skill = self.get(name)
        if skill is None:
            from src.models import SkillResult
            return SkillResult(success=False, error=f"Skill '{name}' not found")
        return await skill.execute(**kwargs)
