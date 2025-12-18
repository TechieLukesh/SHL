@echo off
REM run_backend.bat - one-step batch script to setup venv, install deps, and run uvicorn

SET "SCRIPT_DIR=%~dp0"
REM go to backend folder
cd /d "%SCRIPT_DIR%shl_recommender"

IF NOT EXIST ".venv\Scripts\python.exe" (
  echo Creating virtual environment .venv...
  python -m venv .venv
) ELSE (
  echo Virtual environment exists, reusing .venv
)

echo Upgrading pip and installing dependencies...
.venv\Scripts\python -m pip install --upgrade pip setuptools wheel
.venv\Scripts\python -m pip install -r requirements.txt

echo Starting backend (uvicorn) on http://127.0.0.1:8000 ...
.venv\Scripts\python -m uvicorn main:app --reload --host 127.0.0.1 --port 8000
