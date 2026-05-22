"""ChatEngine — LLM-powered pipeline chatbot for Vyper Monitor.

Multi-provider support: 27+ AI providers diadopsi dari opencode ecosystem.
Termasuk OpenAI, Anthropic, DeepSeek, Google AI, xAI (Grok), OpenRouter,
Nous Portal, NovitaAI, Alibaba/Qwen, Xiaomi MiMo, Tencent TokenHub, Z.AI/GLM,
Kimi/Moonshot, StepFun, MiniMax, Ollama Cloud, HuggingFace, NVIDIA NIM,
Arcee AI, GMI Cloud, Kilo Code, OpenCode Zen, OpenCode Go, AWS Bedrock,
Azure Foundry, Vercel AI Gateway, dan semua API OpenAI-compatible.

Key bisa diset via chat: `set openai_key sk-xxx` atau `set provider deepseek key ds-xxx`
Model bisa diganti: `set provider deepseek model deepseek-v4-pro`
Base URL bisa custom: `set provider openai base_url http://localhost:11434/v1`
Key disimpan di ~/.vyper/config.yml atau di Config Service (dashboard settings).
"""

from __future__ import annotations

import asyncio
import difflib
import re
from datetime import datetime
from typing import Any

import httpx

from cli.config import get_config, DEFAULT_CONFIG_PATH

# ── Service Ports (dari docker-compose.yml) ────────────────────

SERVICES: list[tuple[str, int]] = [
    ("01-config", 8011),
    ("02-immunefi", 8001),
    ("03-source", 8002),
    ("04-scanner", 8003),
    ("04a-scanner-slither", 8014),
    ("04b-scanner-echidna", 8015),
    ("04c-scanner-forge", 8016),
    ("04d-scanner-halmos", 8017),
    ("05-scanner-mythril", 8013),
    ("06-ai", 8004),
    ("07-classifier", 8005),
    ("08-exploit", 8006),
    ("09-reporter", 8007),
    ("10-notifier", 8008),
    ("11-orchestrator", 8009),
    ("12-webhook", 8010),
    ("13-upkeep", 8012),
    ("14-agent", 8021),  # port 8021 (hindari bentrok dengan 04a-scanner-slither di 8014)
    ("16-submission", 8018),
]

# ── Provider Registry ─────────────────────────────────────────
# Semua provider didefinisikan di sini. API format:
#   "openai"    → OpenAI Chat Completions (/v1/chat/completions) — kompatibel dengan DeepSeek, xAI, OpenRouter, dll
#   "anthropic" → Anthropic Messages API (x-api-key header)
#   "google"    → Google Gemini native API
# Terinspirasi dari opencode & hermes-agent provider catalog.

PROVIDER_CONFIG: dict[str, dict[str, Any]] = {
    # ── Provider Utama ────────────────────────────────────────────
    "openai": {
        "name": "OpenAI",
        "api_format": "openai",
        "default_model": "gpt-4o",
        "default_base_url": "https://api.openai.com/v1",
        "config_key": "openai",
        "env_key": "OPENAI_API_KEY",
    },
    "anthropic": {
        "name": "Anthropic",
        "api_format": "anthropic",
        "default_model": "claude-sonnet-4-6",
        "default_base_url": "https://api.anthropic.com/v1",
        "config_key": "anthropic",
        "env_key": "ANTHROPIC_API_KEY",
    },
    "deepseek": {
        "name": "DeepSeek",
        "api_format": "openai",
        "default_model": "deepseek-chat",
        "default_base_url": "https://api.deepseek.com/v1",
        "config_key": "deepseek",
        "env_key": "DEEPSEEK_API_KEY",
    },
    "google": {
        "name": "Google AI",
        "api_format": "google",
        "default_model": "gemini-2.0-flash",
        "default_base_url": "https://generativelanguage.googleapis.com/v1",
        "config_key": "google",
        "env_key": "GOOGLE_API_KEY",
    },
    "xai": {
        "name": "xAI (Grok)",
        "api_format": "openai",
        "default_model": "grok-2",
        "default_base_url": "https://api.x.ai/v1",
        "config_key": "xai",
        "env_key": "XAI_API_KEY",
    },

    # ── Agregator & Gateway ─────────────────────────────────────
    "openrouter": {
        "name": "OpenRouter",
        "api_format": "openai",
        "default_model": "anthropic/claude-sonnet-4.6",
        "default_base_url": "https://openrouter.ai/api/v1",
        "config_key": "openrouter",
        "env_key": "OPENROUTER_API_KEY",
    },
    "nous": {
        "name": "Nous Portal",
        "api_format": "openai",
        "default_model": "hermes-3-405b",
        "default_base_url": "https://api.nousresearch.com/v1",
        "config_key": "nous",
        "env_key": "NOUS_API_KEY",
    },
    "novita": {
        "name": "NovitaAI",
        "api_format": "openai",
        "default_model": "moonshotai/kimi-k2.5",
        "default_base_url": "https://api.novita.ai/v3/openai",
        "config_key": "novita",
        "env_key": "NOVITA_API_KEY",
    },
    "ai_gateway": {
        "name": "Vercel AI Gateway",
        "api_format": "openai",
        "default_model": "moonshotai/kimi-k2.6",
        "default_base_url": "https://gateway.ai.vercel.com/v1",
        "config_key": "ai_gateway",
        "env_key": "AI_GATEWAY_API_KEY",
    },

    # ── Provider China & Asia ────────────────────────────────────
    "alibaba": {
        "name": "Qwen Cloud (DashScope)",
        "api_format": "openai",
        "default_model": "qwen3.6-plus",
        "default_base_url": "https://dashscope-intl.aliyuncs.com/compatible-mode/v1",
        "config_key": "alibaba",
        "env_key": "ALIBABA_API_KEY",
    },
    "xiaomi": {
        "name": "Xiaomi MiMo",
        "api_format": "openai",
        "default_model": "mimo-v2.5-pro",
        "default_base_url": "https://api.mimo.xiaomi.com/v1",
        "config_key": "xiaomi",
        "env_key": "XIAOMI_API_KEY",
    },
    "tencent": {
        "name": "Tencent TokenHub",
        "api_format": "openai",
        "default_model": "hy3-preview",
        "default_base_url": "https://tokenhub.tencentmaas.com/v1",
        "config_key": "tencent",
        "env_key": "TENCENT_API_KEY",
    },
    "zai": {
        "name": "Z.AI / GLM (Zhipu)",
        "api_format": "openai",
        "default_model": "glm-5.1",
        "default_base_url": "https://open.bigmodel.cn/api/paas/v4",
        "config_key": "zai",
        "env_key": "ZAI_API_KEY",
    },
    "kimi": {
        "name": "Kimi / Moonshot",
        "api_format": "openai",
        "default_model": "kimi-k2.6",
        "default_base_url": "https://api.moonshot.cn/v1",
        "config_key": "kimi",
        "env_key": "KIMI_API_KEY",
    },
    "stepfun": {
        "name": "StepFun",
        "api_format": "openai",
        "default_model": "step-3.5-flash",
        "default_base_url": "https://api.stepfun.com/v1",
        "config_key": "stepfun",
        "env_key": "STEP_API_KEY",
    },
    "minimax": {
        "name": "MiniMax",
        "api_format": "openai",
        "default_model": "MiniMax-M2.7",
        "default_base_url": "https://api.minimax.chat/v1/text/chatcompletion_v2",
        "config_key": "minimax",
        "env_key": "MINIMAX_API_KEY",
    },

    # ── Provider Open-Source & Cloud ─────────────────────────────
    "ollama_cloud": {
        "name": "Ollama Cloud",
        "api_format": "openai",
        "default_model": "qwen3.6-plus",
        "default_base_url": "https://api.ollama.com/v1",
        "config_key": "ollama_cloud",
        "env_key": "OLLAMA_CLOUD_API_KEY",
    },
    "huggingface": {
        "name": "Hugging Face",
        "api_format": "openai",
        "default_model": "moonshotai/Kimi-K2.5",
        "default_base_url": "https://api-inference.huggingface.co/v1",
        "config_key": "huggingface",
        "env_key": "HUGGINGFACE_API_KEY",
    },
    "nvidia": {
        "name": "NVIDIA NIM",
        "api_format": "openai",
        "default_model": "nvidia/nemotron-3-super-120b-a12b",
        "default_base_url": "https://api.nvcf.nvidia.com/v1",
        "config_key": "nvidia",
        "env_key": "NVIDIA_API_KEY",
    },
    "arcee": {
        "name": "Arcee AI",
        "api_format": "openai",
        "default_model": "trinity-large-thinking",
        "default_base_url": "https://api.arcee.ai/v1",
        "config_key": "arcee",
        "env_key": "ARCEE_API_KEY",
    },
    "gmi": {
        "name": "GMI Cloud",
        "api_format": "openai",
        "default_model": "zai-org/GLM-5.1-FP8",
        "default_base_url": "https://api.gmicloud.ai/v1",
        "config_key": "gmi",
        "env_key": "GMI_API_KEY",
    },
    "kilocode": {
        "name": "Kilo Code",
        "api_format": "openai",
        "default_model": "anthropic/claude-sonnet-4.6",
        "default_base_url": "https://gateway.kilocode.ai/v1",
        "config_key": "kilocode",
        "env_key": "KILOCODE_API_KEY",
    },

    # ── OpenCode Resmi ───────────────────────────────────────────
    "opencode_zen": {
        "name": "OpenCode Zen",
        "api_format": "openai",
        "default_model": "kimi-k2.5",
        "default_base_url": "https://api.opencode.ai/v1",
        "config_key": "opencode_zen",
        "env_key": "OPENCODE_ZEN_API_KEY",
    },
    "opencode_go": {
        "name": "OpenCode Go",
        "api_format": "openai",
        "default_model": "kimi-k2.6",
        "default_base_url": "https://api.opencode.ai/v1",
        "config_key": "opencode_go",
        "env_key": "OPENCODE_GO_API_KEY",
    },

    # ── Cloud Enterprise ─────────────────────────────────────────
    "bedrock": {
        "name": "AWS Bedrock",
        "api_format": "openai",
        "default_model": "us.anthropic.claude-sonnet-4-6",
        "default_base_url": "https://bedrock-runtime.us-east-1.amazonaws.com",
        "config_key": "bedrock",
        "env_key": "AWS_ACCESS_KEY_ID",
        "note": "Membutuhkan AWS credentials (AWS_ACCESS_KEY_ID + AWS_SECRET_ACCESS_KEY)",
    },
    "azure_foundry": {
        "name": "Azure Foundry",
        "api_format": "openai",
        "default_model": "",
        "default_base_url": "",
        "config_key": "azure_foundry",
        "env_key": "AZURE_FOUNDRY_API_KEY",
        "note": "Set base_url ke endpoint Azure AI Anda",
    },
}

