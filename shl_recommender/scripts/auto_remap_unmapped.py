import json
import os
from difflib import SequenceMatcher

ROOT = os.path.join(os.path.dirname(__file__), '..')
DATA = os.path.join(ROOT, 'data')
REPORT = os.path.join(DATA, 'remap_report.json')
OUT = os.path.join(DATA, 'remap_report_auto.json')

with open(REPORT, 'r', encoding='utf-8') as f:
    report = json.load(f)

# load catalog ids and descriptions
catalog = json.load(open(os.path.join(DATA, 'shl_assessments.json'), 'r', encoding='utf-8'))['recommended_assessments']
items = []
for it in catalog:
    aid = it.get('assessment_id') or (it.get('url') or '').rstrip('/').split('/')[-1]
    name = (it.get('description') or '')
    items.append((aid, name))

def norm(s):
    return (s or '').lower().replace('-', ' ').replace('_', ' ').strip()

auto = {'mapped': report.get('remapped', []), 'auto_suggested': []}

for u in report.get('unresolved', []):
    orig = u.get('original') or ''
    # use last path segment or description
    seg = orig.rstrip('/').split('/')[-1].lower()
    seg = seg.replace('%28','(').replace('%29',')')
    best = None
    best_score = 0.0
    for aid, name in items:
        # compare against assessment id and description
        s1 = norm(seg)
        s2 = norm(aid)
        s3 = norm(name)
        # use several similarity checks
        r1 = SequenceMatcher(None, s1, s2).ratio()
        r2 = SequenceMatcher(None, s1, s3).ratio()
        r = max(r1, r2)
        if r > best_score:
            best_score = r
            best = aid
    auto['auto_suggested'].append({'query': u.get('query'), 'original': u.get('original'), 'best_match': best, 'score': best_score})

with open(OUT, 'w', encoding='utf-8') as f:
    json.dump(auto, f, indent=2, ensure_ascii=False)

print('Wrote auto remap report to', OUT)
