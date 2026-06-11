from app.rag.chain import RAGChain
from app.core.logger import logger
from app.embeddings.base import BaseEmbeddingProvider
from app.llm.base import BaseLLMProvider
from app.vectorstore.base import BaseVectorStoreProvider

class RAGPipeline:
    def __init__(
        self,
        embedding_provider: BaseEmbeddingProvider,
        vector_store_provider: BaseVectorStoreProvider,
        llm_provider: BaseLLMProvider,
        use_reranker: bool = True,
    ):
        # use_reranker=True para máxima calidad
        # Cambia a False si necesitas más velocidad
        self.chain = RAGChain(
            embedding_provider=embedding_provider,
            vector_store_provider=vector_store_provider,
            llm_provider=llm_provider,
            use_reranker=use_reranker,
        )
        logger.info("RAG Pipeline inicializado")

    def query(self, question: str) -> dict:
        """
        Punto de entrada principal del sistema RAG.
        Maneja errores y garantiza siempre una respuesta estructurada.
        """
        if not question or not question.strip():
            return self._error_response("La pregunta no puede estar vacía.")

        question = question.strip()

        try:
            result = self.chain.run(question)
            return {
                "success": True,
                "query": result["query"],
                "answer": result["answer"],
                "sources": result["sources"],
                "context_used": result.get("context_used", []),
                "metadata": {
                    "chunks_retrieved": result["chunks_retrieved"],
                    "chunks_used": result["chunks_used"],
                    "tools_used": result.get("tools_used", []),
                },
            }
        except Exception as e:
            logger.error(f"Error en RAG Pipeline: {e}")
            return self._error_response(f"Error interno del sistema: {str(e)}")

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