# ── Model Catalog ────────────────────────────────────────────
# Daftar model per provider, diadopsi dari opencode/hermes-agent.
PROVIDER_MODELS: dict[str, list[str]] = {
    "openai": [
        "gpt-5.4", "gpt-5.4-mini", "gpt-5-mini", "gpt-5.3-codex",
        "gpt-5.2-codex", "gpt-4.1", "gpt-4o", "gpt-4o-mini",
    ],
    "anthropic": [
        "claude-opus-4-7", "claude-opus-4-6", "claude-sonnet-4-6",
        "claude-opus-4-5-20251101", "claude-sonnet-4-5-20250929",
        "claude-opus-4-20250514", "claude-sonnet-4-20250514",
        "claude-haiku-4-5-20251001",
    ],
    "deepseek": [
        "deepseek-v4-pro", "deepseek-v4-flash", "deepseek-chat", "deepseek-reasoner",
    ],
    "google": [
        "gemini-3.1-pro-preview", "gemini-3-pro-preview", "gemini-3-flash-preview",
        "gemini-3.1-flash-lite-preview", "gemini-2.5-pro",
    ],
    "xai": [
        "grok-4.3", "grok-4.20-0309-reasoning", "grok-4.20-0309-non-reasoning",
        "grok-4.20-multi-agent-0309",
    ],
    "openrouter": [
        "anthropic/claude-opus-4.7", "anthropic/claude-opus-4.6",
        "anthropic/claude-sonnet-4.6", "moonshotai/kimi-k2.6",
        "openrouter/pareto-code", "qwen/qwen3.6-plus",
        "anthropic/claude-haiku-4.5", "openai/gpt-5.5", "openai/gpt-5.5-pro",
        "openai/gpt-5.4-mini", "openai/gpt-5.4-nano", "openai/gpt-5.3-codex",
        "xiaomi/mimo-v2.5-pro", "tencent/hy3-preview", "google/gemini-3.1-pro-preview",
        "google/gemini-3-flash-preview", "google/gemini-3.1-flash-lite-preview",
        "stepfun/step-3.5-flash", "minimax/minimax-m2.7", "z-ai/glm-5.1",
        "x-ai/grok-4.3", "nvidia/nemotron-3-super-120b-a12b",
        "deepseek/deepseek-v4-pro",
    ],
    "nous": [
        "anthropic/claude-opus-4.7", "anthropic/claude-opus-4.6",
        "anthropic/claude-sonnet-4.6", "moonshotai/kimi-k2.6",
        "qwen/qwen3.6-plus", "openai/gpt-5.5", "xiaomi/mimo-v2.5-pro",
        "google/gemini-3.1-pro-preview", "deepseek/deepseek-v4-pro",
    ],
    "novita": [
        "moonshotai/kimi-k2.5", "minimax/minimax-m2.7", "zai-org/glm-5",
        "deepseek/deepseek-v3-0324", "deepseek/deepseek-r1-0528",
        "qwen/qwen3-235b-a22b-fp8",
    ],
    "alibaba": [
        "qwen3.6-plus", "kimi-k2.5", "qwen3.5-plus", "qwen3-coder-plus",
        "qwen3-coder-next", "glm-5", "glm-4.7", "MiniMax-M2.5",
    ],
    "xiaomi": [
        "mimo-v2.5-pro", "mimo-v2.5", "mimo-v2-pro", "mimo-v2-omni", "mimo-v2-flash",
    ],
    "tencent": ["hy3-preview"],
    "zai": [
        "glm-5.1", "glm-5", "glm-5v-turbo", "glm-5-turbo",
        "glm-4.7", "glm-4.5", "glm-4.5-flash",
    ],
    "kimi": [
        "kimi-k2.6", "kimi-k2.5", "kimi-for-coding", "kimi-k2-thinking",
        "kimi-k2-thinking-turbo", "kimi-k2-turbo-preview", "kimi-k2-0905-preview",
    ],
    "stepfun": ["step-3.5-flash", "step-3.5-flash-2603"],
    "minimax": ["MiniMax-M2.7", "MiniMax-M2.5", "MiniMax-M2.1", "MiniMax-M2"],
    "ollama_cloud": ["qwen3.6-plus", "qwen3.5-plus"],
    "huggingface": [
        "moonshotai/Kimi-K2.5", "Qwen/Qwen3.5-397B-A17B",
        "deepseek-ai/DeepSeek-V3.2", "MiniMaxAI/MiniMax-M2.5",
        "zai-org/GLM-5", "moonshotai/Kimi-K2.6",
    ],
    "nvidia": [
        "nvidia/nemotron-3-super-120b-a12b", "nvidia/nemotron-3-nano-30b-a3b",
        "qwen/qwen3.5-397b-a17b", "deepseek-ai/deepseek-v3.2",
        "moonshotai/kimi-k2.6", "z-ai/glm5",
    ],
    "arcee": ["trinity-large-thinking", "trinity-large-preview", "trinity-mini"],
    "gmi": [
        "zai-org/GLM-5.1-FP8", "deepseek-ai/DeepSeek-V3.2",
        "moonshotai/Kimi-K2.5", "anthropic/claude-sonnet-4.6", "openai/gpt-5.4",
    ],
    "kilocode": [
        "anthropic/claude-opus-4.6", "anthropic/claude-sonnet-4.6",
        "openai/gpt-5.4", "google/gemini-3-pro-preview", "google/gemini-3-flash-preview",
    ],
    "opencode_zen": [
        "kimi-k2.5", "gpt-5.4-pro", "gpt-5.4", "gpt-5.3-codex",
        "claude-opus-4-6", "claude-sonnet-4-6", "claude-haiku-4-5",
        "gemini-3.1-pro", "minimax-m2.7", "glm-5", "kimi-k2-thinking",
    ],
    "opencode_go": [
        "kimi-k2.6", "kimi-k2.5", "glm-5.1", "mimo-v2.5-pro",
        "minimax-m2.7", "qwen3.6-plus",
    ],
    "bedrock": [
        "us.anthropic.claude-sonnet-4-6", "us.anthropic.claude-opus-4-6-v1",
        "us.anthropic.claude-haiku-4-5-20251001-v1:0",
        "us.amazon.nova-pro-v1:0", "us.amazon.nova-lite-v1:0",
        "deepseek.v3.2", "us.meta.llama4-maverick-17b-instruct-v1:0",
    ],
    "azure_foundry": [],
    "ai_gateway": [
        "moonshotai/kimi-k2.6", "alibaba/qwen3.6-plus", "zai/glm-5.1",
        "anthropic/claude-sonnet-4.6", "anthropic/claude-opus-4.7",
        "openai/gpt-5.4", "google/gemini-3.1-pro-preview",
        "xai/grok-4.20-reasoning",
    ],
}

