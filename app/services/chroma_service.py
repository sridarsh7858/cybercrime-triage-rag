import os
from langchain_ollama import OllamaEmbeddings
from langchain_chroma import Chroma
from app.core.config import settings

print(f"[chroma] Connecting to existing SQLite ChromaDB at: {settings.CHROMA_DB_DIR}")

if not os.path.exists(os.path.join(settings.CHROMA_DB_DIR, "chroma.sqlite3")):
    raise RuntimeError(f"No ChromaDB found at {settings.CHROMA_DB_DIR}")

# Initialize the embedding model
embedding_model = OllamaEmbeddings(model=settings.EMBEDDING_MODEL)

# Attach to the existing persisted collection
vector_db = Chroma(
    collection_name=settings.CHROMA_COLLECTION,
    embedding_function=embedding_model,
    persist_directory=settings.CHROMA_DB_DIR
)

# Chroma silently creates an empty collection when the name doesn't exist, which
# turns a config typo into "0 similar matches" instead of an error. Fail loudly.
_count = vector_db._collection.count()
if _count == 0:
    raise RuntimeError(
        f"Collection '{settings.CHROMA_COLLECTION}' in {settings.CHROMA_DB_DIR} is empty. "
        f"Available collections: "
        f"{[c.name for c in vector_db._client.list_collections()]}"
    )
print(f"[chroma] Collection '{settings.CHROMA_COLLECTION}' ready with {_count} documents")

def retrieve_similar_cases(query: str, top_k: int = 3):
    """Fetches top-k similar complaints directly from disk."""
    results = vector_db.similarity_search(query, k=top_k)
    return results