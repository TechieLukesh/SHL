Pipeline summary

Commands

- Scrape SHL catalog (writes data/shl_assessments.json):

  .venv\Scripts\python scripts\scrape_shl_catalog.py

- Build embeddings (done automatically on import) and persist to data/doc_embeddings.npy

- Build vector store (FAISS preferred, sklearn fallback):

  .venv\Scripts\python data\build_vector_store.py

- Run RAG recommendation (retrieval + optional OpenAI synthesis):

  .venv\Scripts\python rag_recommend.py --query "Your job description" --top_k 5

- Parse dataset.xlsx to train/test JSON:

  .venv\Scripts\python data\parse_dataset.py

- Remap UNMAPPED labels (attempt fuzzy + url-segment matching):

  .venv\Scripts\python data\remap_unmapped_labels.py

- Evaluate recommender (Precision@5, MRR) and produce predictions.csv:

  .venv\Scripts\python evaluate.py

Notes

- `data/shl_assessments.json` and `data/doc_embeddings.npy` are persisted in the repo workspace. If you need a submission-ready snapshot, I can create a zip of those files.
- OpenAI synthesis is optional and requires `OPENAI_API_KEY`.
