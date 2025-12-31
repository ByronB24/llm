
from typing import Tuple
from src.config import CONTENT_CLEAN_PROMPTS, INFO_EXTRACTION_PROMPTS, CHAT_PROMPTS


class ContentCleanPrompt:
    SYSTEM_PROMPT:Tuple[str] = CONTENT_CLEAN_PROMPTS.system
    USER_PROMPT:Tuple[str] = CONTENT_CLEAN_PROMPTS.user
    
class InformationExtractionPrompt:
    SYSTEM_PROMPT:Tuple[str] = INFO_EXTRACTION_PROMPTS.system
    USER_PROMPT:Tuple[str] = INFO_EXTRACTION_PROMPTS.user
       
class ChatPrompts:
    SYSTEM_PROMPT:str = CHAT_PROMPTS.system
