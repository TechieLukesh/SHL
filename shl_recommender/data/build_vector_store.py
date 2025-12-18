"""Build a vector store for document embeddings.

Tries FAISS first; if unavailable, falls back to sklearn NearestNeighbors.
Outputs:
 - data/faiss.index (if FAISS used)
 - data/index_map.json (list of assessment_id in index order)
 - or data/nn_store.pkl (sklearn fallback) and index_map.json

Run: python data/build_vector_store.py
"""
import os
import json
import numpy as np
from pathlib import Path

ROOT = Path(__file__).parent
EMB = ROOT / 'doc_embeddings.npy'
CAT = ROOT / 'shl_assessments.json'
OUT_MAP = ROOT / 'index_map.json'
OUT_FAISS = ROOT / 'faiss.index'
OUT_NN = ROOT / 'nn_store.pkl'

def load_embeddings():
    if not EMB.exists():
        raise FileNotFoundError(f'Missing embeddings: {EMB}')
    return np.load(EMB)

def load_catalog():
    if not CAT.exists():
        raise FileNotFoundError(f'Missing catalog: {CAT}')
    data = json.loads(CAT.read_text(encoding='utf-8')).get('recommended_assessments', [])
    ids = []
    for it in data:
        aid = it.get('assessment_id') or (it.get('url') or '').rstrip('/').split('/')[-1]
        ids.append(aid)
    return ids, data

def try_faiss(embs, ids):
    try:
        import faiss
    except Exception:
        return False
    d = embs.shape[1]
    index = faiss.IndexFlatIP(d)
    # normalize for cosine-like inner product
    faiss.normalize_L2(embs)
    index.add(embs)
    faiss.write_index(index, str(OUT_FAISS))
    print('Wrote FAISS index to', OUT_FAISS)
    return True

def fallback_nn(embs, ids):
    try:
        from sklearn.neighbors import NearestNeighbors
        import pickle
    except Exception as e:
        raise RuntimeError('sklearn fallback unavailable: ' + str(e))
    nbrs = NearestNeighbors(metric='cosine', algorithm='brute')
    nbrs.fit(embs)
    with open(OUT_NN, 'wb') as f:
        pickle.dump(nbrs, f)
    print('Wrote sklearn NN store to', OUT_NN)
    return True

def main():
    embs = load_embeddings()
    ids, data = load_catalog()
    if embs.shape[0] != len(ids):
        print('Warning: embeddings count != catalog items; proceeding with min count')
        n = min(embs.shape[0], len(ids))
        embs = embs[:n]
        ids = ids[:n]

    OUT_MAP.write_text(json.dumps(ids, indent=2), encoding='utf-8')
    print('Wrote index map to', OUT_MAP)

    if try_faiss(embs.copy(), ids):
        return
    print('FAISS not available, using sklearn fallback')
    fallback_nn(embs, ids)

if __name__ == '__main__':
    main()
