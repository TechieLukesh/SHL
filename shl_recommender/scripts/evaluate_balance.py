import json
from pathlib import Path
from recommender import recommend, filtered_data

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / 'data'

# load labeled set
train = json.loads((DATA / 'train_remapped.json').read_text(encoding='utf-8'))

def is_relevant(pred_item, truths):
    # compare assessment_id or normalized url
    aid = pred_item.get('assessment_id') or (pred_item.get('url') or '').rstrip('/').split('/')[-1]
    # truths may contain canonical ids or urls or names
    for t in truths:
        if not t:
            continue
        if t == aid:
            return True
        if isinstance(t,str) and t.startswith('http'):
            if aid in t:
                return True
        # fallback compare description/title
        if pred_item.get('description') and t.lower() in pred_item.get('description','').lower():
            return True
    return False

# Mean Recall@10
recalls = []
for ex in train:
    q = ex['query']
    truths = ex.get('labels', [])
    preds = recommend(q, top_k=10)
    hits = 0
    # treat truths as set
    for p in preds:
        if is_relevant(p, truths):
            hits += 1
    total_relevant = max(len([t for t in truths if t and not str(t).startswith('UNMAPPED:')]), 1)
    recall = hits / total_relevant
    recalls.append(recall)

mean_recall_10 = sum(recalls)/len(recalls) if recalls else 0.0

# Balance metric: fraction of queries whose top10 contains both K and P test types
both_count = 0
for ex in train:
    q = ex['query']
    preds = recommend(q, top_k=10)
    has_k = False
    has_p = False
    for p in preds:
        tlist = p.get('test_type') or []
        # test_type entries like 'K' or 'P' or descriptive; normalize
        for t in tlist:
            if isinstance(t,str) and 'k' in t.lower():
                has_k = True
            if isinstance(t,str) and 'p' in t.lower():
                has_p = True
    if has_k and has_p:
        both_count += 1

balance_fraction = both_count / len(train) if train else 0.0

# Example query check
example_q = "Need a Java developer who is good in collaborating with external teams and stakeholders."
ex_preds = recommend(example_q, top_k=10)
ex_has_k = 0
ex_has_p = 0
k_items = []
p_items = []
for p in ex_preds:
    types = p.get('test_type') or []
    found_k = any(('k' in str(t).lower()) for t in types)
    found_p = any(('p' in str(t).lower()) for t in types)
    if found_k:
        ex_has_k += 1
        k_items.append(p.get('assessment_id') or p.get('url'))
    if found_p:
        ex_has_p += 1
        p_items.append(p.get('assessment_id') or p.get('url'))

# write report
out = {
    'mean_recall@10': mean_recall_10,
    'balance_fraction_top10_contains_K_and_P': balance_fraction,
    'example_query': example_q,
    'example_top10_K_count': ex_has_k,
    'example_top10_P_count': ex_has_p,
    'example_top10_K_items': k_items[:10],
    'example_top10_P_items': p_items[:10]
}
print(json.dumps(out, indent=2))

with open(DATA / 'balance_report.json','w',encoding='utf-8') as f:
    json.dump(out, f, indent=2, ensure_ascii=False)
print('Wrote data/balance_report.json')
