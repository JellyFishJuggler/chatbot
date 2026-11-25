import chromadb

client = chromadb.PersistentClient(path='/tmp/chroma_db')
collection = client.get_or_create_collection(name='user_docs')


def chunk_text(text: str, chunk_size: int = 50, overlap: int = 10) -> list[str]:
    words = text.split()
    CONTEXT = []
    for word in range(0, len(words), chunk_size - overlap):
        CONTEXT.append(" ".join(words[word:word + chunk_size]))
    return CONTEXT


def ingest_text(text: str, user_id: str, filename: str):
    chunks = chunk_text(text)
    if not chunks:
        return

    clean_user = str(user_id).strip()
    metadatas = [{"user_id": clean_user, "source": filename} for _ in chunks]
    ids = [f"{clean_user}_{filename}_chunk_{i}" for i in range(len(chunks))]
    collection.upsert(documents=chunks, metadatas=metadatas, ids=ids)
    print(f"[INGEST] user={clean_user!r} | chunks={len(chunks)} | total_in_db={collection.count()}")


def retrieve_context(query: str, user_id: str, k: int = 4) -> str:
    clean_user = str(user_id).strip()
    print(f"[RETRIEVE] user={clean_user!r} | total_in_db={collection.count()}")

    results = collection.query(query_texts=[query], n_results=k, where={"user_id": clean_user})

    if not results["documents"] or not results["documents"][0]:
        print(f"[RETRIEVE] user={clean_user!r} | 0 docs found in collection!")
        return "No context available"

    docs = results["documents"][0]
    distances = results["distances"][0]
    print(f"[RETRIEVE] distances={distances}")

    CONTEXT = [doc for doc, dist in zip(docs, distances) if dist < 1.7]
    if CONTEXT:
        return "\n---\n".join(CONTEXT)

    return "No context available"