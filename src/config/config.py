from pathlib import Path
import os
from dotenv import load_dotenv

load_dotenv()

PROJECT_ROOT = Path(__file__).parent.parent.parent

# print(PROJECT_ROOT)
PROMPTS_DIT = PROJECT_ROOT / "prompts"

DEFAULT_WORK_DIR = PROJECT_ROOT / "workspace"

AGENT_NAME = "AgCamp Coding Agent"

MAX_MODEL_CALLS_PER_RUN = int(os.getenv("MAX_MODEL_CALLS_PER_RUN", "10"))

MAX_READ_BYTES = int(os.getenv("MAX_READ_BYTES", "1000000"))


def hitl_enabled() -> bool:
    return os.getenv("HITL_ENABLED", "true").lower() in ["1", "true", "yes"]


def get_work_dir() -> Path:
    override = os.getenv("WORK_DIR", "").strip()

    if override:
        return Path(override).expanduser().resolve()

    return DEFAULT_WORK_DIR.resolve()


# print(type(DEFAULT_WORK_DIR.resolve()))
