"""Remap UNMAPPED: labels in data/train.json to catalog assessment_id using fuzzy-match.

Creates `data/train_remapped.json` and `data/remap_report.json`.
"""
import json
import os
import re
from difflib import SequenceMatcher

ROOT = os.path.dirname(__file__)
TRAIN_IN = os.path.join(ROOT, 'train.json')
TRAIN_OUT = os.path.join(ROOT, 'train_remapped.json')
REPORT_OUT = os.path.join(ROOT, 'remap_report.json')
CATALOG = os.path.join(ROOT, 'shl_assessments.json')

def norm(s):
    if not s:
        return ''
    s = s.lower()
    s = re.sub(r'[^0-9a-z ]+', ' ', s)
    s = re.sub(r'\s+', ' ', s).strip()
    return s

def best_match(label, candidates):
    best_id = None
    best_score = 0.0
    for aid, text in candidates.items():
        score = SequenceMatcher(None, label, text).ratio()
        if score > best_score:
            best_score = score
            best_id = aid
    return best_id, best_score

def load_catalog():
    if not os.path.exists(CATALOG):
        return {}
    with open(CATALOG, 'r', encoding='utf-8') as f:
        data = json.load(f).get('recommended_assessments', [])
    cand = {}
    for it in data:
        aid = it.get('assessment_id') or (it.get('url') or '').rstrip('/').split('/')[-1]
        if not aid:
            continue
        desc = it.get('description') or ''
        cand[aid] = norm(desc)
    return cand

def main(threshold=0.4):
    if not os.path.exists(TRAIN_IN):
        print('Missing', TRAIN_IN)
        return
    with open(TRAIN_IN, 'r', encoding='utf-8') as f:
        rows = json.load(f)

    candidates = load_catalog()
    remapped = []
    report = {'remapped': [], 'unresolved': []}
    for ex in rows:
        labels = ex.get('labels', [])
        new_labels = []
        changed = False
        for lab in labels:
            if isinstance(lab, str) and lab.startswith('UNMAPPED:'):
                original = lab.replace('UNMAPPED:', '')
                lbl = norm(original)
                # first try exact match by last URL segment if original looks like a URL
                best_id = None
                score = 0.0
                try:
                    from urllib.parse import urlparse
                    up = urlparse(original)
                    if up.scheme in ('http', 'https'):
                        seg = (up.path or '').rstrip('/').split('/')[-1]
                        if seg in candidates:
                            best_id = seg
                            score = 1.0
                except Exception:
                    pass
                if best_id is None:
                    best_id, score = best_match(lbl, candidates)
                if best_id and score >= threshold:
                    new_labels.append(best_id)
                    report['remapped'].append({'query': ex.get('query'), 'original': original, 'mapped_to': best_id, 'score': score})
                    changed = True
                else:
                    new_labels.append(lab)
                    report['unresolved'].append({'query': ex.get('query'), 'original': original, 'best_match': best_id, 'score': score})
            else:
                new_labels.append(lab)
        if changed:
            ex['labels'] = new_labels
        remapped.append(ex)

    with open(TRAIN_OUT, 'w', encoding='utf-8') as f:
        json.dump(remapped, f, indent=2, ensure_ascii=False)
    with open(REPORT_OUT, 'w', encoding='utf-8') as f:
        json.dump(report, f, indent=2, ensure_ascii=False)
    print('Wrote', TRAIN_OUT, 'and', REPORT_OUT)

if __name__ == '__main__':
    main()
