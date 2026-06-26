from hashlib import sha256
from uuid import NAMESPACE_URL, uuid5


def source_label(document: dict) -> str:
    """Devuelve una etiqueta legible para documentos o chunks normalizados."""
    metadata = document.get("metadata", {})

    if metadata.get("filename"):
        return metadata["filename"]

    if metadata.get("table") and metadata.get("record_id") is not None:
        return f"{metadata['table']}#{metadata['record_id']}"

    if metadata.get("table"):
        return metadata["table"]

    return "desconocido"


def stable_chunk_id(chunk: dict) -> str:
    """Construye un UUID estable a partir de la fuente, posición y contenido del chunk."""
    metadata = chunk.get("metadata", {})
    text_hash = sha256(chunk.get("text", "").encode("utf-8")).hexdigest()
    source_parts = [
        metadata.get("source", ""),
        metadata.get("file_path", ""),
        metadata.get("table", ""),
        str(metadata.get("record_id", "")),
        str(metadata.get("chunk_index", "")),
        str(metadata.get("start_char", "")),
        str(metadata.get("end_char", "")),
        text_hash,
    ]
    return str(uuid5(NAMESPACE_URL, "|".join(source_parts)))
