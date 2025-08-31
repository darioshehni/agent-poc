from pathlib import Path
from enum import Enum


class OpenAIModels(Enum):
    GPT_4O = "gpt-4o"
    GPT_4O_MINI = "gpt-4o-mini"
    GPT_5_NANO = "gpt-5-nano"
    GPT_5 = "gpt-5"

DOSSIER_BASE_DIR = Path("../../data/dossiers")
