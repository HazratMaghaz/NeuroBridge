Set the cloned repository root once in your shell:

```bash
export CNS_PROJECT_ROOT="$(git rev-parse --show-toplevel)"
```

# CNS-MultiModalAI Frontend GUI MVP

> ⚠️ **RESEARCH PROTOTYPE** — Outputs GBM-like vs LGG-like similarity for academic
> thesis demonstration only. Not a pan-CNS classifier and not intended for clinical
> diagnosis.

---

## Stack

| Tool | Version | Note |
|---|---|---|
| Next.js | 14.x (App Router) | SSR/CSR hybrid |
| React | 18.x | |
| TypeScript | 5.x | strict mode |
| CSS | Plain CSS (globals.css) | No Tailwind required |

---

## Prerequisites

```bash
# Node.js ≥ 18 required
node --version   # should be ≥ 18

# Install nvm if needed:
curl -o- https://raw.githubusercontent.com/nvm-sh/nvm/v0.39.7/install.sh | bash
nvm install 20
nvm use 20
```

---

## Quick Start

### 1 — Install frontend dependencies

```bash
cd "$CNS_PROJECT_ROOT/frontend"
npm install
```

### 2 — Configure backend URL (optional — default is 127.0.0.1:8000)

```bash
cp .env.example .env.local
# Edit .env.local if your backend is on a different host/port
```

### 3 — Start the backend (in a separate terminal)

```bash
cd "$CNS_PROJECT_ROOT"
# Activate the project venv if needed, then:
uvicorn backend.main:app --host 0.0.0.0 --port 8000 --reload
```

### 4 — Start the frontend dev server

```bash
cd "$CNS_PROJECT_ROOT/frontend"
npm run dev
```

Open **http://localhost:3000** in your browser.

---

## File Structure

```
frontend/
├── package.json
├── next.config.mjs
├── tsconfig.json
├── .env.example          ← copy to .env.local
└── src/
    ├── app/
    │   ├── layout.tsx    ← Root layout, metadata, CSS import
    │   ├── page.tsx      ← Dashboard home page
    │   └── globals.css   ← Design system (dark navy + teal palette)
    └── components/
        ├── WarningBanner.tsx   ← Amber research-prototype disclaimer
        ├── RnaUpload.tsx       ← CSV upload form + options
        ├── ResultCard.tsx      ← Stat blocks, prediction table, download links
        └── CanvasViewer.tsx    ← Morphology canvas image + patient tabs
```

---

## API Integration

| Frontend action | Backend endpoint |
|---|---|
| "Ping API" button | `GET /api/health` |
| RNA upload + run | `POST /api/infer/rna` (multipart) |
| Download result files | `GET /api/results/{run_id}/file?relative_path=...` |

The patch upload card is **visually present but disabled** — it will be
wired to `POST /api/infer/patches` in the next development step.

---

## Environment Variables

| Variable | Default | Description |
|---|---|---|
| `NEXT_PUBLIC_API_BASE_URL` | `http://127.0.0.1:8000` | FastAPI backend base URL |

---

## Known Limitations

- Node.js must be installed separately (not bundled with the project).
- Canvas image display uses a plain `<img>` tag (not `next/image`) to avoid
  remotePatterns configuration complexity in MVP.
- No authentication — do not expose on a public network.
