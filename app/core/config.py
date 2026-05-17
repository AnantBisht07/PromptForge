from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    # JWT settings
    SECRET_KEY: str = "super-secret-key-change-this-in-production"
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30

    # Database — SQLite for local dev, swap for PostgreSQL in production
    DATABASE_URL: str = "sqlite:///./promptforge.db"
    SQL_ECHO: bool = False

    # Qdrant vector database settings
    QDRANT_URL: str = ""
    QDRANT_API_KEY: str = ""
    QDRANT_HOST: str = "localhost"
    QDRANT_PORT: int = 6333
    QDRANT_COLLECTION: str = "prompts"

    # Must match the embedding model's output size
    # Mock embeddings use 384 dimensions; OpenAI text-embedding-3-small uses 1536
    EMBEDDING_DIM: int = 384

    # OpenAI — used by the evaluation engine's LLM service
    # Leave empty to use mock responses (no API key needed for local dev)
    OPENAI_API_KEY: str = ""

    # LangSmith tracing — used by the evaluation graph
    # Leave empty to disable tracing (app works fine without it)
    # Get your key at https://smith.langchain.com
    LANGCHAIN_API_KEY: str = ""
    LANGCHAIN_PROJECT: str = "promptforge-eval"

    class Config:
        env_file = ".env"
        extra = "ignore"


# Single shared instance — import this everywhere instead of re-instantiating
settings = Settings()
