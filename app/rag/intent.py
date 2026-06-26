import re
from enum import Enum

from app.rag.schemas import WorkingMemory


class QueryIntent(str, Enum):
    CONVERSATION = "conversation"
    AUTOMOTIVE = "automotive"
    MEMORY_REQUEST = "memory_request"
    OUT_OF_SCOPE = "out_of_scope"


_CONVERSATION_RE = re.compile(
    r"^(?:hola|buenas|buenos días|buenas tardes|buenas noches|gracias|ok|okay|sí|si|no)\b"
    r"|qué haces|que haces|cómo estás|como estas|quién eres|quien eres"
    r"|muchas gracias|adiós|adios|bye",
    re.IGNORECASE,
)

_MEMORY_RE = re.compile(
    r"qué (?:me )?pregunt|que (?:me )?pregunt"
    r"|qué (?:acabamos|hablamos)|que (?:acabamos|hablamos)"
    r"|qué recuerdas|que recuerdas"
    r"|mi (?:última|ultima) pregunta"
    r"|lo que (?:dijimos|hablamos)"
    r"|repite (?:mi|la) pregunta",
    re.IGNORECASE,
)

_EXPLICIT_REFERENCE_RE = re.compile(
    r"\b(?:ese|esa|el mismo|la misma|lo anterior|el anterior|la anterior)\b"
    r"|\beste año\b|\beste modelo\b|\bese (?:vehículo|vehiculo|coche|auto|carro|modelo)\b"
    r"|\bel problema anterior\b|\bese problema\b|\blo de antes\b",
    re.IGNORECASE,
)

_VAGUE_OPINION_RE = re.compile(
    r"^(?:qué opinas|que opinas|qué piensas|que piensas|qué crees|que crees)\??$",
    re.IGNORECASE,
)

_OUT_OF_SCOPE_RE = re.compile(
    r"\b(?:receta|política|politica|fútbol|futbol|programación|programacion|javascript|python)\b"
    r"|\b(?:clima|tiempo|noticias|bitcoin|cripto)\b",
    re.IGNORECASE,
)

_AUTOMOTIVE_RE = re.compile(
    r"\b(?:motor|transmisión|transmision|caja de cambios|embrague|freno|balata|pastilla"
    r"|batería|bateria|alternador|inyector|turbo|ecu|obd|dtc|falla|fallo|ruido|vibración|vibracion"
    r"|mantenimiento|refacción|refaccion|diagnóstico|diagnostico|reparación|reparacion|taller"
    r"|aceite|refrigerante|suspensión|suspension|dirección|direccion|escape|mofle|cilindro"
    r"|hyundai|tesla|toyota|honda|ford|chevrolet|nissan|bmw|audi|mercedes|volkswagen|kia|mazda"
    r"|santa fe|model s|corolla|civic|camioneta|sedán|sedan|suv|pickup|motocicleta|moto)\b",
    re.IGNORECASE,
)


def has_explicit_reference(message: str) -> bool:
    return bool(_EXPLICIT_REFERENCE_RE.search(message))


def detect_intent(message: str, working_memory: WorkingMemory) -> QueryIntent:
    text = message.strip()
    if not text:
        return QueryIntent.CONVERSATION

    if _MEMORY_RE.search(text):
        return QueryIntent.MEMORY_REQUEST

    if _CONVERSATION_RE.search(text) and not _AUTOMOTIVE_RE.search(text):
        return QueryIntent.CONVERSATION

    if _VAGUE_OPINION_RE.match(text) and not working_memory.has_active_context():
        return QueryIntent.CONVERSATION

    if _OUT_OF_SCOPE_RE.search(text) and not _AUTOMOTIVE_RE.search(text):
        return QueryIntent.OUT_OF_SCOPE

    if _AUTOMOTIVE_RE.search(text) or working_memory.has_active_context():
        return QueryIntent.AUTOMOTIVE

    return QueryIntent.CONVERSATION
