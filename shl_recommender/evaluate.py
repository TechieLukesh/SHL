import json
import os
from collections import defaultdict

# import recommend function from local recommender module
try:
    from recommender import recommend
except Exception as e:
    recommend = None

def normalize(s: str):
    if s is None:
        return ""
    return s.strip().lower()

def pred_key(pred):
    # try url first, then name/title
    for k in ("url", "name", "title"):
        if k in pred and pred[k]:
            return normalize(pred[k])
    # fallback: stringify whole dict
    return normalize(str(pred))

def is_url(s: str):
    s = (s or "").strip().lower()
    return s.startswith("http://") or s.startswith("https://")

def precision_at_k(preds, truths, k=5):
    topk = preds[:k]
    # build truth set; if truths look like urls, normalize as urls
    truth_is_url = any(is_url(t) for t in truths)
    if truth_is_url:
        truth_set = set(normalize(t) for t in truths)
        hits = sum(1 for p in topk if pred_key(p) in truth_set)
    else:
        truth_set = set(normalize(t) for t in truths)
        # match against predicted name/title/url
        hits = 0
        for p in topk:
            # compare predicted name/title first
            name_candidates = [p.get(k) for k in ("name","title") if p.get(k)]
            matched = False
            for nc in name_candidates:
                if normalize(nc) in truth_set:
                    matched = True
                    break
            if matched:
                hits += 1
                continue
            # as fallback compare url
            if pred_key(p) in truth_set:
                hits += 1
    return hits / k

def mrr(preds, truths):
    truth_is_url = any(is_url(t) for t in truths)
    truth_set = set(normalize(t) for t in truths)
    for i, p in enumerate(preds, start=1):
        if pred_key(p) in truth_set:
            return 1.0 / i
        # also check name/title
        for k in ("name", "title"):
            if k in p and normalize(p[k]) in truth_set:
                return 1.0 / i
    return 0.0

def evaluate(train_json="data/train.json", top_k=5):
    if recommend is None:
        print("Error: could not import recommend() from recommender.py. Aborting.")
        return

    with open(train_json, "r", encoding="utf8") as f:
        cases = json.load(f)

    p_sum = 0.0
    mrr_sum = 0.0
    n = 0
    per_case = []

    for item in cases:
        query = item.get("query")
        labels = item.get("labels", [])
        try:
            preds = recommend(query, top_k=top_k)
        except Exception as e:
            print(f"recommend() failed for query: {e}")
            preds = []

        p = precision_at_k(preds, labels, k=top_k)
        r = mrr(preds, labels)
        per_case.append({"query": query, f"precision@{top_k}": p, "mrr": r, "preds": preds, "labels": labels})
        p_sum += p
        mrr_sum += r
        n += 1

    avg_p = p_sum / n if n else 0.0
    avg_mrr = mrr_sum / n if n else 0.0
    print(f"Avg precision@{top_k}: {avg_p:.3f}")
    print(f"Avg MRR: {avg_mrr:.3f}")

    out_path = os.path.join("data", "eval_detail.json")
    with open(out_path, "w", encoding="utf8") as f:
        json.dump(per_case, f, indent=2, ensure_ascii=False)
    print("Wrote eval detail to", out_path)

if __name__ == '__main__':
    evaluate()
"""Evaluate recommender on labeled queries and produce predictions for unlabeled set.

Compute Precision@5 and MRR on labeled set. Simple weight tuning is a small grid
search over a single keyword-boost multiplier that adds to semantic score when
query tokens appear in the assessment description.

Run: `python evaluate.py` (from `shl_recommender` folder)
Outputs: `predictions.csv` (for unlabeled) and prints metrics.
"""
import json
from pathlib import Path
from recommender import model, doc_embeddings, filtered_data
import numpy as np
from sentence_transformers import util
import re
from urllib.parse import urlparse

ROOT = Path(__file__).parent
DATA = ROOT / 'data'

def load_labeled():
    p1 = DATA / 'train.json'
    p2 = DATA / 'labeled.json'
    if p1.exists():
        return json.loads(p1.read_text(encoding='utf-8'))
    if p2.exists():
        return json.loads(p2.read_text(encoding='utf-8'))
    raise FileNotFoundError('labeled.json or train.json not found; run data/parse_dataset.py')

def load_unlabeled():
    p = DATA / 'unlabeled.json'
    if not p.exists():
        raise FileNotFoundError('unlabeled.json not found; run data/parse_dataset.py')
    return json.loads(p.read_text(encoding='utf-8'))

def score_query(query, kw_boost=0.0):
    q_emb = model.encode(f"query: {query}", convert_to_tensor=True)
    scores = util.cos_sim(q_emb, doc_embeddings)[0].cpu().numpy()
    if kw_boost > 0:
        q_lower = query.lower()
        for i, item in enumerate(filtered_data):
            desc = (item.get('description') or '').lower()
            # simple keyword count
            cnt = sum(1 for w in q_lower.split() if w in desc)
            if cnt:
                scores[i] += kw_boost * cnt
    return scores

