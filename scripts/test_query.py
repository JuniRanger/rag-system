"""
Script para probar consultas al sistema RAG desde la terminal.
No necesita el servidor FastAPI corriendo.

Uso:
    python scripts/test_query.py --query "¿Qué es RAG?"
    python scripts/test_query.py --query "¿Qué es RAG?" --no-reranker
    python scripts/test_query.py --interactive
"""
import sys
import argparse
from pathlib import Path

sys.path.append(str(Path(__file__).parent.parent))

from app.core.providers import create_rag_pipeline
from app.core.logger import logger


def print_result(result: dict):
    """Imprime el resultado de forma legible en terminal."""
    print("\n" + "="*60)
    print(f"  PREGUNTA: {result.get('query', '')}")
    print("="*60)
    print(f"\n  RESPUESTA:\n  {result['answer']}")
    print("\n" + "-"*60)

    sources = result.get("sources", [])
    if sources:
        labels = [
            source.get("label") or source.get("document_id")
            for source in sources
        ]
        print(f"  FUENTES: {', '.join(labels)}")

    meta = result.get("metadata", {})
    print(f"  Chunks recuperados : {meta.get('retrieved_chunks', meta.get('chunks_retrieved', 0))}")
    print(f"  Chunks usados      : {meta.get('used_chunks', meta.get('chunks_used', 0))}")
    print(f"  Latencia (ms)      : {meta.get('latency_ms', 0)}")
    if meta.get("function_calls"):
        print(f"  Tools usadas       : {len(meta['function_calls'])}")
    print("="*60 + "\n")


def run_single_query(query: str, use_reranker: bool = True):
    """Corre una sola consulta y muestra el resultado."""
    logger.info(f"Ejecutando consulta: '{query}'")
    pipeline = create_rag_pipeline(use_reranker=use_reranker)

    result = pipeline.query(query)
    print_result(result)


def run_interactive(use_reranker: bool = True):
    """Modo interactivo — escribe preguntas en loop hasta escribir 'salir'."""
    print("\n🤖 Sistema RAG activo — escribe 'salir' para terminar\n")
    pipeline = create_rag_pipeline(use_reranker=use_reranker)

    while True:
        try:
            query = input("Tu pregunta: ").strip()

            if not query:
                continue

            if query.lower() in ["salir", "exit", "quit", "bye", "adios"]:
                print("👋 Hasta luego")
                break

            result = pipeline.query(query)
            print_result(result)

        except KeyboardInterrupt:
            print("\n👋 Hasta luego")
            break


def main():
    parser = argparse.ArgumentParser(description="Probar consultas al sistema RAG")
    parser.add_argument(
        "--query",
        type=str,
        help="Pregunta a hacer al sistema"
    )
    parser.add_argument(
        "--interactive",
        action="store_true",
        help="Modo interactivo para múltiples preguntas"
    )
    parser.add_argument(
        "--no-reranker",
        action="store_true",
        help="Desactivar reranking para respuestas más rápidas"
    )
    args = parser.parse_args()

    use_reranker = not args.no_reranker

    if args.interactive:
        run_interactive(use_reranker)
    elif args.query:
        run_single_query(args.query, use_reranker)
    else:
        # Si no se pasa ningún argumento, entrar en modo interactivo
        run_interactive(use_reranker)


if __name__ == "__main__":
    main()
