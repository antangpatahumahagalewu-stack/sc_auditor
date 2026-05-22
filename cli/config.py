"""Local CLI configuration — ~/.vyper/config.yml

Stores:
  - Orchestrator URL
  - Service URLs (override defaults)
  - Output preferences
  - Docker compose project path
"""

from __future__ import annotations

import os
import yaml
from pathlib import Path
from typing import Any, Dict, Optional

# ── Defaults ─────────────────────────────────────────────────────

DEFAULT_CONFIG: Dict[str, Any] = {
    # Service URLs (Docker Compose host-side ports)
    "orchestrator_url": "http://localhost:8009",
    "scanner_url": "http://localhost:8003",
    "exploit_url": "http://localhost:8006",
    "reporter_url": "http://localhost:8007",
    # "dashboard_url": "http://localhost:8000",  # 15-dashboard has been removed
    "notifier_url": "http://localhost:8008",
    "source_url": "http://localhost:8002",
    "immunefi_url": "http://localhost:8001",

    # Docker compose project directory
    "project_dir": "",  # auto-detected if empty

    # Output preferences
    "output_format": "rich",  # rich | json | text
    "color": True,
    "show_progress": True,

    # Docker compose config
    "compose_file": "docker-compose.yml",
    "project_name": "sc_auditor",

    # ── LLM API Keys (disimpan lokal, tidak di-commit) ──────────────
    # Provider utama
    "openai_key": "",
    "anthropic_key": "",
    "deepseek_key": "",
    "google_key": "",
    "xai_key": "",

    # Provider komunitas & agregator
    "openrouter_key": "",
    "openrouter_referer": "",       # identifier untuk OpenRouter
    "nous_key": "",
    "novita_key": "",

    # Provider China & Asia
    "alibaba_key": "",
    "xiaomi_key": "",
    "tencent_key": "",
    "zai_key": "",
    "kimi_key": "",
    "stepfun_key": "",
    "minimax_key": "",

    # Provider open-source / cloud
    "ollama_cloud_key": "",
    "huggingface_key": "",
    "nvidia_key": "",
    "arcee_key": "",
    "gmi_key": "",
    "kilocode_key": "",

    # OpenCode resmi
    "opencode_zen_key": "",
    "opencode_go_key": "",

    # Cloud enterprise
    "bedrock_key": "",              # AWS Bedrock (IAM fallback)
    "azure_foundry_key": "",
    "ai_gateway_key": "",

    # ── LLM Models ─────────────────────────────────────────────────
    # Provider utama
    "openai_model": "gpt-4o",
    "anthropic_model": "claude-sonnet-4-6",
    "deepseek_model": "deepseek-chat",
    "google_model": "gemini-2.0-flash",
    "xai_model": "grok-2",

    # Provider komunitas & agregator
    "openrouter_model": "anthropic/claude-sonnet-4.6",
    "nous_model": "hermes-3-405b",
    "novita_model": "moonshotai/kimi-k2.5",

    # Provider China & Asia
    "alibaba_model": "qwen3.6-plus",
    "xiaomi_model": "mimo-v2.5-pro",
    "tencent_model": "hy3-preview",
    "zai_model": "glm-5.1",
    "kimi_model": "kimi-k2.6",
    "stepfun_model": "step-3.5-flash",
    "minimax_model": "MiniMax-M2.7",

    # Provider open-source / cloud
    "ollama_cloud_model": "qwen3.6-plus",
    "huggingface_model": "moonshotai/Kimi-K2.5",
    "nvidia_model": "nvidia/nemotron-3-super-120b-a12b",
    "arcee_model": "trinity-large-thinking",
    "gmi_model": "zai-org/GLM-5.1-FP8",
    "kilocode_model": "anthropic/claude-sonnet-4.6",

    # OpenCode resmi
    "opencode_zen_model": "kimi-k2.5",
    "opencode_go_model": "kimi-k2.6",

    # Cloud enterprise
    "bedrock_model": "us.anthropic.claude-sonnet-4-6",
    "azure_foundry_model": "",
    "ai_gateway_model": "moonshotai/kimi-k2.6",

    # ── Custom Base URLs (untuk self-hosted / OpenAI-compatible proxy) ──
    "openai_base_url": "",
    "anthropic_base_url": "",
    "deepseek_base_url": "",
    "google_base_url": "",
    "xai_base_url": "",
    "openrouter_base_url": "",
    "nous_base_url": "",
    "novita_base_url": "",
    "alibaba_base_url": "",
    "xiaomi_base_url": "",
    "tencent_base_url": "",
    "zai_base_url": "",
    "kimi_base_url": "",
    "stepfun_base_url": "",
    "minimax_base_url": "",
    "ollama_cloud_base_url": "",
    "huggingface_base_url": "",
    "nvidia_base_url": "",
    "arcee_base_url": "",
    "gmi_base_url": "",
    "kilocode_base_url": "",
    "opencode_zen_base_url": "",
    "opencode_go_base_url": "",
    "bedrock_base_url": "",
    "azure_foundry_base_url": "",
    "ai_gateway_base_url": "",
}

DEFAULT_CONFIG_PATH = Path.home() / ".vyper" / "config.yml"


# ── Config Manager ───────────────────────────────────────────────

class Config:
    """Manages local CLI configuration stored in ~/.vyper/config.yml."""

    def __init__(self, path: Path = DEFAULT_CONFIG_PATH) -> None:
        self._path = path
        self._data: Dict[str, Any] = dict(DEFAULT_CONFIG)
        self._load()

    # ── Loading ─────────────────────────────────────────────────

    def _load(self) -> None:
        """Load config from YAML file, merging with defaults."""
        if not self._path.exists():
            return
        try:
            raw = self._path.read_text("utf-8")
            parsed = yaml.safe_load(raw)
            if isinstance(parsed, dict):
                # Merge: override defaults with user values
                self._data = {**DEFAULT_CONFIG, **parsed}
        except (yaml.YAMLError, OSError) as exc:
            print(f"[yellow]Warning:[/] Could not load config {self._path}: {exc}")

    def save(self) -> None:
        """Persist current config to YAML file."""
        self._path.parent.mkdir(parents=True, exist_ok=True)
        self._path.write_text(yaml.dump(self._data, default_flow_style=False), "utf-8")

    # ── Access ──────────────────────────────────────────────────

    def get(self, key: str, default: Any = None) -> Any:
        return self._data.get(key, default)

    def set(self, key: str, value: Any) -> None:
        self._data[key] = value

    @property
    def data(self) -> Dict[str, Any]:
        return dict(self._data)

    @property
    def project_dir(self) -> Path:
        """Auto-detect project directory if not configured."""
        pd = self.get("project_dir", "")
        if pd:
            return Path(pd)
        # Walk up from cwd looking for docker-compose.yml
        cwd = Path.cwd()
        for parent in [cwd, *cwd.parents]:
            compose = parent / "docker-compose.yml"
            if compose.exists():
                return parent
        return cwd

    # ── Display ─────────────────────────────────────────────────

    def as_table(self) -> list[tuple[str, str]]:
        """Return config as list of (key, value) tuples for display."""
        rows = []
        for k, v in sorted(self._data.items()):
            if k == "project_dir" and not v:
                v = str(self.project_dir)
            rows.append((k, str(v)))
        return rows


# ── Singleton ────────────────────────────────────────────────────

_config_instance: Config | None = None


def get_config() -> Config:
    """Return global Config singleton."""
    global _config_instance
    if _config_instance is None:
        _config_instance = Config()
    return _config_instance
