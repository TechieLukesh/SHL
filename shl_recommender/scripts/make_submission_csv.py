import json
from pathlib import Path
from recommender import recommend

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / 'data'
OUT = ROOT / 'submission.csv'

# use labeled/test set if present; else use unlabeled
p_test = DATA / 'train_remapped.json'
if not p_test.exists():
    p_test = DATA / 'train.json'

cases = json.loads(p_test.read_text(encoding='utf-8'))

# prepare header: Query + up to 10 Assessment_url columns
with open(OUT, 'w', encoding='utf-8', newline='') as f:
    # write CSV manually
    f.write('Query')
    for i in range(1,11):
        f.write(',Assessment_url_{}'.format(i))
    f.write('\n')
    for ex in cases:
        q = ex.get('query','').replace('\n',' ').replace('\r',' ')
        preds = recommend(q, top_k=10)
        urls = []
        for p in preds:
            u = p.get('url') or ''
            urls.append(u.replace(',', ''))
        # pad to 10
        while len(urls) < 10:
            urls.append('')
        row = '"{}",'.format(q.replace('"','""')) + ','.join('"{}"'.format(u) for u in urls)
        f.write(row + '\n')
print('Wrote submission CSV to', OUT)
