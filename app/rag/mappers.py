from app.core.documents import source_label, stable_chunk_id
from app.rag.schemas import (
    FunctionCallRecord,
    RAGResponse,
    RAGResponseMetadata,
    SourceReference,
    WorkingMemory,
)


def build_source_references(chunks: list[dict]) -> list[SourceReference]:
    references: list[SourceReference] = []
    seen: set[str] = set()

    for chunk in chunks:
        metadata = chunk.get("metadata", {})
        document_id = metadata.get("record_id") or stable_chunk_id(chunk)
        document_key = str(document_id)

        if document_key in seen:
            continue

        score = float(chunk.get("rerank_score") or chunk.get("score", 0.0))
        references.append(
            SourceReference(
                document_id=document_key,
                score=round(score, 4),
                label=source_label(chunk),
            )
        )
        seen.add(document_key)

    return sorted(references, key=lambda source: source.score, reverse=True)


def build_function_calls(tools_used: list[dict]) -> list[FunctionCallRecord]:
    calls: list[FunctionCallRecord] = []
    for item in tools_used:
        calls.append(
            FunctionCallRecord(
                name=item.get("tool", ""),
                arguments=item.get("arguments", {}),
                status=item.get("status", "unknown"),
                output=item.get("output"),
            )
        )
    return calls


def estimate_tokens(text: str) -> int:
    if not text:
        return 0
    return max(1, len(text) // 4)


def error_response(
    conversation_id: str,
    message: str,
    summary: str = "",
    working_memory: WorkingMemory | None = None,
) -> RAGResponse:
    return RAGResponse(
        success=False,
        conversation_id=conversation_id,
        answer=message,
        summary=summary,
        working_memory=working_memory or WorkingMemory(),
        sources=[],
        metadata=RAGResponseMetadata(),
    )
