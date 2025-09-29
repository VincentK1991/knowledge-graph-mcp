from openai import AsyncOpenAI


class VectorEmbedding:
    def __init__(self, dimension: int = 384):
        self.client = AsyncOpenAI()
        self.dimension = dimension

    async def embed(self, text: str) -> list[float]:
        response = await self.client.embeddings.create(
            input=text, model="text-embedding-3-small", dimensions=self.dimension
        )
        return response.data[0].embedding

    async def batch_embed(self, texts: list[str]) -> list[list[float]]:
        response = await self.client.embeddings.create(
            input=texts, model="text-embedding-3-small", dimensions=self.dimension
        )
        return [data.embedding for data in response.data]