# ── Provider Aliases ─────────────────────────────────────────
# Memungkinkan pengguna mengetik nama alternatif untuk provider yang sama.
PROVIDER_ALIASES: dict[str, str] = {
    "claude": "anthropic", "claude-code": "anthropic",
    "google": "gemini", "google-ai-studio": "gemini", "gemini": "google",
    "grok": "xai", "x-ai": "xai", "x.ai": "xai",
    "deep-seek": "deepseek",
    "or": "openrouter", "open-router": "openrouter",
    "nousresearch": "nous", "nous-portal": "nous",
    "novita-ai": "novita", "novitaai": "novita",
    "glm": "zai", "z-ai": "zai", "z.ai": "zai", "zhipu": "zai",
    "kimi": "kimi", "moonshot": "kimi",
    "step": "stepfun", "stepfun-coding-plan": "stepfun",
    "qwen": "alibaba", "dashscope": "alibaba", "aliyun": "alibaba",
    "mimo": "xiaomi", "xiaomi-mimo": "xiaomi",
    "tencent": "tencent", "tokenhub": "tencent",
    "nim": "nvidia", "nvidia-nim": "nvidia", "nemotron": "nvidia",
    "hf": "huggingface", "hugging-face": "huggingface",
    "arcee-ai": "arcee", "arceeai": "arcee",
    "gmi-cloud": "gmi", "gmicloud": "gmi",
    "kilo": "kilocode", "kilo-code": "kilocode", "kilo-gateway": "kilocode",
    "zen": "opencode-zen", "opencode": "opencode-zen",
    "go": "opencode-go", "opencode-go-sub": "opencode-go",
    "aws": "bedrock", "aws-bedrock": "bedrock", "amazon-bedrock": "bedrock",
    "azure": "azure_foundry", "azure-ai": "azure_foundry",
    "vercel": "ai_gateway", "vercel-ai-gateway": "ai_gateway", "aigateway": "ai_gateway",
    "ollama": "ollama_cloud", "ollama-cloud": "ollama_cloud",
    "minimax-china": "minimax", "minimax_cn": "minimax",
}

# Config Service key mapping (dashboard settings → internal provider id)
# Dashboard menyimpan key sebagai `provider_{id}_api_key`, `provider_{id}_base_url`
_CS_PROVIDER_KEYS: list[tuple[str, str, str]] = [
    ("openai",        "provider_openai_api_key",         "provider_openai_base_url"),
    ("anthropic",     "provider_anthropic_api_key",      "provider_anthropic_base_url"),
    ("google",        "provider_google_api_key",         "provider_google_base_url"),
    ("deepseek",      "provider_deepseek_api_key",       "provider_deepseek_base_url"),
    ("xai",           "provider_xai_api_key",            "provider_xai_base_url"),
    ("openrouter",    "provider_openrouter_api_key",     "provider_openrouter_base_url"),
    ("nous",          "provider_nous_api_key",           "provider_nous_base_url"),
    ("novita",        "provider_novita_api_key",         "provider_novita_base_url"),
    ("alibaba",       "provider_alibaba_api_key",        "provider_alibaba_base_url"),
    ("xiaomi",        "provider_xiaomi_api_key",         "provider_xiaomi_base_url"),
    ("tencent",       "provider_tencent_api_key",        "provider_tencent_base_url"),
    ("zai",           "provider_zai_api_key",            "provider_zai_base_url"),
    ("kimi",          "provider_kimi_api_key",           "provider_kimi_base_url"),
    ("stepfun",       "provider_stepfun_api_key",        "provider_stepfun_base_url"),
    ("minimax",       "provider_minimax_api_key",        "provider_minimax_base_url"),
    ("ollama_cloud",  "provider_ollama_cloud_api_key",   "provider_ollama_cloud_base_url"),
    ("huggingface",   "provider_huggingface_api_key",    "provider_huggingface_base_url"),
    ("nvidia",        "provider_nvidia_api_key",         "provider_nvidia_base_url"),
    ("arcee",         "provider_arcee_api_key",          "provider_arcee_base_url"),
    ("gmi",           "provider_gmi_api_key",            "provider_gmi_base_url"),
    ("kilocode",      "provider_kilocode_api_key",       "provider_kilocode_base_url"),
    ("opencode_zen",  "provider_opencode_zen_api_key",   "provider_opencode_zen_base_url"),
    ("opencode_go",   "provider_opencode_go_api_key",    "provider_opencode_go_base_url"),
    ("bedrock",       "provider_bedrock_api_key",        "provider_bedrock_base_url"),
    ("azure_foundry", "provider_azure_foundry_api_key",  "provider_azure_foundry_base_url"),
    ("ai_gateway",    "provider_ai_gateway_api_key",     "provider_ai_gateway_base_url"),
]

# Model use-case keys dari Settings dashboard
_MODEL_USE_CASE_KEYS = [
    "ai_analysis_model",
    "ai_classification_model",
    "ai_exploit_model",
]


