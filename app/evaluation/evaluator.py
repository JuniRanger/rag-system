import json
from pathlib import Path
from app.evaluation.metrics import MetricsCalculator, RAGMetrics
from app.evaluation.dataset import EvalDataset
from app.rag.pipeline import RAGPipeline
from app.core.logger import logger

class RAGEvaluator:
    def __init__(self):
        self.pipeline = RAGPipeline()
        self.calculator = MetricsCalculator()
        self.dataset = EvalDataset()

    def evaluate(self, dataset_path: str = None) -> dict:
        """
        Corre la evaluación completa del sistema RAG.
        Retorna métricas promedio y resultados por pregunta.
        """
        samples = (
            self.dataset.load_from_file(dataset_path)
            if dataset_path
            else self.dataset.get_samples()
        )

        logger.info(f"Iniciando evaluación con {len(samples)} muestras")
        results = []

        for i, sample in enumerate(samples, 1):
            logger.info(f"Evaluando muestra {i}/{len(samples)}: '{sample.question}'")

            # Correr el sistema RAG con esta pregunta
            rag_result = self.pipeline.query(sample.question)

            # Calcular las 4 métricas para esta muestra
            metrics = RAGMetrics(
                context_precision=self.calculator.calculate_context_precision(
                    sample.question,
                    rag_result.get("context_used", [])
                ),
                context_recall=self.calculator.calculate_context_recall(
                    rag_result["answer"],
                    rag_result.get("context_used", [])
                ),
                faithfulness=self.calculator.calculate_faithfulness(
                    rag_result["answer"],
                    rag_result.get("context_used", [])
                ),
                answer_relevancy=self.calculator.calculate_answer_relevancy(
                    sample.question,
                    rag_result["answer"]
                )
            )

            results.append({
                "question": sample.question,
                "answer": rag_result["answer"],
                "sources": rag_result["sources"],
                "metrics": metrics.to_dict()
            })

            logger.info(f"  Métricas: {metrics.to_dict()}")

        # Calcular promedios finales
        avg_metrics = self._average_metrics(results)
        final_metrics = RAGMetrics(**avg_metrics)

        # Imprimir reporte en terminal
        print(final_metrics.report())

        # Guardar resultados en disco
        report = {
            "total_samples": len(samples),
            "average_metrics": final_metrics.to_dict(),
            "results": results
        }
        self._save_report(report)

        return report

    def _average_metrics(self, results: list[dict]) -> dict:
        keys = ["context_precision", "context_recall", "faithfulness", "answer_relevancy"]
        averages = {}
        for key in keys:
            values = [r["metrics"][key] for r in results]
            averages[key] = sum(values) / len(values)
        return averages

    def _save_report(self, report: dict):
        output_path = Path("data/processed/evaluation_report.json")
        output_path.parent.mkdir(parents=True, exist_ok=True)

        with open(output_path, "w", encoding="utf-8") as f:
            json.dump(report, f, ensure_ascii=False, indent=2)

        logger.info(f"Reporte de evaluación guardado en: {output_path}")