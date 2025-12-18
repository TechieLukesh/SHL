import json
import csv
import os

try:
    from recommender import recommend
except Exception as e:
    print("Error importing recommend():", e)
    raise

data_dir = os.path.join(os.path.dirname(__file__), "data")
test_path = os.path.join(data_dir, "test.json")
out_json = os.path.join(data_dir, "test_predictions.json")
out_csv = os.path.join(data_dir, "test_predictions.csv")

with open(test_path, "r", encoding="utf8") as f:
    tests = json.load(f)

out = []
for i, item in enumerate(tests):
    q = item.get("query")
    preds = recommend(q, top_k=10)
    preds_out = []
    for p in preds[:5]:
        name = p.get("name") or p.get("description") or p.get("title") or ""
        url = p.get("url") or p.get("link") or ""
        score = p.get("score") if isinstance(p, dict) else None
        aid = p.get('assessment_id')
        if not aid and url:
            aid = url.rstrip('/').split('/')[-1]
        preds_out.append({"assessment_id": aid, "name": name, "url": url, "score": score})
    out.append({"query": q, "predictions": preds_out})

with open(out_json, "w", encoding="utf8") as f:
    json.dump(out, f, indent=2, ensure_ascii=False)

with open(out_csv, "w", newline='', encoding="utf8") as csvfile:
    writer = csv.writer(csvfile)
    writer.writerow(["query_index", "query", "rank", "assessment_name", "assessment_url", "score"])
    for idx, row in enumerate(out):
        for r, p in enumerate(row["predictions"], start=1):
            writer.writerow([idx, row["query"], r, p["assessment_id"], p["name"], p["url"], p["score"]])

print("Wrote predictions to", out_json, "and", out_csv)
