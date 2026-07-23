# SA PrepBot

SA PrepBot is an AI-powered emergency preparedness assistant for San Antonio residents. It answers questions about emergency supply kits, evacuation routes, shelters, severe weather alerts, and disaster preparedness using official City of San Antonio (COSA) sources — with verifiable citations.

## MVP Scope

**In Scope**
- City of San Antonio (COSA) emergency preparedness content
- Emergency supply kits and family preparedness plans
- Evacuation routes and shelter locations
- Severe weather alerts and warning systems
- Flood, hurricane, and winter storm preparedness
- Utility and safety guidance during disasters

**Out of Scope**
- General city services not related to emergency preparedness (library hours, dining, parking)
- Sports, tourism, and non-emergency local information
- Real-time or operational information beyond indexed sources
- Any non-COSA or non-preparedness sources

**Refusal Behavior**

The system refuses if no relevant COSA source is retrieved, the question falls outside the emergency preparedness domain, or the answer cannot be supported with at least one citation:

> "I cannot find supporting information in the indexed COSA documents."

## Features

- Grounded answers with inline citations linking to official COSA sources
- Multi-turn conversation — follow-up questions retain prior context
- Clean refusal when a question falls outside the indexed data
- Two-stage retrieval: vector similarity (top 20) → cross-encoder reranker (top 7)
- Streamlit chat interface

## Tech Stack

| Layer | Technology |
|---|---|
| Frontend | Streamlit |
| Backend | FastAPI (Python) |
| RAG Pipeline | LlamaIndex + ChromaDB |
| LLM | OpenAI `gpt-4o-mini` |
| Re-ranker | `cross-encoder/ms-marco-MiniLM-L-12-v2` |

## Data

The index is built from JSONL records in `data/cosa_data/` (not tracked in git — see `.gitignore`). Each record contains a `source_url`, `title`, `record_type`, and `full_body` field. The index is persisted to `src/storage/` (ChromaDB), also not tracked in git.

## Setup

### Prerequisites

- Python 3.10+
- OpenAI API key with access to `gpt-4o-mini`

### 1. Clone and configure environment

```bash
git clone https://github.com/<your-username>/sa-prepbot.git
cd sa-prepbot
cp .env.example .env
```

Edit `.env` and set `OPENAI_API_KEY`.

### 2. Install dependencies

```bash
pip install -r requirements.txt
```

### 3. Add data and build the vector index

Place your COSA JSONL data file(s) in `data/cosa_data/` (e.g. `data/cosa_data/emergency_prep.jsonl`), then build the index (first time only, and any time source data changes):

```bash
cd src
python retrieval.py
```

This wipes and rebuilds `src/storage/`.

### 4. Run the backend (FastAPI + uvicorn)

```bash
cd src
python -m uvicorn app:app --reload
```

Backend runs on `http://127.0.0.1:8000`. Startup confirms: `SA PrepBot ready.`

### 5. Run the frontend (Streamlit)

From the project root (in a separate terminal, with `.env` configured so `BACKEND_URL` points at the running backend):

```bash
streamlit run streamlit_app.py
```

Open the URL Streamlit prints (default `http://localhost:8501`).

## Project Structure

```
sa-prepbot/
├── src/
│   ├── app.py                 # FastAPI backend, /ask endpoint
│   ├── generator.py           # Query engine, prompt template, question condensing
│   ├── ingestion.py           # JSONL/markdown document loading
│   ├── retrieval.py           # ChromaDB index build/load
│   ├── citation_formatter.py  # Citation extraction, refusal handling
│   └── storage/                # ChromaDB persisted index (gitignored)
├── streamlit_app.py           # Streamlit chat frontend
├── data/
│   └── cosa_data/              # COSA JSONL source data (gitignored)
├── tests/
│   └── test_rag.py            # Grounded + refusal test cases
├── requirements.txt
├── .env.example
├── .gitignore
└── README.md
```

## Evaluation

See `tests/test_rag.py` for a grounded + refusal test suite covering emergency preparedness topics (evacuation, shelters, supply kits, weather alerts) alongside out-of-scope refusal cases.
