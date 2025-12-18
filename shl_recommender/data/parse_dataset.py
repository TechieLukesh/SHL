import pandas as pd
import json
import os
from urllib.parse import urlparse

fn = os.path.join(os.path.dirname(__file__), "dataset.xlsx")
out_dir = os.path.dirname(__file__)

# load catalog to map urls/names -> assessment_id when possible
CATALOG_PATH = os.path.join(os.path.dirname(__file__), 'shl_assessments.json')
catalog_map = {}
name_to_id = {}
if os.path.exists(CATALOG_PATH):
    try:
        with open(CATALOG_PATH, 'r', encoding='utf-8') as f:
            cat = json.load(f).get('recommended_assessments', [])
            for item in cat:
                aid = item.get('assessment_id') or (item.get('url') or '').rstrip('/').split('/')[-1]
                if not aid:
                    continue
                catalog_map[aid] = item
                name = (item.get('description') or '').strip().lower()
                if name:
                    name_to_id[name] = aid
    except Exception:
        pass

def find_query_column(cols):
    q_candidates = [c for c in cols if any(k in c.lower() for k in ("query","text","description","jd","job"))]
    return q_candidates[0] if q_candidates else cols[0]

def find_label_columns(cols):
    label_keywords = ("label", "relev", "assessment", "assessment_url", "assessmenturl", "relevant")
    return [c for c in cols if any(k in c.lower() for k in label_keywords)]

def read_excel_safely(path, sheet):
    try:
        return pd.read_excel(path, sheet_name=sheet)
    except Exception:
        # fallback: let pandas infer with engine
        return pd.read_excel(path, sheet_name=sheet, engine='openpyxl')

def normalize_val(v):
    if pd.isna(v):
        return None
    if isinstance(v, str):
        s = v.strip()
        return s if s != "" else None
    return str(v)

def parse():
    if not os.path.exists(fn):
        print("dataset.xlsx not found at", fn)
        return

    xls = pd.ExcelFile(fn)
    train_rows = []
    test_rows = []

    for sheet in xls.sheet_names:
        df = read_excel_safely(fn, sheet)
        cols = list(df.columns)
        cols_lower = [c.lower() for c in cols]

        label_cols = find_label_columns(cols)
        qcol = find_query_column(cols)

        if label_cols:
            for _, r in df.iterrows():
                query = normalize_val(r.get(qcol))
                if not query:
                    continue
                labels = []
                for lc in label_cols:
                    val = r.get(lc)
                    v = normalize_val(val)
                    if not v:
                        continue
                    # If comma-separated string, split
                    if isinstance(v, str) and "," in v:
                        parts = [p.strip() for p in v.split(",") if p.strip()]
                        labels.extend(parts)
                    else:
                        labels.append(v)

                # dedupe labels while preserving order
                seen = set()
                cleaned = []
                for L in labels:
                    if L in seen:
                        continue
                    seen.add(L)
                    cleaned.append(L)

                # Attempt to canonicalize labels to assessment_id when possible
                mapped = []
                for L in cleaned:
                    l = L.strip()
                    # if URL, try extract last path segment
                    try:
                        up = urlparse(l)
                        if up.scheme in ("http", "https"):
                            seg = (up.path or '').rstrip('/').split('/')[-1]
                            if seg in catalog_map:
                                mapped.append(seg)
                                continue
                    except Exception:
                        seg = None
                    # direct match to name -> id
                    key = l.lower()
                    if key in name_to_id:
                        mapped.append(name_to_id[key])
                        continue
                    # otherwise keep original (unmapped) prefixed so downstream can detect
                    mapped.append(f"UNMAPPED:{l}")

                train_rows.append({"query": query, "labels": mapped, "raw_labels": cleaned, "source_sheet": sheet})
        else:
            # unlabeled
            for _, r in df.iterrows():
                query = normalize_val(r.get(qcol))
                if not query:
                    continue
                test_rows.append({"query": query, "source_sheet": sheet})

    os.makedirs(out_dir, exist_ok=True)
    train_path = os.path.join(out_dir, "train.json")
    test_path = os.path.join(out_dir, "test.json")
    with open(train_path, "w", encoding="utf8") as f:
        json.dump(train_rows, f, indent=2, ensure_ascii=False)
    with open(test_path, "w", encoding="utf8") as f:
        json.dump(test_rows, f, indent=2, ensure_ascii=False)

    print("Wrote:", len(train_rows), "train entries and", len(test_rows), "test entries")

if __name__ == '__main__':
    parse()
"""Parse `dataset.xlsx` to extract labeled train queries and unlabeled test queries.

Produces two files in the same folder:
 - labeled.json  -> list of {"query":..., "labels": [assessment_urls or names]}
 - unlabeled.json -> list of {"id":..., "query":...}

The script uses pandas if available, otherwise openpyxl.
Run: `python parse_dataset.py`
"""
from pathlib import Path
import json

try:
    import pandas as pd
except Exception:
    pd = None

ROOT = Path(__file__).parent
XLSX = ROOT / "dataset.xlsx"

def read_excel(path):
    if pd is None:
        # minimal fallback using openpyxl
        from openpyxl import load_workbook
        wb = load_workbook(path)
        sheet = wb.active
        rows = list(sheet.values)
        headers = [str(h).strip() for h in rows[0]]
        data = [dict(zip(headers, r)) for r in rows[1:]]
        return data
    else:
        df = pd.read_excel(path)
        return df.to_dict(orient="records")

def main():
    if not XLSX.exists():
        print(f"Missing {XLSX}, nothing to do")
        return

    rows = read_excel(XLSX)

    labeled = []
    unlabeled = []

    # Heuristics: look for columns containing 'query', 'text', 'label', 'labels', 'id'
    for r in rows:
        keys = {k.lower(): k for k in r.keys()}
        q_key = None
        id_key = None
        label_key = None
        for k in keys:
            if 'query' in k or 'text' in k or 'job' in k:
                q_key = keys[k]
            if k in ('id', 'identifier'):
                id_key = keys[k]
            if 'label' in k or 'gold' in k or 'target' in k:
                label_key = keys[k]

        query = r.get(q_key) if q_key else None
        labels = r.get(label_key) if label_key else None
        rid = r.get(id_key) if id_key else None

        if query and labels:
            # assume labels are semicolon/comma separated
            if isinstance(labels, str):
                labs = [x.strip() for x in labels.replace(';', ',').split(',') if x.strip()]
            elif isinstance(labels, (list, tuple)):
                labs = list(labels)
            else:
                labs = [str(labels)]
            labeled.append({"query": str(query).strip(), "labels": labs})
        elif query:
            unlabeled.append({"id": rid, "query": str(query).strip()})

    with open(ROOT / "labeled.json", "w", encoding="utf-8") as f:
        json.dump(labeled, f, indent=2, ensure_ascii=False)

    with open(ROOT / "unlabeled.json", "w", encoding="utf-8") as f:
        json.dump(unlabeled, f, indent=2, ensure_ascii=False)

    print(f"Wrote {len(labeled)} labeled and {len(unlabeled)} unlabeled queries")

if __name__ == '__main__':
    main()
