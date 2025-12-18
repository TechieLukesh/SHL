import json
from pathlib import Path

BASE = Path(__file__).resolve().parents[1]  # shl_recommender
DATA = BASE / "data"

auto_file = DATA / "remap_report_auto.json"
train_file = DATA / "train.json"
out_file = DATA / "train_remapped.json"

with auto_file.open("r", encoding="utf-8") as f:
    auto = json.load(f)

mapping = {}
# accept mapped entries with score >= 0.4
for entry in auto.get("mapped", []):
    if entry.get("score", 0) >= 0.4 and entry.get("original"):
        mapping[entry["original"].strip()] = entry.get("mapped_to")
# accept auto_suggested with score >= 0.4
for entry in auto.get("auto_suggested", []):
    if entry.get("score", 0) >= 0.4 and entry.get("original"):
        mapping[entry["original"].strip()] = entry.get("best_match")

print(f"Loaded {len(mapping)} auto-mappings")

with train_file.open("r", encoding="utf-8") as f:
    train = json.load(f)

changed = 0
for rec in train:
    new_labels = []
    seen = set()
    for lab in rec.get("labels", []):
        if isinstance(lab, str) and lab.startswith("UNMAPPED:"):
            url = lab.split("UNMAPPED:", 1)[1].strip()
            mapped = mapping.get(url)
            if mapped:
                lab = mapped
        # avoid duplicates
        if lab not in seen:
            new_labels.append(lab)
            seen.add(lab)
    if new_labels != rec.get("labels", []):
        changed += 1
        rec["labels"] = new_labels

with out_file.open("w", encoding="utf-8") as f:
    json.dump(train, f, indent=2, ensure_ascii=False)

print(f"Wrote {out_file} ({len(train)} records), updated {changed} records")