# Provider model ID parser — model ID seperti "claude-opus-4-7"
# atau "deepseek-v4-pro" — prefix sebelum "-" pertama adalah provider
def _parse_model_id(model_id: str) -> tuple[str, str]:
    """Parse model ID like 'claude-opus-4-7' → ('anthropic', 'claude-opus-4-7')."""
    model_id = model_id.strip()
    prefix = model_id.split("-")[0] if "-" in model_id else model_id
    prefix_lower = prefix.lower()
    # Map common model prefixes to provider IDs
    prefix_map = {
        # OpenAI
        "gpt": "openai", "openai": "openai", "o1": "openai", "o3": "openai",
        # Anthropic
        "claude": "anthropic", "anthropic": "anthropic",
        # Google
        "gemini": "google", "google": "google",
        # DeepSeek
        "deepseek": "deepseek",
        # xAI
        "grok": "xai", "xai": "xai",
        # OpenRouter (format: provider/model)
        "anthropic/": "openrouter", "openai/": "openrouter",
        "google/": "openrouter", "deepseek/": "openrouter",
        "x-ai/": "openrouter", "xai/": "openrouter",
        "moonshotai/": "openrouter", "qwen/": "openrouter",
        "z-ai/": "openrouter", "minimax/": "openrouter",
        "nvidia/": "openrouter", "xiaomi/": "openrouter",
        "stepfun/": "openrouter", "tencent/": "openrouter",
        # Zhipu / GLM
        "glm": "zai",
        # Kimi / Moonshot
        "kimi": "kimi", "moonshot": "kimi",
        # Alibaba / Qwen
        "qwen": "alibaba",
        # Xiaomi MiMo
        "mimo": "xiaomi",
        # StepFun
        "step": "stepfun",
        # MiniMax
        "minimax": "minimax",
        # NVIDIA
        "nvidia/": "nvidia", "nemotron": "nvidia",
        # HuggingFace
        "moonshotai/": "huggingface",
        # AWS Bedrock
        "us.anthropic.": "bedrock", "us.amazon.": "bedrock",
        "us.meta.": "bedrock",
        # Vercel AI Gateway
        "alibaba/": "ai_gateway", "zai/": "ai_gateway",
        "xai/": "ai_gateway",
    }
    provider = prefix_map.get(prefix_lower, prefix_map.get(prefix, prefix))
    return provider, model_id


SYSTEM_PROMPT = """Kamu adalah VYPER AI Assistant — asisten pipeline smart contract security auditing.
Kamu membantu tim VYPER memonitor dan mengelola pipeline audit.

**Pipeline VYPER** (8 stage):
1. IMMUNEFI_SYNC → Sync 234+ bug bounty programs
2. SOURCE_FETCH → Fetch source code dari GitHub/Etherscan/Sourcify
3. SCANNING → 5 scanner: Slither (static), Echidna (fuzzing), Forge (build), Halmos (symbolic), Mythril (symbolic sidecar)
4. AI_ANALYSIS → LLM TP/FP classification via AI
5. CLASSIFICATION → TP/FP/TN/FN categorization
6. EXPLOIT_TEST → Generate PoC via Anvil Docker engine
7. REPORT_GENERATION → Immunefi-ready + full audit report
8. NOTIFICATION → Discord / Telegram / Email / Desktop

Pipeline diorkestrasi oleh 11-orchestrator dengan state machine 11 state.
Total 20 microservices.

**AI Provider yang didukung** (27 provider):
- Utama: OpenAI, Anthropic, DeepSeek, Google AI, xAI (Grok)
- Agregator: OpenRouter (100+ models), Nous Portal, NovitaAI, Vercel AI Gateway
- China/Asia: Qwen Cloud (Alibaba), Xiaomi MiMo, Tencent TokenHub, Z.AI/GLM, Kimi/Moonshot, StepFun, MiniMax
- Open-Source/Cloud: Ollama Cloud, HuggingFace, NVIDIA NIM, Arcee AI, GMI Cloud, Kilo Code
- OpenCode Resmi: OpenCode Zen, OpenCode Go
- Enterprise: AWS Bedrock, Azure Foundry

Semua provider dengan format "openai" support custom base_url — bisa pakai
Ollama lokal, vLLM, OpenRouter, Groq, Together AI, dll.

{context}

Jawab dalam Bahasa Indonesia. Ramah, informatif, dan to the point.
Gunakan data pipeline real-time yang diberikan di context untuk jawaban akurat.
"""


# ── Intent Detection ──────────────────────────────────────────


class Intent:
    HEALTH = "service_health"
    STATS = "audit_stats"
    PIPELINE = "pipeline_info"
    AUDITS = "recent_audits"
    FINDINGS = "findings_info"
    QUEUE = "queue_info"
    CONFIG = "config_info"
    SET_KEY = "set_key"
    SET_PROVIDER = "set_provider"
    LIST_PROVIDERS = "list_providers"
    LIST_MODELS = "list_models"
    HELP = "help"
    GREETING = "greeting"
    GENERAL = "general"


_INTENT_PATTERNS: list[tuple[list[str], str]] = [
    (["health", "sehat", "hidup", "alive", "up", "running", "service", "status service",
      "down", "mati", "service apa", "daftar service", "semua service"], Intent.HEALTH),
    (["stats", "statistik", "statistic", "total audit", "completed", "selesai",
      "failed", "gagal", "findings", "temuan", "success rate", "persentase"], Intent.STATS),
    (["pipeline", "proses", "alur", "tahapan", "stage", "bagaimana", "cara kerja",
      "jelaskan", "proses audit"], Intent.PIPELINE),
    (["audit", "recent", "terakhir", "history", "riwayat", "daftar audit",
      "audit terbaru"], Intent.AUDITS),
    (["finding", "temuan", "vulnerability", "vuln", "critical", "high",
      "severity", "bug"], Intent.FINDINGS),
    (["queue", "antrian", "pending", "menunggu", "stack"], Intent.QUEUE),
    (["config", "konfigurasi", "setting", "pengaturan", "rpc", "endpoint"], Intent.CONFIG),
    (["help", "bantuan", "? ", "menu", "command", "perintah"], Intent.HELP),
    (["halo", "hai", "hi", "hello", "hey", "pagi", "siang", "sore", "malam"], Intent.GREETING),
    (["provider", "ganti provider", "pindah", "switch"], Intent.LIST_PROVIDERS),
    (["model", "models list", "daftar model", "model apa"], Intent.LIST_MODELS),
]

# Regex untuk perintah `set <provider_id>_key <key>` atau `set provider <id> key <key>`
# Auto-generate dari PROVIDER_CONFIG.keys()
_ALL_PROVIDER_KEYS = "|".join(PROVIDER_CONFIG.keys())
_SET_KEY_RE = re.compile(
    rf"^set\s+(?:"
    rf"({_ALL_PROVIDER_KEYS})_key\s+(\S+)"                      # set openai_key sk-xxx
    rf"|"
    rf"provider\s+(\w+)\s+key\s+(\S+)"                          # set provider deepseek key ds-xxx
    rf")",
    re.IGNORECASE,
)

# Regex untuk perintah `set provider <id> model <model>`
_SET_MODEL_RE = re.compile(
    r"^set\s+provider\s+(\w+)\s+model\s+(\S+)",
    re.IGNORECASE,
)

# Regex untuk perintah `set provider <id> base_url <url>`
_SET_BASE_URL_RE = re.compile(
    r"^set\s+provider\s+(\w+)\s+base_url\s+(\S+)",
    re.IGNORECASE,
)


