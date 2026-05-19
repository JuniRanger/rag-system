import json
from pathlib import Path
from dataclasses import dataclass
from app.core.logger import logger

@dataclass
class EvalSample:
    """Una muestra de evaluación: pregunta + respuesta esperada."""
    question: str
    expected_answer: str
    relevant_keywords: list[str]

class EvalDataset:
    """
    Dataset de evaluación del sistema RAG.
    Debes personalizar estas preguntas según tus documentos reales.
    """

    DEFAULT_SAMPLES = [
        EvalSample(
            question="¿Qué latencia en el percentil p95 debe mantener el sistema para un buen resultado?",
            expected_answer="El sistema debe mantener una latencia en el percentil 95 (p95) por debajo de los 100 milisegundos.",
            relevant_keywords=["latencia", "percentil", "p95", "100", "milisegundos"]
        ),
        EvalSample(
            question="¿Qué sucede si la configuración de la base de datos vectorial es volátil?",
            expected_answer="Si la configuración es volátil y los datos se borran al reiniciar, la calificación se considera insuficiente o en desarrollo.",
            relevant_keywords=["volátil", "borran", "reiniciar", "insuficiente", "desarrollo"]
        ),
        EvalSample(
            question="¿Cuáles son las 4 métricas de evaluación categóricas que exige la rúbrica?",
            expected_answer="Las métricas obligatorias son Fidelidad, Relevancia, Precisión y Recuerdo (Context Precision, Context Recall, Faithfulness, Answer Relevancy).",
            relevant_keywords=["fidelidad", "relevancia", "precisión", "recuerdo", "métricas"]
        ),
        EvalSample(
            question="¿Qué algoritmo de búsqueda aproximada se debe ajustar según los requerimientos de velocidad?",
            expected_answer="Se deben ajustar los parámetros de búsqueda aproximada utilizando algoritmos HNSW.",
            relevant_keywords=["búsqueda", "aproximada", "algoritmos", "hnsw"]
        ),
        EvalSample(
            question="¿Qué se evalúa en el criterio de Trabajo en Equipo?",
            expected_answer="Se evalúa un trabajo equitativo con 3 roles técnicos claros y roles distribuidos con evidencia de código en el repositorio.",
            relevant_keywords=["trabajo", "equitativo", "roles", "código", "repositorio"]
        )
    ]

    def get_samples(self) -> list[EvalSample]:
        return self.DEFAULT_SAMPLES

    def load_from_file(self, path: str) -> list[EvalSample]:
        """Carga preguntas desde un JSON externo."""
        file_path = Path(path)
        if not file_path.exists():
            logger.warning(f"Dataset no encontrado: {path}. Usando dataset por defecto.")
            return self.DEFAULT_SAMPLES

        with open(file_path, "r", encoding="utf-8") as f:
            data = json.load(f)

        samples = [
            EvalSample(
                question=item["question"],
                expected_answer=item["expected_answer"],
                relevant_keywords=item.get("relevant_keywords", [])
            )
            for item in data
        ]

        logger.info(f"Dataset cargado: {len(samples)} muestras desde {path}")
        return samples

    def save_to_file(self, path: str):
        """Guarda el dataset por defecto en disco para que puedas editarlo."""
        output = [
            {
                "question": s.question,
                "expected_answer": s.expected_answer,
                "relevant_keywords": s.relevant_keywords
            }
            for s in self.DEFAULT_SAMPLES
        ]

        Path(path).parent.mkdir(parents=True, exist_ok=True)
        with open(path, "w", encoding="utf-8") as f:
            json.dump(output, f, ensure_ascii=False, indent=2)

        logger.info(f"Dataset guardado en: {path}")