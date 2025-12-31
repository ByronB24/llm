from pathlib import Path
import yaml
import os
import re
from dataclasses import dataclass

ROOT_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "..")) 
CONFG_PATH = os.path.join(ROOT_DIR, "config.yaml") 
CLEAN_CONTENT_PROMPT_DIR_PATH = os.path.join(ROOT_DIR, "prompts/content_clean.yaml")
INFO_EXTRACTION_PROMPT_DIR_PATH = os.path.join(ROOT_DIR, "prompts/information_extraction.yaml")
CHAT_PROMPT_DIR_PATH = os.path.join(ROOT_DIR, "prompts/chat.yaml")

#Open Config file
with open(CONFG_PATH, "r", encoding="utf-8") as file:
    CONFIG = yaml.safe_load(file) or {}

OPEN_AI_VARS_CONFIG = CONFIG.get("OPEN_AI_VARS",{})

#Helpers to load prompt files (YAML with system/user keys or legacy text with SYSTEM/USER markers)
def _load_prompt(path: str, expect_user_block: bool = True) -> tuple[str, str]:
    ext = Path(path).suffix.lower()
    if ext in {".yaml", ".yml"}:
        data = yaml.safe_load(Path(path).read_text(encoding="utf-8")) or {}
        system = data.get("system", "")
        user = data.get("user", "") if expect_user_block else ""
        return system.strip(), user.strip()

    raw_prompt = Path(path).read_text(encoding="utf-8")
    user_match = re.search(r"^USER\s*:\s*\|?\s*", raw_prompt, flags=re.IGNORECASE | re.MULTILINE)
    if not user_match:
        raise ValueError(f"USER block not found in prompt file: {path}")
    system_block = raw_prompt[:user_match.start()]
    user_block = raw_prompt[user_match.end():]
    system = re.sub(r"^SYSTEM\s*:\s*\|?\s*", "", system_block, flags=re.IGNORECASE).strip()
    user = re.sub(r"^USER\s*:\s*\|?\s*", "", user_block, flags=re.IGNORECASE).strip()
    return system, user


_CLEAN_CONTENT_SYSTEM_BLOCK, _CLEAN_CONTENT_USER_BLOCK = _load_prompt(CLEAN_CONTENT_PROMPT_DIR_PATH)
_INFO_EXTRACTION_SYSTEM_BLOCK, _INFO_EXTRACTION_USER_BLOCK = _load_prompt(INFO_EXTRACTION_PROMPT_DIR_PATH)
_CHAT_SYSTEM_BLOCK, _ = _load_prompt(CHAT_PROMPT_DIR_PATH, expect_user_block=False)

@dataclass
class OpenAIVars:
    open_ai_model:str = ""

@dataclass
class CleanPrompts:
    system:str = ""
    user: str = ""

@dataclass
class InformationExtractionPrompts:
    system:str = ""
    user: str = ""

@dataclass
class ChatPrompts:
    system:str = ""

OPENAIVARS = OpenAIVars(open_ai_model = OPEN_AI_VARS_CONFIG.get("OPENAI_MODEL"))

CONTENT_CLEAN_PROMPTS = CleanPrompts(system=_CLEAN_CONTENT_SYSTEM_BLOCK,
                                     user=_CLEAN_CONTENT_USER_BLOCK)

INFO_EXTRACTION_PROMPTS = InformationExtractionPrompts(system=_INFO_EXTRACTION_SYSTEM_BLOCK,
                                                       user =  _INFO_EXTRACTION_USER_BLOCK
                                                       )

CHAT_PROMPTS = ChatPrompts(system=_CHAT_SYSTEM_BLOCK)