def _normalize_name(s: str):
    if not s:
        return ""
    s = s.lower()
    # keep alphanum, spaces, # and +
    s = re.sub(r"[^0-9a-z #\+]", " ", s)
    s = re.sub(r"\s+", " ", s).strip()
    return s

def _normalize_url(u: str):
    if not u:
        return ""
    try:
        parts = urlparse(u)
    except Exception:
        return _normalize_name(u)
    path = (parts.path or "").rstrip('/')
    # return netloc+path and last path segment
    seg = path.split('/')[-1] if path else ''
    keys = set()
    if parts.netloc or path:
        keys.add((parts.netloc + path).lower())
    if seg:
        keys.add(_normalize_name(seg))
    return keys

def precision_at_k(relevant_set, ranking, k=5):
    topk = ranking[:k]
    hits = 0
    for cand_keys in topk:
        if cand_keys & relevant_set:
            hits += 1
    return hits / k

def mrr(relevant_set, ranking):
    for idx, cand_keys in enumerate(ranking, start=1):
        if cand_keys & relevant_set:
            return 1.0 / idx
    return 0.0

def evaluate(kw_boost=0.0):
    labeled = load_labeled()
    # build assessment_id -> item map from filtered_data
    assess_map = {}
    for it in filtered_data:
        aid = it.get('assessment_id') or (it.get('url') or '').rstrip('/').split('/')[-1]
        if aid:
            assess_map[aid] = it
    ps = []
    mrs = []
    for ex in labeled:
        q = ex['query']
        raw_labels = [l for l in ex.get('labels', []) if l]
        # build normalized relevant set (strings)
        relevant = set()
        for lab in raw_labels:
            lab = lab.strip()
            # if canonical assessment_id
            if lab in assess_map:
                item = assess_map[lab]
                relevant.add(_normalize_name(item.get('description')))
                for k in _normalize_url(item.get('url') or ''):
                    relevant.add(k)
                continue
            # if appears to be URL
            if lab.lower().startswith('http://') or lab.lower().startswith('https://'):
                keys = _normalize_url(lab)
                for k in keys:
                    relevant.add(k)
                continue
            # skip unmapped markers
            if lab.startswith('UNMAPPED:'):
                # add the literal name as fallback (without prefix)
                relevant.add(_normalize_name(lab.replace('UNMAPPED:', '')))
                continue
            # otherwise treat as free-form name
            relevant.add(_normalize_name(lab))

        scores = score_query(q, kw_boost=kw_boost)
        ranking_idx = (-scores).argsort()
        # build candidate key sets for each ranked item
        ranking = []
        for i in ranking_idx:
            item = filtered_data[int(i)]
            cand_keys = set()
            desc = item.get('description') or ''
            cand_keys.add(_normalize_name(desc))
            url = item.get('url') or ''
            url_keys = _normalize_url(url)
            if isinstance(url_keys, set):
                cand_keys.update(url_keys)
            elif url_keys:
                cand_keys.add(url_keys)
            ranking.append(cand_keys)

        ps.append(precision_at_k(relevant, ranking, k=5))
        mrs.append(mrr(relevant, ranking))
    return np.mean(ps), np.mean(mrs)

def grid_tune():
    best = (0.0, 0.0, 0.0)
    for boost in [0.0, 0.1, 0.2, 0.5, 1.0]:
        p, r = evaluate(kw_boost=boost)
        print(f"kw_boost={boost}: Precision@5={p:.4f}, MRR={r:.4f}")
        if p > best[0]:
            best = (p, r, boost)
    print(f"Best: Precision@5={best[0]:.4f}, MRR={best[1]:.4f}, boost={best[2]}")
    return best[2]

def predict_unlabeled(boost=0.0):
    unl = load_unlabeled()
    import csv
    out = ROOT / 'predictions.csv'
    with open(out, 'w', newline='', encoding='utf-8') as f:
        writer = csv.writer(f)
        writer.writerow(['id','query','predicted_assessment_id','predicted_name','predicted_url'])
        for ex in unl:
            q = ex['query']
            scores = score_query(q, kw_boost=boost)
            idx = int((-scores).argsort()[0])
            item = filtered_data[idx]
            aid = item.get('assessment_id') or (item.get('url') or '').rstrip('/').split('/')[-1]
            writer.writerow([ex.get('id'), q, aid, item.get('description'), item.get('url')])
    print(f"Wrote predictions to {out}")

def main():
    print("Parsing done; tuning on labeled set...")
    try:
        best_boost = grid_tune()
    except Exception as e:
        print("Tuning failed:", e)
        best_boost = 0.0
    print("Generating predictions for unlabeled with boost=", best_boost)
    predict_unlabeled(boost=best_boost)

if __name__ == '__main__':
    main()
