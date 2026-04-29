import asyncio
from typing import Any

from fastembed import TextEmbedding

from retrieval_service.domain.errors import RetrievalUnavailableError


class FastEmbedEmbeddingProvider:
    def __init__(self, model_name: str, model: Any | None = None) -> None:
        self._model = model if model is not None else TextEmbedding(model_name=model_name)

    async def embed(self, texts: list[str]) -> list[list[float]]:
        try:
            return await asyncio.to_thread(
                lambda: [list(vector) for vector in self._model.embed(texts)],
            )
        except Exception as error:
            raise RetrievalUnavailableError() from error
