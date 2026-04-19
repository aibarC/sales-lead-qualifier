"""
Document Indexer for Big Dream Lab RAG System
Reads text files from data/ directory, chunks them, and stores in ChromaDB.
"""

import os
import chromadb
from sentence_transformers import SentenceTransformer

DATA_DIR = os.path.join(os.path.dirname(__file__), "data")
CHROMA_DIR = os.path.join(os.path.dirname(__file__), "chroma_db")


def chunk_text(text: str, chunk_size: int = 500, overlap: int = 50) -> list[str]:
    """Split text into overlapping chunks by character count."""
    chunks = []
    start = 0
    while start < len(text):
        end = start + chunk_size
        chunk = text[start:end]
        if chunk.strip():
            chunks.append(chunk.strip())
        start += chunk_size - overlap
    return chunks


def load_documents(data_dir: str) -> list[dict]:
    """Load all .txt files from data directory."""
    documents = []
    for filename in os.listdir(data_dir):
        if filename.endswith(".txt"):
            filepath = os.path.join(data_dir, filename)
            with open(filepath, "r", encoding="utf-8") as f:
                text = f.read()
            documents.append({
                "filename": filename,
                "text": text
            })
            print(f"Loaded: {filename} ({len(text)} chars)")
    return documents


def index_documents():
    """Main indexing function."""
    print("=" * 50)
    print("Big Dream Lab RAG Indexer")
    print("=" * 50)

    # Load embedding model
    print("\nLoading embedding model...")
    model = SentenceTransformer("paraphrase-multilingual-MiniLM-L12-v2")
    print("Model loaded!")

    # Load documents
    print(f"\nLoading documents from {DATA_DIR}...")
    documents = load_documents(DATA_DIR)
    print(f"Loaded {len(documents)} documents")

    # Chunk documents
    print("\nChunking documents...")
    all_chunks = []
    all_metadata = []
    all_ids = []

    for doc in documents:
        chunks = chunk_text(doc["text"])
        for i, chunk in enumerate(chunks):
            chunk_id = f"{doc['filename']}_{i}"
            all_chunks.append(chunk)
            all_metadata.append({"source": doc["filename"], "chunk_index": i})
            all_ids.append(chunk_id)

    print(f"Created {len(all_chunks)} chunks")

    # Create embeddings and store in ChromaDB
    print("\nCreating embeddings and storing in ChromaDB...")

    # Remove old database if exists
    if os.path.exists(CHROMA_DIR):
        import shutil
        shutil.rmtree(CHROMA_DIR)

    client = chromadb.PersistentClient(path=CHROMA_DIR)
    collection = client.create_collection(
        name="bigdreamlab_docs",
        metadata={"hnsw:space": "cosine"}
    )

    # Generate embeddings
    embeddings = model.encode(all_chunks).tolist()

    # Add to collection
    collection.add(
        ids=all_ids,
        embeddings=embeddings,
        documents=all_chunks,
        metadatas=all_metadata
    )

    print(f"Indexed {len(all_chunks)} chunks into ChromaDB")
    print("\nIndexing complete!")
    print(f"Database saved to: {CHROMA_DIR}")


if __name__ == "__main__":
    index_documents()
