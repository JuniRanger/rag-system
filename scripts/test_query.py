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

from app.rag.pipeline import RAGPipeline
from app.core.logger import logger


def print_result(result: dict):
    """Imprime el resultado de forma legible en terminal."""
    print("\n" + "="*60)
    print(f"  PREGUNTA: {result['query']}")
    print("="*60)
    print(f"\n  RESPUESTA:\n  {result['answer']}")
    print("\n" + "-"*60)

    if result["sources"]:
        print(f"  FUENTES: {', '.join(result['sources'])}")

    meta = result.get("metadata", {})
    print(f"  Chunks recuperados : {meta.get('chunks_retrieved', 0)}")
    print(f"  Chunks usados      : {meta.get('chunks_used', 0)}")
    print("="*60 + "\n")


def run_single_query(query: str, use_reranker: bool = True):
    """Corre una sola consulta y muestra el resultado."""
    logger.info(f"Ejecutando consulta: '{query}'")
    pipeline = RAGPipeline()

    # Configurar reranker según argumento
    pipeline.chain.use_reranker = use_reranker

    result = pipeline.query(query)
    print_result(result)


def run_interactive(use_reranker: bool = True):
    """Modo interactivo — escribe preguntas en loop hasta escribir 'salir'."""
    print("\n🤖 Sistema RAG activo — escribe 'salir' para terminar\n")
    pipeline = RAGPipeline()
    pipeline.chain.use_reranker = use_reranker

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