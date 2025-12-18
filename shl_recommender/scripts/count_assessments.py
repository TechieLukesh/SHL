import json
p = r"C:\Users\BIT\Desktop\SHL Lukesh\shl_recommender\data\shl_assessments.json"
with open(p, 'r', encoding='utf-8') as f:
    data = json.load(f)
print(len(data.get('recommended_assessments', [])))
