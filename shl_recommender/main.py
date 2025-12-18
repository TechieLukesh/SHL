import os
import uvicorn
import requests
from bs4 import BeautifulSoup
from fastapi import FastAPI, HTTPException
from models import RecommendationRequest, RecommendationResponse
from recommender import recommend, recommend_balanced
from fastapi.middleware.cors import CORSMiddleware

app = FastAPI()

# Allow requests from your frontend (adjust the origin as needed)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # React dev server
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/health")
def health_check():
    return {"status": "ok"}

@app.post("/recommend", response_model=RecommendationResponse)
def recommend_assessments(payload: RecommendationRequest):
    text = None
    if payload.url:
        try:
            headers = {
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
            }
            resp = requests.get(payload.url, timeout=10, headers=headers)
            resp.raise_for_status()
            soup = BeautifulSoup(resp.text, "html.parser")

            # Try to extract the main article or job description text
            text_candidates = []
            article = soup.find("article")
            if article:
                text_candidates.append(article.get_text(separator=" ").strip())

            # paragraphs
            paragraphs = [p.get_text().strip() for p in soup.find_all("p") if p.get_text().strip()]
            if paragraphs:
                text_candidates.append(" \n".join(paragraphs))

            # common meta description tags
            meta_desc = None
            meta = soup.find("meta", attrs={"name": "description"}) or soup.find("meta", attrs={"property": "og:description"})
            if meta and meta.get("content"):
                meta_desc = meta.get("content").strip()
                text_candidates.append(meta_desc)

            # fallback to full visible text
            full_text = soup.get_text(separator=" ").strip()
            if full_text:
                text_candidates.append(full_text)

            # pick the longest candidate (heuristic)
            text_candidates = [t for t in text_candidates if t]
            if text_candidates:
                text = max(text_candidates, key=lambda s: len(s))
            else:
                raise ValueError("No extractable text found on the page")
        except Exception as e:
            # Return a clear structured error so frontend can display it
            raise HTTPException(status_code=400, detail=f"Failed to fetch or parse URL: {str(e)}")

    # Prefer explicit job_description if provided
    job_text = payload.job_description or text
    if not job_text:
        raise HTTPException(status_code=400, detail="Either `job_description` or `url` must be provided")

    top_k = payload.top_k or 10
    # enforce sensible bounds (min 5, max 10)
    if top_k < 1:
        top_k = 10
    if top_k > 10:
        top_k = 10

    # Collect tuning params if provided (fallback to recommender defaults)
    w_skill = payload.w_skill if payload.w_skill is not None else None
    w_embed = payload.w_embed if payload.w_embed is not None else None
    w_diff = payload.w_diff if payload.w_diff is not None else None
    prefer_ratio = payload.prefer_ratio if payload.prefer_ratio is not None else 0.5

    # Choose the recommendation function based on the `balanced` flag
    if payload.balanced:
        results = recommend_balanced(
            job_text,
            top_k=top_k,
            w_skill=w_skill if w_skill is not None else 0.6,
            w_embed=w_embed if w_embed is not None else 0.4,
            w_diff=w_diff if w_diff is not None else 0.0,
            prefer_ratio=prefer_ratio,
            exclude_prepackaged=payload.exclude_prepackaged,
        )
    else:
        results = recommend(
            job_text,
            top_k=top_k,
            w_skill=w_skill if w_skill is not None else 0.6,
            w_embed=w_embed if w_embed is not None else 0.4,
            w_diff=w_diff if w_diff is not None else 0.0,
            exclude_prepackaged=payload.exclude_prepackaged,
        )

    return {"recommended_assessments": results}

# 👇 Optional for local testing
if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8000))
    uvicorn.run("main:app", host="0.0.0.0", port=port, reload=True)