def detect_intent(text: str) -> str:
    lower = text.lower().strip()
    if _SET_KEY_RE.match(text.strip()):
        return Intent.SET_KEY
    for keywords, intent in _INTENT_PATTERNS:
        if any(kw in lower for kw in keywords):
            return intent
    return Intent.GENERAL


# ── Context Gatherer ──────────────────────────────────────────


class PipelineContext:
    """Gathers real-time pipeline context from all services."""

    def __init__(self) -> None:
        self.cfg = get_config()
        self._http: httpx.AsyncClient | None = None
        self.orchestrator_url = self.cfg.get("orchestrator_url", "http://localhost:8009")
        self.config_url = "http://localhost:8011"

    @property
    def http(self) -> httpx.AsyncClient:
        if self._http is None or self._http.is_closed:
            self._http = httpx.AsyncClient(
                timeout=httpx.Timeout(5.0, connect=2.0),
                limits=httpx.Limits(max_keepalive_connections=20, max_connections=20),
            )
        return self._http

    async def close(self) -> None:
        if self._http and not self._http.is_closed:
            await self._http.aclose()

    async def get_health(self) -> list[dict]:
        async def _check(name: str, port: int) -> dict:
            try:
                resp = await self.http.get(f"http://localhost:{port}/health")
                if resp.status_code == 200:
                    body = resp.json()
                    inner = body.get("data", body) if isinstance(body, dict) else body
                    uptime = inner.get("uptime_seconds") or inner.get("uptime", 0)
                    if isinstance(uptime, dict):
                        uptime = 0
                    return {"name": name, "port": port, "alive": True, "uptime": uptime}
            except Exception:
                pass
            return {"name": name, "port": port, "alive": False, "uptime": 0}
        tasks = [_check(n, p) for n, p in SERVICES]
        return await asyncio.gather(*tasks)

    async def get_stats(self) -> dict:
        try:
            resp = await self.http.get(f"{self.orchestrator_url}/stats", timeout=5.0)
            if resp.status_code == 200:
                data = resp.json()
                if isinstance(data, dict) and "data" in data:
                    return data["data"]
                return data
        except Exception:
            pass
        return {}

    async def get_audits(self, limit: int = 10) -> list[dict]:
        try:
            resp = await self.http.get(
                f"{self.orchestrator_url}/audits", params={"limit": limit}, timeout=5.0,
            )
            if resp.status_code == 200:
                data = resp.json()
                if isinstance(data, dict) and "data" in data:
                    return data["data"]
                if isinstance(data, list):
                    return data
        except Exception:
            pass
        return []

    async def get_queue(self) -> int:
        try:
            resp = await self.http.get(
                f"{self.orchestrator_url}/queue", params={"limit": 1}, timeout=5.0,
            )
            if resp.status_code == 200:
                data = resp.json()
                if isinstance(data, dict) and "data" in data:
                    items = data["data"]
                    return len(items) if isinstance(items, list) else 0
        except Exception:
            pass
        return 0

    async def get_config(self) -> dict:
        try:
            resp = await self.http.get(f"{self.config_url}/config/", timeout=5.0)
            if resp.status_code == 200:
                data = resp.json()
                if isinstance(data, dict) and "data" in data:
                    return data["data"]
        except Exception:
            pass
        return {}

    async def get_llm_keys(self) -> dict[str, str]:
        """Baca semua provider API keys + base_urls + model dari Config Service.

        Mengembalikan dict dengan key seperti 'openai_key', 'openai_base_url',
        'openai_model', 'deepseek_key', dll.
        """
        cs_config = await self.get_config()
        result: dict[str, str] = {}

        for provider_id, api_key_field, base_url_field in _CS_PROVIDER_KEYS:
            key = cs_config.get(api_key_field, "")
            if key:
                result[f"{provider_id}_key"] = key
            base_url = cs_config.get(base_url_field, "")
            if base_url:
                result[f"{provider_id}_base_url"] = base_url

        # Baca model dari use-case settings (ambil yang pertama tersedia)
        for use_case_key in _MODEL_USE_CASE_KEYS:
            model_id = cs_config.get(use_case_key, "")
            if model_id:
                provider_from_model, _ = _parse_model_id(model_id)
                result[f"{provider_from_model}_model"] = model_id

        # Fallback model defaults jika tidak ada dari dashboard
        for pid, pconf in PROVIDER_CONFIG.items():
            if f"{pid}_model" not in result:
                result[f"{pid}_model"] = pconf["default_model"]

        return result

    async def gather_all(self) -> dict:
        health_task = self.get_health()
        stats_task = self.get_stats()
        audits_task = self.get_audits(limit=5)
        queue_task = self.get_queue()
        config_task = self.get_config()
        health, stats, audits, queue, cfg = await asyncio.gather(
            health_task, stats_task, audits_task, queue_task, config_task,
        )
        return {"health": health, "stats": stats, "audits": audits, "queue": queue, "config": cfg}


# ── Chat Engine ───────────────────────────────────────────────


