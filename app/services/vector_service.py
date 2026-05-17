import random
from qdrant_client import QdrantClient
from qdrant_client.models import (
    Distance,
    VectorParams,
    PointStruct,
    Filter,
    FieldCondition,
    MatchValue,
)
from app.core.config import settings

# One client shared across all requests — connecting on every call would be slow
if settings.QDRANT_URL:
    client = QdrantClient(
        url=settings.QDRANT_URL,
        api_key=settings.QDRANT_API_KEY or None,
    )
else:
    client = QdrantClient(host=settings.QDRANT_HOST, port=settings.QDRANT_PORT)


def ensure_collection_exists():
    """
    Idempotent setup: create the Qdrant collection only if it doesn't exist yet.
    Called before every upsert/search so the service is self-initializing.
    """
    existing = [c.name for c in client.get_collections().collections]
    if settings.QDRANT_COLLECTION not in existing:
        client.create_collection(
            collection_name=settings.QDRANT_COLLECTION,
            vectors_config=VectorParams(
                size=settings.EMBEDDING_DIM,
                distance=Distance.COSINE,  # cosine similarity is standard for text
            ),
        )


def create_embedding(text: str) -> list:
    """
    Generate a vector embedding for the given text.

    ⚠️  THIS IS A MOCK for learning purposes.
    The mock is deterministic (same text → same vector) but NOT semantic
    (similar texts do NOT get similar vectors). That means search results
    won't be meaningful, but the pipeline will work end-to-end.

    To make search actually work, replace this with a real model:

    Option A — OpenAI (requires API key):
        import openai
        response = openai.embeddings.create(
            model="text-embedding-3-small", input=text
        )
        return response.data[0].embedding

    Option B — Free, local (sentence-transformers):
        from sentence_transformers import SentenceTransformer
        model = SentenceTransformer("all-MiniLM-L6-v2")  # 384-dim
        return model.encode(text).tolist()
    """
    seed = sum(ord(c) for c in text)
    random.seed(seed)
    return [random.uniform(-1.0, 1.0) for _ in range(settings.EMBEDDING_DIM)]


def store_vector(prompt_id: int, tenant_id: str, embedding: list):
    """
    Upsert (insert or update) a vector into Qdrant.

    The payload carries metadata that we use for:
    - Multi-tenant filtering (tenant_id)
    - Mapping results back to DB rows (prompt_id)
    """
    ensure_collection_exists()
    client.upsert(
        collection_name=settings.QDRANT_COLLECTION,
        points=[
            PointStruct(
                id=prompt_id,
                vector=embedding,
                payload={
                    "tenant_id": tenant_id,
                    "prompt_id": prompt_id,
                },
            )
        ],
    )


def search_similar(query: str, tenant_id: str, top_k: int = 5) -> list:
    """
    Find the top-k most similar prompts to the query.

    CRITICAL — MULTI-TENANT ENFORCEMENT:
    The Filter below ensures Qdrant only considers vectors where
    tenant_id matches the requesting user's tenant. Without this filter,
    a user from tenant A could see tenant B's prompts — a data leak.
    """
    ensure_collection_exists()
    query_vector = create_embedding(query)

    results = client.search(
        collection_name=settings.QDRANT_COLLECTION,
        query_vector=query_vector,
        query_filter=Filter(
            must=[
                # Only return results belonging to THIS tenant
                FieldCondition(
                    key="tenant_id",
                    match=MatchValue(value=tenant_id),
                )
            ]
        ),
        limit=top_k,
    )

    return [
        {
            "prompt_id": str(r.id),
            "score": r.score,
            "payload": r.payload,
        }
        for r in results
    ]
