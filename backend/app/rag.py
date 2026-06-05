import os

os.environ["ORT_DISABLE_COREML"] = "1"

import chromadb
from chromadb.utils import embedding_functions

CHUNK_SIZE = 500
CHUNK_OVERLAP = 50


class HLDDRetriever:
    def __init__(self, persistent: bool = False):
        settings = chromadb.config.Settings(
            anonymized_telemetry=False,
            allow_reset=True,
        )
        if persistent:
            persist_dir = os.path.join(os.path.dirname(__file__), "..", "chroma_db")
            os.makedirs(persist_dir, exist_ok=True)
            self.client = chromadb.PersistentClient(path=persist_dir, settings=settings)
        else:
            self.client = chromadb.EphemeralClient(settings=settings)

        self.collection = self.client.get_or_create_collection(
            name="hldd_chunks",
            embedding_function=embedding_functions.DefaultEmbeddingFunction(),
        )

    def _warm_up(self):
        """Trigger embedding model download at startup, not on first upload."""
        self.collection.add(documents=["warmup"], ids=["warmup_0"])
        self.collection.delete(ids=["warmup_0"])

    def ingest(self, hldd_text: str, doc_id: str = "current"):
        if not hldd_text.strip():
            return
        chunks = []
        start = 0
        while start < len(hldd_text):
            end = start + CHUNK_SIZE
            chunks.append(hldd_text[start:end])
            start += CHUNK_SIZE - CHUNK_OVERLAP

        ids = [
            f"{doc_id}_{i}" if doc_id != "current" else f"chunk_{i}"
            for i in range(len(chunks))
        ]

        existing = self.collection.get(ids=ids)
        if existing and existing["ids"]:
            self.collection.delete(ids=existing["ids"])

        self.collection.add(
            documents=chunks,
            ids=ids,
        )

    def retrieve(self, query: str, k: int = 3) -> str:
        if self.collection.count() == 0:
            return ""
        results = self.collection.query(
            query_texts=[query],
            n_results=min(k, self.collection.count()),
        )
        if results and results.get("documents") and results["documents"][0]:
            return "\n\n".join(results["documents"][0])
        return ""

    def clear(self):
        self.collection.delete(ids=self.collection.get()["ids"])


retriever = HLDDRetriever()
try:
    retriever._warm_up()
except Exception:
    pass  # embedding model download failed at startup; will retry on first ingest
