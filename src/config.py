import configparser
import yaml
import os
from dataclasses import dataclass

ROOT_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "..")) 
CONFG_PATH = os.path.join(ROOT_DIR, "config.yaml") 


with open(CONFG_PATH, "r", encoding="utf-8") as file:
    config = yaml.safe_load(file) or {}


OPEN_AI_VARS_CONFIG = config.get("OPEN_AI_VARS",{})

@dataclass
class OpenAIVars:
    open_ai_model:str = ""

OPENAIVARS = OpenAIVars(open_ai_model = OPEN_AI_VARS_CONFIG.get("OPENAI_MODEL"))
