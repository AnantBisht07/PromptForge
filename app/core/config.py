from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    # JWT settings
    SECRET_KEY: str = "super-secret-key-change-this-in-production"
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30

    # Database — SQLite for local dev, swap for PostgreSQL in production
    DATABASE_URL: str = "sqlite:///./promptforge.db"

    # Qdrant vector database settings
    QDRANT_HOST: str = "localhost"
    QDRANT_PORT: int = 6333
    QDRANT_COLLECTION: str = "prompts"

    # Must match the embedding model's output size
    # Mock embeddings use 384 dimensions; OpenAI text-embedding-3-small uses 1536
    EMBEDDING_DIM: int = 384

    class Config:
        env_file = ".env"


# Single shared instance — import this everywhere instead of re-instantiating
settings = Settings()
