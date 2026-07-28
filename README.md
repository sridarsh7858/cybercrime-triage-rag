# Cybercrime Triage AI

A traditional RAG pipeline for triaging Indian cybercrime complaints. A citizen's
narrative (plus an optional screenshot, read with OCR) is matched against a vector store
of historical complaints, and a local Llama 3.2 model produces the triage response.

**Stack:** FastAPI · LangChain · ChromaDB (SQLite) · Ollama (`nomic-embed-text` +
`llama3.2`) · EasyOCR · React + Vite

---

## Important: the vector store is not in this repo

`data/` is gitignored. The ChromaDB index is ~1.8 GB of generated files — far past
GitHub's 100 MB per-file limit — so it is rebuilt locally with `scripts/build_db.py`
instead of being committed.

The API loads the store at startup (`app/services/chroma_service.py`) and raises
`RuntimeError` if it is missing or empty, so **step 3 below has to happen before you can
run the backend.**

---

## 1. Prerequisites

- Python 3.12 (see `.python-version`)
- Node 18+ (for the frontend)
- [Ollama](https://ollama.com) running locally, with both models pulled:

  ```bash
  ollama pull nomic-embed-text
  ollama pull llama3.2
  ollama list          # confirm both appear
  ```

## 2. Install

```bash
python -m venv .venv
.venv\Scripts\activate          # Windows;  source .venv/bin/activate on macOS/Linux
pip install -r requirements.txt
```

## 3. Build the vector store (required)

Put a complaints CSV in `data/`, then:

```bash
python scripts/build_db.py --csv "data/your-complaints.csv"
```

Start with a small run to confirm Ollama is reachable before committing to the full
ingest:

```bash
python scripts/build_db.py --csv "data/your-complaints.csv" --max-rows 5000
```

The output lands in `data/ChromaDB_Indian/`, which is where `app/core/config.py`
expects it.

### Expected CSV schema

One content column — **`complaint_text`** — is embedded and searched. These columns are
stored as metadata alongside each vector (see `METADATA_COLUMNS` in
`scripts/build_db.py`):

`complaint_id`, `primary_category`, `sub_category`, `severity_level`, `priority`,
`amount_lost`, `platform`, `routing_department`, `jurisdiction`, `keywords`,
`incident_date`, `user_name`, `user_city`

### Options

| flag | meaning |
| --- | --- |
| `--csv PATH` | source CSV (default `data/cybercrime_complaints_300k_fixed.csv`) |
| `--db-dir PATH` | where to persist the store (default `data/ChromaDB_Indian`) |
| `--max-rows N` | ingest only the first N rows |
| `--batch-size N` | documents per embedding request (default 200) |
| `--fresh` | delete any existing store and start from row 0 |

The ingest is **resumable**. Progress is written to
`data/ChromaDB_Indian/ingest_checkpoint.json` after every batch, so an interrupted run
picks up where it stopped when you re-run the same command. Use `--fresh` to start over.
A full 300k-row build takes a few hours on CPU.

## 4. Run the backend

```bash
uvicorn app.main:app --reload
```

On a successful start you'll see:

```
[chroma] Collection 'langchain' ready with N documents
```

- Health check: <http://localhost:8000/health>
- Interactive docs: <http://localhost:8000/docs>
- Main endpoint: `POST /api/v1/analyze` — form fields `query` (text) and/or `file` (image)

## 5. Run the frontend

```bash
cd frontend
npm install
cp .env.example .env      # VITE_API_URL, defaults to http://localhost:8000
npm run dev
```

The dev server runs at <http://localhost:5173>, which is already allowed by the
backend's CORS config.

---

## Layout

```
app/
  api/        FastAPI routes (analyze_router.py)
  core/       config.py — paths, model names, collection name
  schemas/    request/response models
  services/   chroma_service.py, rag_service.py, ocr_service.py
frontend/     React + Vite client
scripts/
  build_db.py builds the ChromaDB index from a CSV
data/         gitignored — CSVs, the generated index, temp uploads
```
