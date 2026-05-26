from app.rag.chain import RAGChain
from app.rag.router import should_use_tools
from app.llm.tool_handler import ToolHandler
from app.core.logger import logger


class RAGPipeline:

    def __init__(self):

        # use_reranker=True para máxima calidad
        # Cambia a False si necesitas más velocidad

        self.chain = RAGChain(use_reranker=True)

        self.tool_handler = ToolHandler()

        logger.info("RAG Pipeline inicializado")

    def query(self, question: str) -> dict:
        """
        Punto de entrada principal del sistema RAG.
        Maneja errores y garantiza siempre una respuesta estructurada.
        """

        if not question or not question.strip():

            return self._error_response(
                "La pregunta no puede estar vacía."
            )

        question = question.strip()

        try:

            # =====================================
            # FUNCTION CALLING
            # =====================================

            if should_use_tools(question):

                messages = [
                    {
                        "role": "system",
                        "content": (
                            "Eres un asistente automotriz.\n"
                            "Usa herramientas cuando sea necesario.\n"
                            "No inventes información.\n"
                            "Si faltan datos pide aclaración."
                        )
                    },
                    {
                        "role": "user",
                        "content": question
                    }
                ]

                response = self.tool_handler.execute(
                    messages
                )

                return {
                    "success": True,
                    "query": question,
                    "answer": response,
                    "sources": ["tools"],
                    "context_used": [],
                    "metadata": {
                        "mode": "function_calling"
                    }
                }

            # =====================================
            # RAG NORMAL
            # =====================================

            result = self.chain.run(question)

            return {
                "success": True,
                "query": result["query"],
                "answer": result["answer"],
                "sources": result["sources"],
                "context_used": result.get(
                    "context_used",
                    []
                ),
                "metadata": {
                    "chunks_retrieved": result[
                        "chunks_retrieved"
                    ],
                    "chunks_used": result[
                        "chunks_used"
                    ],
                    "mode": "rag"
                },
            }

        except Exception as e:

            logger.error(
                f"Error en RAG Pipeline: {e}"
            )

            return self._error_response(
                f"Error interno del sistema: {str(e)}"
            )

    def _error_response(self, message: str) -> dict:

        return {
            "success": False,
            "query": "",
            "answer": message,
            "sources": [],
            "context_used": [],
            "metadata": {
                "chunks_retrieved": 0,
                "chunks_used": 0,
            },
        }