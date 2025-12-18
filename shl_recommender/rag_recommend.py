"""Minimal RAG runner: perform vector retrieval and optional LLM synthesis.

Usage:
  python rag_recommend.py --query "my job description" --top_k 5

Requires: sentence-transformers model already available (recommender imports it), and
`data/index_map.json` + `data/faiss.index` or `data/nn_store.pkl` created by the builder.
Optional: set `OPENAI_API_KEY` to enable answer synthesis.
"""
import os
import json
import argparse
import numpy as np
from pathlib import Path

ROOT = Path(__file__).parent
EMB = ROOT / 'data' / 'doc_embeddings.npy'
MAP = ROOT / 'data' / 'index_map.json'
FAISS_IDX = ROOT / 'data' / 'faiss.index'
NN_STORE = ROOT / 'data' / 'nn_store.pkl'

def load_query_embedding(query):
    # reuse recommender's model to ensure same embedding space
    try:
        from recommender import model
    except Exception:
        from sentence_transformers import SentenceTransformer
        model = SentenceTransformer('intfloat/e5-small-v2')
    emb = model.encode([f'query: {query}'], normalize_embeddings=True)
    return emb[0]

def search_faiss(q_emb, top_k=5):
    try:
        import faiss
    except Exception:
        raise RuntimeError('FAISS not available')
    xb = np.load(EMB)
    faiss.normalize_L2(xb)
    d = xb.shape[1]
    index = faiss.read_index(str(FAISS_IDX))
    faiss.normalize_L2(np.expand_dims(q_emb, axis=0))
    D, I = index.search(np.expand_dims(q_emb, axis=0), top_k)
    return I[0].tolist(), D[0].tolist()

def search_nn(q_emb, top_k=5):
    import pickle
    with open(NN_STORE, 'rb') as f:
        nbrs = pickle.load(f)
    dist, idx = nbrs.kneighbors([q_emb], n_neighbors=top_k)
    return idx[0].tolist(), (1 - dist[0]).tolist()

def synthesize_with_openai(query, docs):
    key = os.environ.get('OPENAI_API_KEY')
    if not key:
        return None
    try:
        from openai import OpenAI
        client = OpenAI(api_key=key)
        prompt = 'You are an assistant. Given a job description and a list of candidate assessments (title + URL + short excerpt), recommend the top 3 and explain why.\n\nJob description:\n' + query + '\n\nCandidates:\n'
        for i, d in enumerate(docs, start=1):
            prompt += f"{i}. {d.get('description')} — {d.get('url')}\nExcerpt: {d.get('full_description')[:200]}\n\n"
        resp = client.chat.completions.create(model='gpt-4o-mini', messages=[{'role':'user','content':prompt}], max_tokens=400)
        return resp.choices[0].message.content
    except Exception:
        return None

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--query', required=True)
    parser.add_argument('--top_k', type=int, default=5)
    args = parser.parse_args()

    if not MAP.exists():
        raise SystemExit('Missing index map; run data/build_vector_store.py')
    ids = json.loads(MAP.read_text(encoding='utf-8'))

    q_emb = load_query_embedding(args.query)

    if FAISS_IDX.exists():
        try:
            idxs, scores = search_faiss(q_emb, top_k=args.top_k)
        except Exception:
            idxs, scores = search_nn(q_emb, top_k=args.top_k)
    else:
        idxs, scores = search_nn(q_emb, top_k=args.top_k)

    # load catalog for details
    cat = json.loads((ROOT / 'data' / 'shl_assessments.json').read_text(encoding='utf-8')).get('recommended_assessments', [])
    results = []
    for i, s in zip(idxs, scores):
        i = int(i)
        if i < len(cat):
            it = cat[i]
            results.append({'assessment_id': ids[i] if i < len(ids) else None, 'description': it.get('description'), 'url': it.get('url'), 'score': float(s), 'excerpt': (it.get('full_description') or '')[:300]})

    out = {'query': args.query, 'results': results}
    # optional synthesis
    synth = synthesize_with_openai(args.query, results)
    if synth:
        out['synthesis'] = synth

    print(json.dumps(out, indent=2, ensure_ascii=False))

if __name__ == '__main__':
    main()
