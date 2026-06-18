"""Load credentials and define constants."""

from __future__ import annotations
import os
import yaml
from dotenv import load_dotenv

load_dotenv()

# ── YAML config ──────────────────────────────────────────────────────────────
_cfg_path = os.path.join(os.path.dirname(__file__), "..", "agent_config.yaml")
with open(_cfg_path) as _f:
    _cfg = yaml.safe_load(_f)

BAND_OWNER_HANDLE: str = _cfg["band_owner_handle"]
BAND_AGENTS: dict = _cfg            # full config used by Agent.from_config()


def agent_handle(agent_name: str) -> str:
    """Build the Band @mention handle for an agent.

    Format: @<owner>/<agent-name>
    If this doesn't match what Band resolves, inspect tools.get_participants()
    output and update accordingly.
    """
    band_name = _cfg[agent_name]["band_name"]
    return f"@{BAND_OWNER_HANDLE}/{band_name}"


# ── LLM providers ────────────────────────────────────────────────────────────
FEATHERLESS_KEY: str = os.environ["FEATHERLESS_API_KEY"]
FEATHERLESS_BASE: str = "https://api.featherless.ai/v1"

AIML_KEY: str = os.environ["AIML_API_KEY"]
AIML_BASE: str = "https://api.aimlapi.com/v1"

# Model IDs verified against Featherless dashboard and AIML API docs
MODELS: dict = {
    "triage":     {"base_url": FEATHERLESS_BASE, "key": FEATHERLESS_KEY, "model": "Qwen/Qwen3.6-27B"},
    "research":   {"base_url": FEATHERLESS_BASE, "key": FEATHERLESS_KEY, "model": "Qwen/Qwen3.6-27B"},
    "drafting":   {"base_url": AIML_BASE,        "key": AIML_KEY,        "model": "deepseek/deepseek-v4-flash"},
    "qa":         {"base_url": AIML_BASE,        "key": AIML_KEY,        "model": "deepseek/deepseek-v4-flash"},
    "escalation": {"base_url": FEATHERLESS_BASE, "key": FEATHERLESS_KEY, "model": "deepseek-ai/DeepSeek-V4-Flash"},
}

# ── Pipeline constants ────────────────────────────────────────────────────────
MONITOR_POLL_INTERVAL: int = 30     # seconds between review checks
QA_MAX_REVISIONS: int = 2
QA_APPROVAL_THRESHOLD: int = 75

PLATFORM_LIMITS: dict[str, int] = {
    "google": 4096,
    "yelp": 5000,
    "tripadvisor": 3000,
}
