import json
from sentence_transformers import SentenceTransformer, util
import re
import os
import numpy as np
import warnings

# Load data (full catalog)
with open(os.path.join("data", "shl_assessments.json"), "r", encoding="utf-8") as f:
    raw_data = json.load(f).get("recommended_assessments", [])


# Helper to detect pre-packaged solutions
def is_prepackaged(item: dict) -> bool:
    desc = (item.get("description") or "").lower()
    url = (item.get("url") or "").lower()
    if "pre-packaged" in desc or "prepackaged" in desc or "pre packaged" in desc:
        return True
    if "solution" in desc:
        return True
    if "solution" in url or "pre-packaged" in url or "prepackaged" in url:
        return True
    return False


# Load E5 model (lazy loaded at import)
model = SentenceTransformer("intfloat/e5-small-v2")


# Build document strings for the full catalog (keeps ordering aligned with raw_data)
documents = [
    (
        f"passage: {item.get('description','')} Skills assessed: {', '.join(item.get('skills', []))}. "
        f"Remote support: {item.get('remote_support')}. Adaptive: {item.get('adaptive_support')}. "
        f"Test types: {', '.join(item.get('test_type', []))}. Duration: {item.get('duration', '')} minutes."
    )
    for item in raw_data
]


# Load or precompute document embeddings (persisted to avoid expensive startup)
EMB_PATH = os.path.join("data", "doc_embeddings.npy")
doc_embeddings = None
if os.path.exists(EMB_PATH):
    try:
        emb = np.load(EMB_PATH)
        try:
            import torch

            doc_embeddings = torch.from_numpy(emb)
        except Exception:
            doc_embeddings = emb
        print(f"Loaded {emb.shape} doc embeddings from {EMB_PATH}")
    except Exception as e:
        warnings.warn(f"Failed to load embeddings from {EMB_PATH}: {e}. Recomputing.")

if doc_embeddings is None:
    doc_embeddings = model.encode(documents, convert_to_tensor=True)
    try:
        # save as numpy for portability
        np.save(EMB_PATH, doc_embeddings.cpu().numpy())
        print("Saved document embeddings to", EMB_PATH)
    except Exception as e:
        warnings.warn(f"Could not save embeddings to {EMB_PATH}: {e}")


# small utility helpers for skill matching and difficulty
_ALIASES = {"js": "javascript", "nodejs": "javascript", "csharp": "c#"}


def _normalize_skill(s: str):
    s = (s or "").strip().lower()
    s = re.sub(r"[^a-z0-9#+ ]+", " ", s)
    s = s.replace("c sharp", "c#")
    return _ALIASES.get(s, s)


def _extract_jd_tokens(text: str):
    t = (text or "").lower()
    t = re.sub(r"[\W_]+", " ", t)
    return set(w for w in t.split() if len(w) > 1)


def _skill_overlap_norm(jd_text: str, item_skills) -> float:
    if not item_skills:
        return 0.0
    jd_tokens = _extract_jd_tokens(jd_text)
    normalized = [_normalize_skill(s) for s in item_skills]
    normalized = [s for s in normalized if s]
    if not normalized:
        return 0.0
    matches = 0
    for sk in normalized:
        if sk in jd_tokens or any(sk in tok for tok in jd_tokens):
            matches += 1
        elif " " in sk and all(part in jd_tokens for part in sk.split()):
            matches += 1
    return matches / max(len(normalized), 1)


def _difficulty_score(jd_text: str, item: dict) -> float:
    jd = (jd_text or "").lower()
    wants_entry = bool(re.search(r"\b(entry|junior|graduate|new graduate)\b", jd))
    wants_senior = bool(re.search(r"\b(senior|lead|manager|director)\b", jd))
    if not (wants_entry or wants_senior):
        return 0.0
    desc = (item.get("description") or "").lower()
    is_entry = bool(re.search(r"\b(entry|junior|graduate)\b", desc))
    is_senior = bool(re.search(r"\b(senior|lead|manager|director)\b", desc))
    if wants_entry and is_entry:
        return 1.0
    if wants_senior and is_senior:
        return 1.0
    return 0.0


def _as_tensor(x):
    try:
        import torch

        if isinstance(x, np.ndarray):
            return torch.from_numpy(x)
        return x
    except Exception:
        return x


