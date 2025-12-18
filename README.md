# SHL Assessment Recommender API

![FastAPI](https://img.shields.io/badge/FastAPI-005571?style=for-the-badge&logo=fastapi)
![Python](https://img.shields.io/badge/Python-3776AB?style=for-the-badge&logo=python&logoColor=white)

This is a FastAPI-based backend service that provides SHL assessment recommendations based on a given job description. It uses semantic similarity (via the `sentence-transformers` library) to find the most relevant assessments from a preloaded dataset.

## 🚀 Features

- RESTful API built with FastAPI
- CORS-enabled for frontend integration
- Semantic search using `intfloat/e5-small-v2` embedding model
- Precomputed embeddings for fast recommendations
- Supports POST `/recommend` endpoint with JSON payload

## 📦 Project Structure

shl-recommender/
├── main.py # FastAPI app with CORS and route setup
├── models.py # Pydantic models for request/response validation
├── recommender.py # Embedding-based recommendation logic
├── data/
│ └── shl_assessments.json # SHL assessment data
├── requirements.txt # Python dependencies
└── README.md # This file

## 🎯 API Endpoints

### Health Check

`GET /health`

Local (development): `http://127.0.0.1:8000/health`

{
"status": "ok"
}

Recommend Assessments
POST /recommend

Request:

How It Works
Data Loading: Preloads SHL assessments dataset
Embedding: Uses intfloat/e5-small-v2 model to create embeddings
Recommendation:
Embeds incoming job description
Computes cosine similarity against all assessments
Returns top matches

## Run locally

Below are step-by-step commands for running both the backend (FastAPI) and frontend (Next.js) on Windows. Run these from the repository root (`SHL`).

1. Backend (Python / FastAPI)

Open PowerShell and run:

```powershell
# change to backend folder
cd C:\Users\BIT\Desktop\SHL Lukesh\shl_recommender

# create virtual environment (one-time)
python -m venv .venv

# activate the venv
. .venv\Scripts\Activate.ps1

# upgrade pip and install dependencies
python -m pip install --upgrade pip setuptools wheel
python -m pip install -r requirements.txt

# run the server (development)
python -m uvicorn main:app --reload --host 127.0.0.1 --port 8000
```

Notes:

- If using `cmd.exe` instead of PowerShell, activate the venv with `.venv\Scripts\activate.bat`.
  -- The backend will be available at `http://127.0.0.1:8000` and the health endpoint at `http://127.0.0.1:8000/health`.

### One-command alternative

If you prefer a single command that creates the virtual environment (if missing), installs dependencies, and starts the backend, use one of the helper scripts added to the repository root:

- PowerShell (recommended on Windows):

```powershell
.\run_backend.ps1
```

- CMD (Windows):

```cmd
run_backend.bat
```

Both scripts will operate on the `shl_recommender` folder and start the backend at `http://127.0.0.1:8000`.

2. Frontend (Next.js)

Open a separate terminal (PowerShell or cmd) and run:

```powershell
# change to frontend folder
cd C:\Users\BIT\Desktop\SHL Lukesh\frontend

# install dependencies (one-time)
npm install

# start dev server
npm run dev
```

Notes:

- The Next.js dev server defaults to `http://localhost:3000` unless configured otherwise.
- Keep the frontend dev server running while you work; it will hot-reload on changes.

3. Restarting backend after code changes

If the backend was started before you edited `recommender.py` (or other files), stop the running uvicorn process and restart using the command above so changes are picked up.

4. Optional: run both servers concurrently (WSL / separate terminals)

- Start backend in one terminal and frontend in another. Alternatively use a task runner or terminal multiplexer.

## Author

- **Name:** Lukesh Poddar
- **GitHub:** https://github.com/TechieLukesh
- **Repository for this project:** https://github.com/TechieLukesh/SHL
- **LinkedIn:** https://www.linkedin.com/in/lukeshpoddar/

© 2025 Lukesh Poddar

## Deployment

To deploy a public API endpoint you can either push this repo to a hosting provider (Render / Heroku) or build and run the included Docker image.

Quick Render / Heroku instructions:

- Ensure the repo is on GitHub.
- On Render/Heroku create a new web service and point it to this repo. Use the default build (Python) or Dockerfile. Set the start command to:

```
uvicorn main:app --host 0.0.0.0 --port $PORT
```

Docker example (build & run locally):

```bash
docker build -t shl-recommender:latest .
docker run -p 8000:8000 shl-recommender:latest
```

After deployment your public health endpoint will be `https://<your-service-url>/health` and the recommend endpoint `POST https://<your-service-url>/recommend`.
