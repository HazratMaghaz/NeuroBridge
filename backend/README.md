# CNS-MultiModalAI — Backend API

> ⚠️ **RESEARCH PROTOTYPE** — This API is a proof-of-concept built during academic thesis
> research.  The underlying models are GBM/LGG-focused and output
> *GBM-like vs LGG-like similarity scores only*.  They are **not** a
> pan-CNS classifier and are **not** intended for clinical diagnosis or
> patient management.

---

## Overview

A minimal [FastAPI](https://fastapi.tiangolo.com/) backend that exposes the
frozen `cns_multimodalai` inference package to a GUI front-end.

| Endpoint | Method | Purpose |
|---|---|---|
| `/api/health` | `GET` | Service status and project metadata |
| `/api/infer/rna` | `POST` | Upload RNA-seq CSV → save to run folder |
| `/api/infer/patches` | `POST` | Upload patch ZIP → extract to run folder |

All outputs land under `results/gui_mvp_runs/` (timestamped sub-folders).

---

## Quick Start

### 1. Install dependencies

```bash
# From the project root
pip install -r backend/requirements.txt
```

> **Note:** The `src/cns_multimodalai` package is added to `sys.path`
> automatically by `backend/main.py`. You do **not** need to `pip install`
> it unless you prefer to.

### 2. Start the development server

```bash
# From the project root
uvicorn backend.main:app --host 0.0.0.0 --port 8000 --reload
```

The `--reload` flag auto-restarts the server on code changes.
**Remove it for any non-development deployment.**

### 3. Browse the interactive docs

Open [http://localhost:8000/docs](http://localhost:8000/docs) (Swagger UI)
or [http://localhost:8000/redoc](http://localhost:8000/redoc) (ReDoc).

---

## File Structure

```
backend/
├── main.py                        # FastAPI app & CORS middleware
├── requirements.txt               # Pinned runtime deps
├── README.md                      # This file
└── app/
    ├── __init__.py
    ├── routes/
    │   ├── __init__.py
    │   ├── health.py              # GET /api/health
    │   ├── infer_rna.py           # POST /api/infer/rna
    │   └── infer_patches.py       # POST /api/infer/patches
    └── services/
        ├── __init__.py
        └── inference_service.py   # Thin wrapper; placeholder model calls
```

---

## Enabling Real Inference (after MVP)

Actual model calls are **commented out** in `app/services/inference_service.py`.
To enable them:

1. Ensure model weights are present (see `src/cns_multimodalai/config.py`).
2. Open `backend/app/services/inference_service.py`.
3. Uncomment the **`run_rna_inference()`** block in `handle_rna_upload()`.
4. Uncomment the **`predict_from_patch_folder()`** block in `handle_patch_upload()`.
5. Restart the server.

> ⚠️ CTransPath feature extraction requires a GPU and the model checkpoint
> at `models/weights/ctranspath/ctranspath.pth`.

---

## Output Layout

```
results/
└── gui_mvp_runs/
    ├── rna_20260609T120000Z/
    │   ├── <uploaded>.csv           # saved input
    │   └── (inference outputs when enabled)
    └── patches_20260609T120500Z/
        ├── patches/                 # extracted images
        └── (inference outputs when enabled)
```

---

## Limitations

- Upload size limits: CSV ≤ 500 MB, patch ZIP ≤ 2 GB.
- CORS is set to `allow_origins=["*"]` for MVP convenience — restrict before
  any real deployment.
- No authentication — do not expose this server on a public network.
