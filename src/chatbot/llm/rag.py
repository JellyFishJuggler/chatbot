from pathlib import Path
from sentence_transformers import SentenceTransformer, util

model = SentenceTransformer('all-MiniLM-L6-v2')


KNOWLEDGE_BASE = Path('src/chatbot/llm/notes.txt')
    
def load_chunks(filepath:str | Path = KNOWLEDGE_BASE, chunk_size:int = 50, overlap: int = 10) -> list[str]:

    knowledge_base = Path(filepath).read_text(encoding='utf-8')
    words = knowledge_base.split()

    CONTEXT = list()

    for word in range(0, len(words), chunk_size - overlap):
        CONTEXT.append(" ".join(words[word:word+chunk_size]))

    return CONTEXT

KNOWLEDGE_BASE = load_chunks(KNOWLEDGE_BASE)
CHUNK_EMBEDDINGS = model.encode(KNOWLEDGE_BASE, convert_to_tensor=True)

def retrieve_context(query: str, k:int = 2) -> str:

    query_embeddings = model.encode(query, convert_to_tensor=True)
    scores = util.cos_sim(query_embeddings, CHUNK_EMBEDDINGS)[0]
    results = scores.topk(k=min(k, len(KNOWLEDGE_BASE)))

    CONTEXT = list()
    # CHUNKS = query.lower().split()

    for k in results.indices:
        CONTEXT.append(KNOWLEDGE_BASE[k])
    if CONTEXT:
        return "\n---\n".join(CONTEXT)

    return "No context available"