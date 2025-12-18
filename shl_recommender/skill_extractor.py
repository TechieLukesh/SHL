import os
import json
import re
from pathlib import Path

ROOT = Path(__file__).parent
DATA = ROOT / 'data'
ASSESS_PATH = DATA / 'shl_assessments.json'
TRAIN_PATH = DATA / 'train.json'
OUT_TRAIN_SKILLS = DATA / 'train_skills.json'

# Few-shot prompt pieces (kept here for clarity)
SYSTEM_PROMPT = "You are a precise extractor of skills and assessment tags. Output JSON array of short skill tokens. Only output JSON array. If no skills, output []."
EXAMPLE_QUERY = 'Job description: "We seek a backend developer with Python, Flask, REST APIs, SQL and strong problem solving ability."\nOutput:\n["python","flask","rest apis","sql","problem solving"]'

COMMON_SKILLS = [
    'python','java','javascript','c#','c++','sql','excel','power bi','react','angular','nodejs','node','django','flask','rest api','rest apis','aws','azure','gcp','docker','kubernetes','html','css','typescript','php','ruby','go','scala','r','matlab','spark','hadoop','nlp','nlp','machine learning','deep learning','data analysis','data entry','communication','leadership','management','sales','marketing','customer service'
]

def fallback_extract(text):
    t = (text or '').lower()
    found = []
    for sk in COMMON_SKILLS:
        if sk in t:
            found.append(sk)
    # also extract capitalized tech tokens like 'SQL', 'C++' via regex
    caps = re.findall(r"\b[A-Za-z\+\#]{2,}\b", text or '')
    for c in caps:
        s = c.strip()
        if len(s) <= 1:
            continue
        low = s.lower()
        if low not in found and any(ch.isalpha() for ch in s):
            found.append(low)
    # normalize common forms
    normalized = []
    for f in found:
        f = f.replace('nodejs', 'javascript')
        f = f.replace('node', 'javascript')
        f = f.replace('rest api', 'rest apis')
        f = f.replace('csharp', 'c#')
        if f not in normalized:
            normalized.append(f)
    return normalized

def try_openai_extract(text):
    try:
        import openai
    except Exception:
        return None  # signal not available
    key = os.environ.get('OPENAI_API_KEY') or os.environ.get('OPENAI_KEY')
    if not key:
        return None
    openai.api_key = key
    prompt = SYSTEM_PROMPT + "\n\n" + EXAMPLE_QUERY + "\n\nUser query to run: \"" + text.replace('"','\"') + "\"\nOutput:"
    try:
        resp = openai.Completion.create(model='gpt-3.5-turbo', prompt=prompt, max_tokens=200, temperature=0)
        txt = resp.choices[0].text.strip()
        # attempt to parse JSON array
        import json as _json
        try:
            arr = _json.loads(txt)
            if isinstance(arr, list):
                return [str(a).strip().lower() for a in arr if a]
        except Exception:
            # try to extract bracketed content
            m = re.search(r"\[(.*)\]", txt, re.S)
            if m:
                inner = m.group(0)
                try:
                    arr = _json.loads(inner)
                    return [str(a).strip().lower() for a in arr if a]
                except Exception:
                    return None
    except Exception:
        return None
    return None

def extract_skills(text):
    # try LLM first (if available), otherwise fallback
    skills = try_openai_extract(text)
    if skills is not None:
        if skills:
            return skills
        # if LLM returned empty list, accept
        return []
    return fallback_extract(text)

def update_assessments_with_skills():
    if not ASSESS_PATH.exists():
        print('Assessments file not found at', ASSESS_PATH)
        return
    data = json.loads(ASSESS_PATH.read_text(encoding='utf-8'))
    changed = 0
    for item in data.get('recommended_assessments', []):
        src = (item.get('description') or '') + ' ' + ' '.join(item.get('test_type', []))
        skills = extract_skills(src)
        if skills:
            item['skills'] = skills
            changed += 1
        else:
            item['skills'] = []
    ASSESS_PATH.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding='utf-8')
    print(f'Updated {changed} assessments with extracted skills')

def extract_train_skills():
    if not TRAIN_PATH.exists():
        print('Train file not found at', TRAIN_PATH)
        return
    train = json.loads(TRAIN_PATH.read_text(encoding='utf-8'))
    out = []
    for ex in train:
        q = ex.get('query')
        skills = extract_skills(q)
        out.append({'query': q, 'skills': skills})
    OUT_TRAIN_SKILLS.write_text(json.dumps(out, indent=2, ensure_ascii=False), encoding='utf-8')
    print(f'Wrote train skills for {len(out)} examples to {OUT_TRAIN_SKILLS}')

if __name__ == '__main__':
    print('Running skill extractor. OpenAI use is optional; falling back to regex if unavailable.')
    update_assessments_with_skills()
    extract_train_skills()
