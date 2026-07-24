"""Paquete de prompts del sistema RAG.

Cada constante vive en su propio módulo. Este ``__init__`` reexporta
todas las plantillas para ``from app.llm.prompts import ...``.
"""

from app.llm.prompts.conversation import CONVERSATION_PROMPT
from app.llm.prompts.conversation_summary import CONVERSATION_SUMMARY_PROMPT
from app.llm.prompts.memory_request import MEMORY_REQUEST_PROMPT
from app.llm.prompts.out_of_scope import OUT_OF_SCOPE_PROMPT
from app.llm.prompts.rag_system import RAG_SYSTEM_PROMPT
from app.llm.prompts.role_rules_admin import ROLE_RULES_ADMIN
from app.llm.prompts.role_rules_client import ROLE_RULES_CLIENT
from app.llm.prompts.scheduling_fallback import SCHEDULING_FALLBACK_PROMPT
from app.llm.prompts.supabase_rag import SUPABASE_RAG_PROMPT
from app.llm.prompts.tool_augmented_rag import TOOL_AUGMENTED_RAG_PROMPT
from app.llm.prompts.tool_final_user_nudge import TOOL_FINAL_USER_NUDGE
from app.llm.prompts.tool_mode_rules_all import TOOL_MODE_RULES_ALL
from app.llm.prompts.tool_mode_rules_none import TOOL_MODE_RULES_NONE
from app.llm.prompts.tool_mode_rules_scheduling import TOOL_MODE_RULES_SCHEDULING

__all__ = [
    "CONVERSATION_PROMPT",
    "CONVERSATION_SUMMARY_PROMPT",
    "MEMORY_REQUEST_PROMPT",
    "OUT_OF_SCOPE_PROMPT",
    "RAG_SYSTEM_PROMPT",
    "ROLE_RULES_ADMIN",
    "ROLE_RULES_CLIENT",
    "SCHEDULING_FALLBACK_PROMPT",
    "SUPABASE_RAG_PROMPT",
    "TOOL_AUGMENTED_RAG_PROMPT",
    "TOOL_FINAL_USER_NUDGE",
    "TOOL_MODE_RULES_ALL",
    "TOOL_MODE_RULES_NONE",
    "TOOL_MODE_RULES_SCHEDULING",
]