def _get_kept_indices(exclude_prepackaged: bool):
    if not exclude_prepackaged:
        return list(range(len(raw_data)))
    return [i for i, item in enumerate(raw_data) if not is_prepackaged(item)]


def recommend(job_desc: str, top_k=10, w_skill=0.6, w_embed=0.4, w_diff=0.0, exclude_prepackaged: bool = False):
    """Recommend assessments for a job description.

    Supports excluding pre-packaged solutions by passing `exclude_prepackaged=True`.
    Returns a list of candidate dicts augmented with a `score` field.
    """
    indices = _get_kept_indices(exclude_prepackaged)
    if not indices:
        return []

    # subset embeddings and items while preserving original indexing
    emb_subset = doc_embeddings[indices]
    emb_subset = _as_tensor(emb_subset)

    query_embedding = model.encode(f"query: {job_desc}", convert_to_tensor=True)
    sim_scores = util.cos_sim(query_embedding, emb_subset)[0].cpu().tolist()

    scored = []
    for idx, score_sim in zip(indices, sim_scores):
        item = raw_data[idx]
        skills = item.get("skills") or []
        s_overlap = _skill_overlap_norm(job_desc, skills)
        diff = _difficulty_score(job_desc, item)
        combined = (w_skill * s_overlap) + (w_embed * float(score_sim)) + (w_diff * diff)
        out = dict(item)
        out["score"] = combined
        scored.append(out)

    scored.sort(key=lambda x: x["score"], reverse=True)
    return scored[:top_k]


def recommend_balanced(job_desc: str, top_k=10, w_skill=0.6, w_embed=0.4, w_diff=0.0, prefer_ratio=0.5, exclude_prepackaged: bool = False):
    """
    Greedy balanced recommender: attempts to include a mix of K (knowledge) and P (personality)
    test types in the top_k results. `prefer_ratio` is fraction of K items desired in top_k.
    If exact mix isn't available, falls back to best scoring items.
    """
    indices = _get_kept_indices(exclude_prepackaged)
    if not indices:
        return []

    emb_subset = doc_embeddings[indices]
    emb_subset = _as_tensor(emb_subset)

    query_embedding = model.encode(f"query: {job_desc}", convert_to_tensor=True)
    sim_scores = util.cos_sim(query_embedding, emb_subset)[0].cpu().tolist()

    scored = []
    for idx, score_sim in zip(indices, sim_scores):
        item = raw_data[idx]
        skills = item.get("skills") or []
        s_overlap = _skill_overlap_norm(job_desc, skills)
        diff = _difficulty_score(job_desc, item)
        combined = (w_skill * s_overlap) + (w_embed * float(score_sim)) + (w_diff * diff)
        out = dict(item)
        out["score"] = combined
        scored.append(out)

    # sort by score
    scored.sort(key=lambda x: x["score"], reverse=True)

    # partition candidates by K vs P vs other
    k_list = []
    p_list = []
    other = []
    for c in scored:
        types = c.get("test_type") or []
        found_k = any(("k" in str(t).lower()) for t in types)
        found_p = any(("p" in str(t).lower()) for t in types)
        if found_k and not found_p:
            k_list.append(c)
        elif found_p and not found_k:
            p_list.append(c)
        else:
            other.append(c)

    # desired counts
    desired_k = int(round(prefer_ratio * top_k))
    desired_p = top_k - desired_k

    selected = []
    ki = pi = oi = 0
    # greedy fill alternatingly to preserve score ordering within each bucket
    while len(selected) < top_k:
        if len([s for s in selected if any(("k" in str(t).lower()) for t in (s.get("test_type") or []))]) < desired_k and ki < len(k_list):
            selected.append(k_list[ki]); ki += 1; continue
        if len([s for s in selected if any(("p" in str(t).lower()) for t in (s.get("test_type") or []))]) < desired_p and pi < len(p_list):
            selected.append(p_list[pi]); pi += 1; continue
        if oi < len(other):
            selected.append(other[oi]); oi += 1; continue
        if ki < len(k_list):
            selected.append(k_list[ki]); ki += 1; continue
        if pi < len(p_list):
            selected.append(p_list[pi]); pi += 1; continue
        break

    return selected[:top_k]

