import pytest
from app.rag.pipeline import RAGPipeline

def test_rag_flow_and_hallucination_prevention():
    """
    CRITERIO RÚBRICA: El System Prompt debe restringir adecuadamente al LLM
    para que admita ignorancia si el dato no está en la base de datos vectorial.
    """
    rag_pipeline = RAGPipeline()
    
    # Caso 1: Pregunta dentro del contexto de la rúbrica
    query_ok = "¿Cuál es el límite de latencia en el percentil 95?"
    res_ok = rag_pipeline.query(query_ok)
    
    assert "answer" in res_ok
    assert len(res_ok["context_used"]) > 0
    assert "100" in res_ok["answer"]

    # Caso 2: Pregunta fuera de contexto (Intento de provocar alucinación)
    query_trap = "¿Cómo se programa un microservicios en Java Spring Boot?"
    res_trap = rag_pipeline.query(query_trap)
    
    # Validar que el prompt lo frena e impide que use su conocimiento preentrenado
    answer_lower = res_trap["answer"].lower()
    assert any(
        phrase in answer_lower 
        for phrase in ["no encontré", "no se menciona", "no tengo información", "lo siento"]
    )