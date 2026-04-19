"""
RAG API Server for Big Dream Lab
Flask server with /ask endpoint that uses ChromaDB + Groq (Llama 3.3 70B)
"""

import os
from flask import Flask, request, jsonify
import chromadb
from sentence_transformers import SentenceTransformer
from openai import OpenAI

app = Flask(__name__)

CHROMA_DIR = os.path.join(os.path.dirname(__file__), "chroma_db")
GROQ_API_KEY = os.environ.get("GROQ_API_KEY", "")
GROQ_MODEL = os.environ.get("GROQ_MODEL", "llama-3.3-70b-versatile")

print("Loading embedding model...")

embed_model = SentenceTransformer("paraphrase-multilingual-MiniLM-L12-v2")
print("Embedding model loaded!")

print("Connecting to ChromaDB...")
chroma_client = chromadb.PersistentClient(path=CHROMA_DIR)
collection = chroma_client.get_collection("bigdreamlab_docs")
print(f"Connected! Collection has {collection.count()} chunks")

print("Configuring Groq...")
groq_client = OpenAI(
    api_key=GROQ_API_KEY,
    base_url="https://api.groq.com/openai/v1"
)
print("Groq configured!")


def search_documents(query, n_results=5):
    query_embedding = embed_model.encode(query).tolist()
    results = collection.query(
        query_embeddings=[query_embedding],
        n_results=n_results
    )
    found = []
    for i in range(len(results["documents"][0])):
        found.append({
            "text": results["documents"][0][i],
            "source": results["metadatas"][0][i]["source"],
            "distance": results["distances"][0][i]
        })
    return found


def generate_answer(question, context_chunks):
    context_text = ""
    sources = set()
    for chunk in context_chunks:
        context_text += f"\n---\nSource: {chunk['source']}\n{chunk['text']}\n"
        sources.add(chunk["source"])

    response = groq_client.chat.completions.create(
        model=GROQ_MODEL,
        messages=[
            {
                "role": "system",
                "content": """You are a helpful and confident assistant for Big Dream Lab, an educational company in Astana, Kazakhstan specializing in Unity 3D, Unreal Engine 5, UI/UX design, 3D modeling, Product Management, and AR/VR development.

Rules:
- Answer in the SAME LANGUAGE as the user's question
- Be concise, confident, and helpful
- Use the provided context as your knowledge base - present information naturally as if you know it, do NOT say "context doesn't contain" or "based on context"
- If about pricing, always mention Tech Orda grant option and calculate the remainder
- If information is truly not available, say "Свяжитесь с нашим менеджером для уточнения"
- Do NOT add disclaimers like "рекомендуется обратиться" if the answer is already in the context
- Do NOT use bullet points or lists unless the question specifically asks for a list
- Answer naturally in 2-4 sentences"""
            },
            {
                "role": "user",
                "content": f"CONTEXT:\n{context_text}\n\nQUESTION: {question}"
            }
        ],
        temperature=0.3,
        max_tokens=500
    )

    return {
        "answer": response.choices[0].message.content,
        "sources": list(sources),
        "chunks_used": len(context_chunks)
    }


@app.route("/ask", methods=["GET", "POST"])
def ask():
    if request.method == "GET":
        question = request.args.get("q", "")
    else:
        data = request.get_json(silent=True) or {}
        question = data.get("q", data.get("question", ""))

    if not question:
        return jsonify({"error": "No question provided"}), 400

    try:
        chunks = search_documents(question, n_results=5)
        result = generate_answer(question, chunks)
        return jsonify({
            "status": "ok",
            "question": question,
            "answer": result["answer"],
            "sources": result["sources"],
            "chunks_used": result["chunks_used"]
        })
    except Exception as e:
        return jsonify({"status": "error", "error": str(e)}), 500


@app.route("/health", methods=["GET"])
def health():
    return jsonify({
        "status": "ok",
        "collection_size": collection.count(),
        "model": GROQ_MODEL
    })


if __name__ == "__main__":
    print(f"\nBig Dream Lab RAG Server")
    print(f"Documents: {collection.count()}")
    print(f"LLM: Groq ({GROQ_MODEL})")
    app.run(host="0.0.0.0", port=5000)