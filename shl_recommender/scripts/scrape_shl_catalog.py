"""
Lightweight scraper for SHL product catalog.

Usage:
  python scrape_shl_catalog.py            # crawl and write data/shl_assessments.json
  python scrape_shl_catalog.py --embeddings  # also compute embeddings (requires sentence-transformers)

Notes:
- Respects a short delay between requests. Be considerate of site policies.
- The script is conservative: it finds product links containing '/product-catalog/view/'.
- It filters out items whose title/URL contain 'solution' or 'pre-packaged'.
"""
import requests
from bs4 import BeautifulSoup
import time
import json
import os
from urllib.parse import urljoin, urlparse
import argparse

START_URL = 'https://www.shl.com/solutions/products/product-catalog/'
OUT_PATH = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'data', 'shl_assessments.json')

HEADERS = {
    'User-Agent': 'Mozilla/5.0 (compatible; SHL-Scraper/1.0; +https://github.com/)'
}

def is_product_link(href):
    if not href:
        return False
    return '/product-catalog/view/' in href

def is_prepackaged_item(info: dict):
    """Detect whether an item belongs to Pre-packaged Job Solutions category.

    We avoid excluding items just because they contain the word 'solution' in the
    title or URL. Instead, look for explicit 'pre-packaged' markers in title,
    full_description, or page text (if present). This reduces false positives.
    """
    title = (info.get('description') or '').lower()
    full = (info.get('full_description') or '').lower()
    url = (info.get('url') or '').lower()

    # explicit phrases
    phrases = ['pre-packaged job solution', 'pre-packaged job solutions', 'pre-packaged solution', 'prepackaged']
    for ph in phrases:
        if ph in title or ph in full or ph in url:
            return True

    # if the page text mentions 'pre-packaged' nearby 'job' or 'solutions'
    if 'pre-packaged' in full or 'prepackaged' in full:
        return True

    return False

def fetch(url, session):
    try:
        r = session.get(url, headers=HEADERS, timeout=15)
        r.raise_for_status()
        return r.text
    except Exception as e:
        print('Fetch failed', url, e)
        return None

def extract_product_info(url, session):
    html = fetch(url, session)
    if not html:
        return None
    soup = BeautifulSoup(html, 'html.parser')
    # heuristics: title from <h1> or <title>
    title_tag = soup.find('h1')
    title = title_tag.get_text(strip=True) if title_tag else (soup.title.string.strip() if soup.title and soup.title.string else '')
    # description: prefer article/main paragraphs
    desc = ''
    main = soup.find('main') or soup.find('article') or soup
    paragraphs = main.find_all('p') if main else []
    if paragraphs:
        desc = '\n\n'.join(p.get_text(strip=True) for p in paragraphs)
    else:
        # fallback meta description
        meta = soup.find('meta', attrs={'name': 'description'})
        desc = meta['content'].strip() if meta and meta.get('content') else ''

    # try to glean duration/test_type from page text (best-effort)
    duration = None
    import re
    m = re.search(r"(\d{1,3})\s*minutes", desc, re.I)
    if m:
        duration = int(m.group(1))

    # construct assessment_id from last URL segment
    parsed = urlparse(url)
    seg = parsed.path.rstrip('/').split('/')[-1]
    assessment_id = seg

    return {
        'url': url,
        'assessment_id': assessment_id,
        'description': title,
        'full_description': desc,
        'duration': duration,
        'test_type': [],
    }

def crawl(start_url, delay=0.5, max_pages=200):
    session = requests.Session()
    visited_pages = set()
    product_urls = set()
    to_visit = [start_url]

    while to_visit and len(visited_pages) < max_pages:
        url = to_visit.pop(0)
        if url in visited_pages:
            continue
        print('Visiting', url)
        html = fetch(url, session)
        if not html:
            visited_pages.add(url)
            continue
        soup = BeautifulSoup(html, 'html.parser')
        visited_pages.add(url)

        # find product links
        for a in soup.find_all('a', href=True):
            href = a['href']
            full = urljoin(url, href)
            if is_product_link(full):
                product_urls.add(full.split('?')[0])
            # also follow pagination or product-catalog list pages
            # naive rule: same base path containing 'product-catalog' and not a product detail
            if 'product-catalog' in full and full not in visited_pages and full not in to_visit:
                # avoid following detail pages repeatedly
                to_visit.append(full)

        time.sleep(delay)

    print('Found', len(product_urls), 'product urls')
    products = []
    for i, p in enumerate(sorted(product_urls)):
        print(f'Extracting ({i+1}/{len(product_urls)})', p)
        info = extract_product_info(p, session)
        if not info:
            continue
        if is_prepackaged_item(info):
            print('Skipping pre-packaged item:', info.get('description'))
            continue
        products.append(info)
        time.sleep(delay)

    return products

def compute_and_save_embeddings(docs, out_embeddings_path):
    try:
        from sentence_transformers import SentenceTransformer
        import numpy as np
    except Exception as e:
        print('Embeddings unavailable (install sentence-transformers):', e)
        return False
    model = SentenceTransformer('intfloat/e5-small-v2')
    texts = [d.get('full_description') or d.get('description') or '' for d in docs]
    emb = model.encode(texts, show_progress_bar=True)
    np.save(out_embeddings_path, emb)
    print('Saved embeddings to', out_embeddings_path)
    return True

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--start-url', default=START_URL)
    parser.add_argument('--out', default=OUT_PATH)
    parser.add_argument('--delay', type=float, default=0.2)
    parser.add_argument('--max-pages', type=int, default=500)
    parser.add_argument('--embeddings', action='store_true', help='Compute embeddings (requires sentence-transformers)')
    args = parser.parse_args()

    os.makedirs(os.path.dirname(args.out), exist_ok=True)
    products = crawl(args.start_url, delay=args.delay, max_pages=args.max_pages)

    out = {'recommended_assessments': products}
    with open(args.out, 'w', encoding='utf-8') as f:
        json.dump(out, f, indent=2, ensure_ascii=False)
    print('Wrote', len(products), 'assessments to', args.out)

    if args.embeddings and products:
        emb_path = os.path.join(os.path.dirname(args.out), 'doc_embeddings.npy')
        compute_and_save_embeddings(products, emb_path)

if __name__ == '__main__':
    main()
