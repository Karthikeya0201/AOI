IC Marking Verifier

Quick start:

1) Install system deps (Debian/Ubuntu):

```bash
sudo apt-get update && sudo apt-get install -y tesseract-ocr libtesseract-dev
```

2) Install Python deps:

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

3) Run server:

```bash
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

Open http://localhost:8000