class ChatEngine:
    """LLM-powered pipeline chatbot dengan multi-provider support.

    Mendukung OpenAI, Anthropic, DeepSeek, Google AI, xAI (Grok),
    dan semua API OpenAI-compatible (OpenRouter, Groq, Together AI, dll).
    """

    def __init__(self) -> None:
        self.ctx = PipelineContext()
        self._provider_id: str | None = None
        self._api_key: str | None = None
        self._model: str | None = None
        self._base_url: str | None = None
        self._ready = False

    # ── Initialization ───────────────────────────────────────

    async def initialize(self) -> str:
        """Cek API key dari local config → Config Service.

        Priority:
          1. Local config (~/.vyper/config.yml)
          2. Config Service (dashboard settings)
          3. Prompt user jika tidak ada
        """
        # 1. Cari provider pertama yang punya key di local config
        local_cfg = get_config()
        found = self._try_load_from_local(local_cfg)

        if not found:
            # 2. Coba dari Config Service (dashboard settings)
            try:
                found = await self._try_load_from_config_service(local_cfg)
            except Exception:
                pass

        if found:
            self._ready = True
            return self._welcome_msg()

        # 3. Tidak ada key sama sekali
        return self._no_key_msg()

    def _try_load_from_local(self, cfg: Any) -> bool:
        """Coba muat provider dari local config.

        Mencari semua provider yang terdefinisi, ambil yang pertama
        punya API key.
        """
        for pid, pconf in PROVIDER_CONFIG.items():
            key = cfg.get(f"{pid}_key", "") or cfg.get(f"{pconf['config_key']}_key", "")
            if key:
                self._provider_id = pid
                self._api_key = key
                self._model = cfg.get(f"{pid}_model") or pconf["default_model"]
                self._base_url = cfg.get(f"{pid}_base_url") or pconf.get("default_base_url", "")
                return True
        return False

    async def _try_load_from_config_service(self, local_cfg: Any) -> bool:
        """Coba muat provider dari Config Service (dashboard settings)."""
        keys = await self.ctx.get_llm_keys()

        for pid, pconf in PROVIDER_CONFIG.items():
            key = keys.get(f"{pid}_key", "")
            if key:
                self._provider_id = pid
                self._api_key = key
                self._model = keys.get(f"{pid}_model") or pconf["default_model"]
                self._base_url = keys.get(f"{pid}_base_url") or pconf.get("default_base_url", "")

                # Simpan ke local config untuk sesi berikutnya
                local_cfg.set(f"{pid}_key", key)
                if self._model:
                    local_cfg.set(f"{pid}_model", self._model)
                local_cfg.save()

                return True

        # Alternatif: cek use-case model dari dashboard
        # Kalau ada ai_analysis_model = "deepseek-v4-pro", trigger deepseek
        for use_case_key in _MODEL_USE_CASE_KEYS:
            model_id = keys.get(use_case_key.replace("_model", "_model"), "")
            if not model_id:
                model_id = keys.get(use_case_key, "")
            if model_id:
                provider_from_model, _ = _parse_model_id(model_id)
                pconf = PROVIDER_CONFIG.get(provider_from_model)
                if pconf:
                    model_key = f"{provider_from_model}_key"
                    if keys.get(model_key):
                        self._provider_id = provider_from_model
                        self._api_key = keys[model_key]
                        self._model = model_id
                        self._base_url = keys.get(f"{provider_from_model}_base_url") or pconf.get("default_base_url", "")
                        return True

        return False

    # ── Messages ─────────────────────────────────────────────

    def _welcome_msg(self) -> str:
        pconf = PROVIDER_CONFIG.get(self._provider_id or "", {})
        provider_name = pconf.get("name", self._provider_id or "?")
        model_display = self._model or "?"
        return (
            f"🤖 Halo! Saya **VYPER AI Assistant**\n"
            f"   Provider: **{provider_name}** | Model: **{model_display}**\n\n"
            "Saya bisa menjawab pertanyaan seputar pipeline audit:\n"
            "• **Status service** — service apa yang hidup/mati\n"
            "• **Pipeline audit** — proses & tahapan audit\n"
            "• **Statistik** — jumlah audit, completed, failed\n"
            "• **Findings** — temuan & severity\n"
            "• **Antrian** — pipeline queue\n"
            "• **Pertanyaan umum** — tanya apapun tentang pipeline\n\n"
            f"💡 *Didukung {len(PROVIDER_CONFIG)} AI provider. Ketik `providers` untuk lihat semua.*\n"
            "   Langsung tanya aja! 🚀\n"
            "   Ketik `help` untuk lihat semua perintah."
        )

    def _no_key_msg(self) -> str:
        # Group providers by category for compact display
        main_providers = [p for p in PROVIDER_CONFIG if p in ("openai","anthropic","deepseek","google","xai")]
        agg_providers = [p for p in PROVIDER_CONFIG if p in ("openrouter","nous","novita","ai_gateway")]
        cn_providers = [p for p in PROVIDER_CONFIG if p in ("alibaba","xiaomi","tencent","zai","kimi","stepfun","minimax")]
        oss_providers = [p for p in PROVIDER_CONFIG if p in ("ollama_cloud","huggingface","nvidia","arcee","gmi","kilocode")]
        oc_providers = [p for p in PROVIDER_CONFIG if p in ("opencode_zen","opencode_go")]
        enterprise = [p for p in PROVIDER_CONFIG if p in ("bedrock","azure_foundry")]

        sections = {
            "Utama": main_providers,
            "Agregator": agg_providers,
            "China/Asia": cn_providers,
            "Open-Source/Cloud": oss_providers,
            "OpenCode Resmi": oc_providers,
            "Enterprise": enterprise,
        }
        lines = ["🔑 **API Key tidak ditemukan!**\n",
                  f"Saya butuh API key dari salah satu dari {len(PROVIDER_CONFIG)} provider:\n"]
        for section_name, provider_list in sections.items():
            if provider_list:
                items = " • ".join(f"`set {p}_key <key>`" for p in provider_list)
                lines.append(f"\n**{section_name}:** {items}")
        lines.append(
            "\n\nContoh:\n"
            "`set openai_key sk-xxxxxxxxxxxx`\n"
            "`set deepseek_key ds-xxxxxxxxxxxx`\n"
            "`set google_key AIzaxxxxxxxxxxxx`\n"
            "`set openrouter_key sk-or-xxx`\n\n"
            "Key akan disimpan di `~/.vyper/config.yml`.\n"
            "Atau set via Dashboard → Settings, lalu restart chat: `vyper chat`"
        )
        return "\n".join(lines)

    # ── Answer ───────────────────────────────────────────────

    async def answer(self, question: str) -> str:
        """Jawab pertanyaan — pakai LLM untuk general questions."""

        # ── Handle SET commands ──────────────────────────────

        # set openai_key sk-xxx / set provider deepseek key ds-xxx
        m = _SET_KEY_RE.match(question.strip())
        if m:
            # Format: set openai_key sk-xxx
            if m.group(1) and m.group(2):
                provider_id = m.group(1)  # already just "openai" from capture group
                key_value = m.group(2)
            # Format: set provider deepseek key ds-xxx (group 3=provider, group 4=key)
            elif m.group(3) and m.group(4):
                provider_id = m.group(3).lower()
                key_value = m.group(4)
            else:
                return self._no_key_msg()

            return await self._handle_set_key(provider_id, key_value)

        # Fallback: set <alias>_key <key> — misal "set claude_key sk-ant-xxx"
        # Resolve melalui PROVIDER_ALIASES
        alias_key_match = re.match(
            r"^set\s+(\w+)_key\s+(\S+)", question.strip(), re.IGNORECASE
        )
        if alias_key_match:
            raw_id = alias_key_match.group(1).lower()
            key_value = alias_key_match.group(2)
            # Coba resolve via alias
            resolved = PROVIDER_ALIASES.get(raw_id, raw_id)
            if resolved in PROVIDER_CONFIG:
                return await self._handle_set_key(resolved, key_value)
            # Mungkin user salah ketik — kasih saran
            close_matches = difflib.get_close_matches(raw_id, list(PROVIDER_CONFIG.keys()), n=3, cutoff=0.5)
            close_matches += [a for a, t in PROVIDER_ALIASES.items() if difflib.get_close_matches(raw_id, [a], n=1, cutoff=0.6)]
            suggestion = f"\nMungkin maksud Anda: {', '.join(close_matches)}" if close_matches else ""
            return (
                f"❌ Provider **{raw_id}** tidak dikenal.{suggestion}\n\n"
                f"Ketik `providers` untuk lihat semua provider.\n"
                f"Atau `set provider <id> key <key>`"
            )

        # set provider deepseek model deepseek-v4-pro
        m = _SET_MODEL_RE.match(question.strip())
        if m:
            provider_id = m.group(1).lower()
            model_value = m.group(2)
            return self._handle_set_model(provider_id, model_value)

        # set provider deepseek base_url http://localhost:11434/v1
        m = _SET_BASE_URL_RE.match(question.strip())
        if m:
            provider_id = m.group(1).lower()
            url_value = m.group(2)
            return self._handle_set_base_url(provider_id, url_value)

        # ── Handle other intents ─────────────────────────────

        intent = detect_intent(question)

        if intent == Intent.HELP:
            return self._help_text()
        elif intent == Intent.GREETING:
            return self._greeting_text()
        elif intent == Intent.LIST_PROVIDERS:
            return self._list_providers_text()
        elif intent == Intent.LIST_MODELS:
            # Cari provider dari pertanyaan: "models openai", "model deepseek", dll
            lower_q = question.lower()
            for pid in PROVIDER_MODELS:
                if pid in lower_q:
                    models = PROVIDER_MODELS[pid]
                    pname = PROVIDER_CONFIG.get(pid, {}).get("name", pid)
                    model_list = "\n".join(f"  • `{m}`" for m in models)
                    return (
                        f"**📋 Model untuk {pname}**\n\n"
                        f"{model_list}\n\n"
                        f"Total {len(models)} model.\n"
                        f"Gunakan `set provider {pid} model <nama>` untuk ganti model."
                    )
            # Fallback: tampilkan semua provider yang punya model
            lines = ["**📋 Model per Provider:**\n"]
            for pid, models in PROVIDER_MODELS.items():
                if models:
                    pname = PROVIDER_CONFIG.get(pid, {}).get("name", pid)
                    lines.append(f"• **{pname}** ({len(models)} model): `{models[0]}` ... `{models[-1]}`")
            lines.append("\n💡 Ketik `models <nama_provider>` untuk detail.")
            return "\n".join(lines)

        # Cek ketersediaan LLM
        if not self._ready or not self._api_key:
            return self._no_key_msg()

        # Gather pipeline context
        context = await self.ctx.gather_all()

        # Semua intent lain → LLM dengan pipeline context
        return await self._answer_with_llm(question, context)

    # ── SET Command Handlers ─────────────────────────────────

    async def _handle_set_key(self, provider_id: str, key_value: str) -> str:
        """Handle `set <provider>_key <key>` atau `set provider <id> key <key>`."""
        # Resolve alias terlebih dahulu
        resolved = PROVIDER_ALIASES.get(provider_id.lower(), provider_id.lower())
        pconf = PROVIDER_CONFIG.get(resolved)
        if not pconf:
            # Coba langsung
            pconf = PROVIDER_CONFIG.get(provider_id)
        if not pconf:
            available = ", ".join(PROVIDER_CONFIG.keys())
            return (
                f"❌ Provider **{provider_id}** tidak dikenal.\n\n"
                f"Provider tersedia ({len(PROVIDER_CONFIG)}):\n{available}\n\n"
                "Gunakan:\n"
                f"`set <provider>_key <key>`\n"
                "Contoh: `set deepseek_key ds-xxx`\n"
                "Atau lihat semua: `providers`"
            )
        provider_id = resolved

        cfg = get_config()
        cfg.set(f"{provider_id}_key", key_value)
        cfg.save()

        self._provider_id = provider_id
        self._api_key = key_value
        self._model = cfg.get(f"{provider_id}_model") or pconf["default_model"]
        self._base_url = cfg.get(f"{provider_id}_base_url") or pconf.get("default_base_url", "")
        self._ready = True

        return (
            f"✅ Key **{pconf['name']}** berhasil disimpan di `~/.vyper/config.yml`!\n\n"
            f"{self._welcome_msg()}"
        )

    def _handle_set_model(self, provider_id: str, model_value: str) -> str:
        """Handle `set provider <id> model <model>`."""
        resolved = PROVIDER_ALIASES.get(provider_id.lower(), provider_id.lower())
        pconf = PROVIDER_CONFIG.get(resolved)
        if not pconf:
            return f"❌ Provider **{provider_id}** tidak dikenal."
        provider_id = resolved

        cfg = get_config()
        cfg.set(f"{provider_id}_model", model_value)
        cfg.save()

        if self._provider_id == provider_id:
            self._model = model_value

        return (
            f"✅ Model **{pconf['name']}** → `{model_value}` tersimpan!\n\n"
            f"Gunakan `set {provider_id}_key <key>` untuk aktifkan."
        )

    def _handle_set_base_url(self, provider_id: str, url_value: str) -> str:
        """Handle `set provider <id> base_url <url>`.

        Berguna untuk:
        - Self-hosted LLM (Ollama: http://localhost:11434/v1)
        - OpenRouter (https://openrouter.ai/api/v1)
        - Groq (https://api.groq.com/openai/v1)
        - Together AI (https://api.together.xyz/v1)
        - vLLM (http://localhost:8000/v1)
        - LocalAI (http://localhost:8080/v1)
        """
        resolved = PROVIDER_ALIASES.get(provider_id.lower(), provider_id.lower())
        pconf = PROVIDER_CONFIG.get(resolved)
        if not pconf:
            return f"❌ Provider **{provider_id}** tidak dikenal."
        provider_id = resolved

        cfg = get_config()
        cfg.set(f"{provider_id}_base_url", url_value)
        cfg.save()

        if self._provider_id == provider_id:
            self._base_url = url_value

        return (
            f"✅ Base URL **{pconf['name']}** → `{url_value}` tersimpan!\n\n"
            f"Gunakan `set {provider_id}_key <key>` untuk aktifkan."
        )

    # ── LLM Call ─────────────────────────────────────────────

    async def _answer_with_llm(self, question: str, context: dict) -> str:
        """Jawab dengan LLM + pipeline context real-time."""
        try:
            health = context.get("health", [])
            stats = context.get("stats", {})
            audits = context.get("audits", [])

            alive = sum(1 for s in health if s.get("alive"))
            dead_list = [s["name"] for s in health if not s.get("alive")]

            ctx_str = (
                f"Pipeline Real-time Status:\n"
                f"- Services: {alive}/{len(health)} alive\n"
                f"- Dead services: {', '.join(dead_list) or 'none'}\n"
                f"- Total audits: {stats.get('total_audits', 0)}\n"
                f"- Completed: {stats.get('completed', 0)}\n"
                f"- Failed: {stats.get('failed', 0)}\n"
                f"- In progress: {stats.get('in_progress', 0)}\n"
                f"- Success rate: {stats.get('success_rate', 0):.1f}%\n"
                f"- Total findings: {stats.get('total_findings', 0)}\n"
                f"- TP: {stats.get('tp', 0)}, FP: {stats.get('fp', 0)}, FN: {stats.get('fn', 0)}\n"
                f"- Queue size: {context.get('queue', 0)}\n"
                f"- Recent audits: {len(audits)}\n"
            )

            if audits:
                ctx_str += "\nRecent audits:\n"
                for a in audits[:5]:
                    ctx_str += f"- {a.get('audit_id','?')[:8]}: {a.get('state','?')}\n"

            prompt = SYSTEM_PROMPT.format(context=ctx_str)

            pconf = PROVIDER_CONFIG.get(self._provider_id or "", {})
            api_format = pconf.get("api_format", "openai")

            if api_format == "anthropic":
                return await self._call_anthropic(question, prompt)
            elif api_format == "google":
                return await self._call_google(question, prompt)
            else:
                # "openai" format — default, juga untuk DeepSeek, xAI, OpenRouter, dll
                return await self._call_openai_compatible(
                    question=question,
                    system_prompt=prompt,
                    base_url=self._base_url or "https://api.openai.com/v1",
                )

        except Exception as exc:
            return (
                f"⚠️ **Gagal memproses pertanyaan:** {exc}\n\n"
                f"Coba lagi atau tanya hal lain. "
                f"Kalau error terus, cek API key dengan `set <provider>_key <key>`\n"
                f"Atau lihat provider tersedia: `providers`"
            )

    def _get_headers(self, extra_headers: dict | None = None) -> dict[str, str]:
        """Build common HTTP headers."""
        headers = {"Content-Type": "application/json"}
        if extra_headers:
            headers.update(extra_headers)
        return headers

    async def _call_openai_compatible(
        self,
        question: str,
        system_prompt: str,
        base_url: str,
    ) -> str:
        """Call any OpenAI-compatible chat completions API.

        Support: OpenAI, DeepSeek, xAI/Grok, OpenRouter, Groq,
        Together AI, Ollama, vLLM, LocalAI, dan semua API
        yang mengikuti format /v1/chat/completions.
        """
        url = f"{base_url.rstrip('/')}/chat/completions"
        headers = self._get_headers({"Authorization": f"Bearer {self._api_key}"})
        body = {
            "model": self._model or "gpt-4o",
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": question},
            ],
            "max_tokens": 2048,
            "temperature": 0.3,
        }

        client = self.ctx.http
        resp = await client.post(url, headers=headers, json=body, timeout=60.0)

        if resp.status_code == 401:
            provider_name = PROVIDER_CONFIG.get(self._provider_id or "", {}).get("name", "Provider")
            return (
                f"❌ **API Key {provider_name} tidak valid!**\n\n"
                f"Gunakan `set {self._provider_id}_key <key>` dengan key yang benar."
            )

        resp.raise_for_status()
        data = resp.json()

        # Handle berbagai format response OpenAI-compatible
        try:
            return data["choices"][0]["message"]["content"].strip()
        except (KeyError, IndexError, TypeError):
            return f"⚠️ Response tidak terduga dari API: {str(data)[:200]}"

    async def _call_anthropic(self, question: str, system_prompt: str) -> str:
        """Call Anthropic Messages API."""
        base_url = self._base_url or "https://api.anthropic.com/v1"
        url = f"{base_url.rstrip('/')}/messages"
        headers = self._get_headers({
            "x-api-key": self._api_key or "",
            "anthropic-version": "2023-06-01",
        })
        body = {
            "model": self._model or "claude-3-5-sonnet-20241022",
            "system": system_prompt,
            "messages": [{"role": "user", "content": question}],
            "max_tokens": 2048,
            "temperature": 0.3,
        }

        client = self.ctx.http
        resp = await client.post(url, headers=headers, json=body, timeout=60.0)

        if resp.status_code == 401:
            return "❌ **API Key Anthropic tidak valid!** Gunakan `set anthropic_key sk-ant-xxx` dengan key yang benar."

        resp.raise_for_status()
        data = resp.json()
        return data["content"][0]["text"].strip()

    async def _call_google(self, question: str, system_prompt: str) -> str:
        """Call Google Gemini API."""
        base_url = self._base_url or "https://generativelanguage.googleapis.com/v1"
        model = self._model or "gemini-2.0-flash"
        url = f"{base_url.rstrip('/')}/models/{model}:generateContent"

        headers = self._get_headers({"x-goog-api-key": self._api_key or ""})
        body = {
            "contents": [{
                "role": "user",
                "parts": [{"text": f"{system_prompt}\n\n{question}"}],
            }],
            "generationConfig": {
                "maxOutputTokens": 2048,
                "temperature": 0.3,
            },
        }

        client = self.ctx.http
        resp = await client.post(url, headers=headers, json=body, timeout=60.0)

        if resp.status_code in (401, 403):
            return "❌ **API Key Google tidak valid!** Gunakan `set google_key <key>` dengan key yang benar."

        resp.raise_for_status()
        data = resp.json()

        try:
            return data["candidates"][0]["content"]["parts"][0]["text"].strip()
        except (KeyError, IndexError, TypeError):
            return f"⚠️ Response tidak terduga dari Google API: {str(data)[:200]}"

    # ── Help / Info ──────────────────────────────────────────

    def _help_text(self) -> str:
        return (
            "**Yang bisa saya lakukan:**\n\n"
            "**🔑 Setup Provider**\n"
            f"Total {len(PROVIDER_CONFIG)} provider didukung.\n"
            "• `set <provider>_key <key>` — Set API key (contoh: `set deepseek_key ds-xxx`)\n"
            "• `set provider <id> model <model>` — Ganti model\n"
            "• `set provider <id> base_url <url>` — Custom endpoint\n"
            "• `providers` — Lihat semua provider & model default\n"
            "• `models <provider>` — Lihat model yang tersedia untuk provider\n\n"
            "**🔧 Self-hosted / OpenAI-compatible**\n"
            "• `set provider openai base_url http://localhost:11434/v1` — Ollama\n"
            "• `set provider openai base_url https://openrouter.ai/api/v1` — OpenRouter\n"
            "• `set provider openai base_url https://api.groq.com/openai/v1` — Groq\n"
            "• `set provider openai base_url http://localhost:8000/v1` — vLLM\n"
            "• `set provider openai model llama3-70b-8192` — Ganti model\n\n"
            "**🔍 Pipeline & Monitoring**\n"
            "• `service apa yang down?` — Status semua service\n"
            "• `statistik pipeline` — Jumlah audit, completed, failed\n"
            "• `tampilkan audit terakhir` — Daftar audit real-time\n"
            "• `bagaimana cara kerja pipeline?` — Penjelasan 8-stage\n"
            "• `total findings` — Ringkasan temuan\n"
            "• `antrian pipeline` — Queue size\n"
            "• `providers` — Lihat semua provider tersedia\n\n"
            "**💬 Pertanyaan umum** — Tanya apapun, AI akan jawab menggunakan\n"
            "   provider aktif saat ini!"
        )

    @staticmethod
    def _list_providers_text() -> str:
        # Group by category
        categories = {
            "**🌟 Provider Utama**": ["openai","anthropic","deepseek","google","xai"],
            "**🔀 Agregator & Gateway**": ["openrouter","nous","novita","ai_gateway"],
            "**🇨🇳 China & Asia**": ["alibaba","xiaomi","tencent","zai","kimi","stepfun","minimax"],
            "**💚 Open-Source & Cloud**": ["ollama_cloud","huggingface","nvidia","arcee","gmi","kilocode"],
            "**🔷 OpenCode Resmi**": ["opencode_zen","opencode_go"],
            "**🏢 Enterprise**": ["bedrock","azure_foundry"],
        }
        lines = [f"**📋 Provider Tersedia ({len(PROVIDER_CONFIG)} total):**\n"]
        for cat_title, pids in categories.items():
            entries = []
            for pid in pids:
                if pid in PROVIDER_CONFIG:
                    pconf = PROVIDER_CONFIG[pid]
                    fmt = pconf.get("api_format", "?")
                    model = pconf.get("default_model", "?")
                    url = pconf.get("default_base_url", "?")
                    alias_list = [alias for alias, target in PROVIDER_ALIASES.items() if target == pid]
                    alias_str = f"  (alias: {', '.join(alias_list[:3])})" if alias_list else ""
                    entries.append(f"  • **{pconf['name']}** (`{pid}`)\n"
                                   f"    Format: `{fmt}` | Model: `{model}`{alias_str}")
            if entries:
                lines.append(f"\n{cat_title}")
                lines.extend(entries)
        lines.append(
            "\n\n💡 *Provider dengan format `openai` bisa pakai endpoint kustom*\n"
            "   via `set provider <id> base_url <url>`\n"
            "   — Cocok untuk Ollama, vLLM, OpenRouter, Groq, dll.\n\n"
            "💡 *Gunakan alias untuk kemudahan:*\n"
            "   `set claude_key ...` = `set anthropic_key ...`\n"
            "   `set grok_key ...` = `set xai_key ...`\n"
            "   `set qwen_key ...` = `set alibaba_key ...`\n"
            "   `set hf_key ...` = `set huggingface_key ...`"
        )
        return "\n".join(lines)

    @staticmethod
    def _greeting_text() -> str:
        hour = datetime.now().hour
        if hour < 12:
            greet = "Selamat pagi"
        elif hour < 15:
            greet = "Selamat siang"
        elif hour < 18:
            greet = "Selamat sore"
        else:
            greet = "Selamat malam"

        return (
            f"{greet}! 👋\n\n"
            "Ada yang bisa saya bantu tentang pipeline VYPER?\n"
            "Ketik `help` untuk lihat daftar perintah.\n"
            "Ketik `providers` untuk lihat semua provider AI tersedia."
        )

    async def close(self) -> None:
        await self.ctx.close()
