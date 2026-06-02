import os
import json
import hashlib
import ollama
import chromadb
from .paths import paths

class VectorDB:
    def __init__(self, db_path: str = None):
        # Default paths
        self.chroma_dir = getattr(paths, 'chroma_db_dir', os.path.join(paths.PROJECT_DIR, ".chroma"))
        self.json_path = db_path or paths.vector_db_file

        # Initialize persistent ChromaDB client & collection
        try:
            self.client = chromadb.PersistentClient(path=self.chroma_dir)
            self.collection = self.client.get_or_create_collection(
                name="arjun_memories",
                metadata={"hnsw:space": "cosine"}
            )
        except Exception as e:
            print(f"Error initializing ChromaDB: {e}")
            raise e

        # Run automatic migration from vector_db.json if it exists
        self.migrate_old_db()

    def migrate_old_db(self):
        """Migrate old JSON database to ChromaDB if ChromaDB is empty."""
        if os.path.exists(self.json_path):
            try:
                count = self.collection.count()
                if count == 0:
                    print(f"ChromaDB collection is empty. Migrating old JSON database at {self.json_path}...")
                    with open(self.json_path, "r", encoding="utf-8") as f:
                        old_docs = json.load(f)
                    
                    if old_docs:
                        ids = []
                        embeddings = []
                        documents = []
                        metadatas = []
                        for doc in old_docs:
                            text = (doc.get("text") or "").strip()
                            emb = doc.get("embedding")
                            if text and emb:
                                doc_id = self._generate_id(text)
                                ids.append(doc_id)
                                embeddings.append(emb)
                                documents.append(text)
                                metadatas.append(doc.get("metadata") or {})
                        
                        if ids:
                            self.collection.add(
                                ids=ids,
                                embeddings=embeddings,
                                documents=documents,
                                metadatas=metadatas
                            )
                            print(f"Successfully migrated {len(ids)} documents with embeddings to ChromaDB.")
                    
                    # Rename the file to avoid future migration attempts
                    backup_path = self.json_path + ".backup"
                    if os.path.exists(backup_path):
                        try:
                            os.remove(backup_path)
                        except Exception:
                            pass
                    os.rename(self.json_path, backup_path)
                    print(f"Renamed old JSON database to {backup_path}")
            except Exception as e:
                print(f"Error during database migration: {e}")

    def load(self):
        """Deprecated: SQLite/ChromaDB loads data automatically."""
        pass

    def save(self):
        """Deprecated: SQLite/ChromaDB saves data automatically."""
        pass

    def _generate_id(self, text: str) -> str:
        """Generate a deterministic MD5 hash of text as document ID for O(1) duplicate checks."""
        return hashlib.md5(text.encode("utf-8")).hexdigest()

    def _get_active_model(self) -> str:
        try:
            models = ollama.list().get("models", [])
            model_names = [m.get("model") or m.get("name") for m in models]
            for candidate in ["arjun-custom:latest", "arjun-custom", "jarvis-custom:latest", "jarvis-custom", "llama3:8b"]:
                if candidate in model_names:
                    return candidate
            if model_names:
                return model_names[0]
        except Exception:
            pass
        return "llama3:8b"

    def get_embedding(self, text: str) -> list[float]:
        model = self._get_active_model()
        try:
            resp = ollama.embeddings(model=model, prompt=text)
            return resp.get("embedding", [])
        except Exception as e:
            print(f"Ollama embedding error using model '{model}': {e}")
            return []

    @property
    def documents(self) -> list[dict]:
        """Backward compatibility: retrieve all documents from ChromaDB."""
        try:
            res = self.collection.get(include=["documents", "metadatas"])
            formatted = []
            if res and res.get("documents"):
                docs = res["documents"]
                metas = res["metadatas"] if res.get("metadatas") else [None] * len(docs)
                for doc_text, meta in zip(docs, metas):
                    formatted.append({
                        "text": doc_text,
                        "metadata": meta or {}
                    })
            return formatted
        except Exception:
            return []

    def add_document(self, text: str, metadata: dict = None):
        """Add a single document to ChromaDB with O(1) indexed duplicate checks."""
        text = (text or "").strip()
        if not text:
            return

        doc_id = self._generate_id(text)
        
        # Check if the document already exists using MD5 ID index (SELECT 1 style optimization)
        try:
            existing = self.collection.get(ids=[doc_id], include=[])
            if existing and existing.get("ids"):
                return  # Document already exists, skip
        except Exception as e:
            print(f"Error checking duplicate in ChromaDB: {e}")

        embedding = self.get_embedding(text)
        if not embedding:
            print(f"Could not generate embedding for text: {text}")
            return

        try:
            self.collection.add(
                ids=[doc_id],
                embeddings=[embedding],
                documents=[text],
                metadatas=[metadata or {}]
            )
        except Exception as e:
            print(f"Error adding document to ChromaDB: {e}")

    def add_documents(self, docs_to_add: list[dict]):
        """Batch add documents to prevent N+1 query and write overhead."""
        if not docs_to_add:
            return

        # Deduplicate incoming items and generate IDs
        docs_map = {}
        for d in docs_to_add:
            text = (d.get("text") or "").strip()
            if text:
                docs_map[self._generate_id(text)] = {
                    "text": text,
                    "metadata": d.get("metadata") or {}
                }

        if not docs_map:
            return

        doc_ids = list(docs_map.keys())

        # Batch check which ones already exist in ChromaDB in 1 database call
        existing_ids = set()
        try:
            existing = self.collection.get(ids=doc_ids, include=[])
            if existing and existing.get("ids"):
                existing_ids = set(existing["ids"])
        except Exception as e:
            print(f"Error batch-checking duplicates in ChromaDB: {e}")

        # Filter to only new documents
        new_ids = [d_id for d_id in doc_ids if d_id not in existing_ids]
        if not new_ids:
            return

        # Generate embeddings only for new documents
        new_docs = []
        new_embeddings = []
        for d_id in new_ids:
            text = docs_map[d_id]["text"]
            embedding = self.get_embedding(text)
            if embedding:
                new_docs.append(docs_map[d_id])
                new_embeddings.append(embedding)
            else:
                print(f"Could not generate embedding for text: {text}")

        # Ingest new documents in a single batch insert
        if new_docs:
            try:
                self.collection.add(
                    ids=[self._generate_id(d["text"]) for d in new_docs],
                    embeddings=new_embeddings,
                    documents=[d["text"] for d in new_docs],
                    metadatas=[d["metadata"] for d in new_docs]
                )
                print(f"Batch added {len(new_docs)} documents to ChromaDB.")
            except Exception as e:
                print(f"Error batch-adding documents to ChromaDB: {e}")

    def query(self, query_text: str, top_n: int = 3) -> list[dict]:
        """Perform semantic search using HNSW indexing and selective field retrieval (SELECT * optimization)."""
        query_text = (query_text or "").strip()
        if not query_text:
            return []

        query_emb = self.get_embedding(query_text)
        if not query_emb:
            return []

        try:
            # We omit 'embeddings' from include to avoid transferring heavy float arrays
            res = self.collection.query(
                query_embeddings=[query_emb],
                n_results=top_n,
                include=["documents", "metadatas", "distances"]
            )
            
            results = []
            if res and res.get("documents"):
                docs = res["documents"][0]
                metas = res["metadatas"][0] if res.get("metadatas") else [None] * len(docs)
                dists = res["distances"][0] if res.get("distances") else [0.0] * len(docs)
                
                for doc_text, meta, dist in zip(docs, metas, dists):
                    # In cosine space, similarity = 1.0 - distance
                    score = 1.0 - dist
                    results.append({
                        "text": doc_text,
                        "metadata": meta or {},
                        "score": score
                    })
            return results
        except Exception as e:
            print(f"ChromaDB query error: {e}")
            return []

    def list_documents(self, limit: int = 10, offset: int = 0) -> list[dict]:
        """Retrieve paginated list of documents without fetching heavy embeddings."""
        try:
            res = self.collection.get(
                limit=limit,
                offset=offset,
                include=["documents", "metadatas"]
            )
            formatted = []
            if res and res.get("documents"):
                docs = res["documents"]
                metas = res["metadatas"] if res.get("metadatas") else [None] * len(docs)
                ids = res["ids"]
                for d_id, doc_text, meta in zip(ids, docs, metas):
                    formatted.append({
                        "id": d_id,
                        "text": doc_text,
                        "metadata": meta or {}
                    })
            return formatted
        except Exception as e:
            print(f"ChromaDB list error: {e}")
            return []

# Singleton instance for general use
vector_db = VectorDB()
