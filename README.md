# Pacioli

Personal finance application for budgeting and expense tracking.

- **Backend**: FastAPI + SQLite (money stored as integer cents, versioned
  migrations, recurring transaction materialization, automatic daily backups)
- **Frontend**: React + TypeScript + Vite, styled with Tailwind CSS v4 and
  shadcn/ui, charts with Recharts, server state with TanStack Query
- **AI assistant**: per-month chat powered by a local Ollama model with
  financial context (summary, budget execution, conversation history)

## Requirements

- Python 3.11+
- Node.js 22+
- [Ollama](https://ollama.com) (optional, only for the AI assistant)

## Setup

```bash
# Backend
cd backend
python3 -m venv .venv
.venv/bin/pip install -e ".[dev]"

# Frontend
cd ../frontend
npm install
```

## Development

```bash
./dev.sh
```

Boots the API on http://localhost:8000 (interactive docs at `/docs`) and the
Vite dev server on http://localhost:5173, which proxies `/api/*` to the
backend. Ctrl+C stops both.

## Production (single process)

```bash
cd frontend && npm run build && cd ..
backend/.venv/bin/uvicorn app.main:app --app-dir backend --port 8000
```

When `frontend/dist` exists the backend serves the built SPA at
http://localhost:8000 (API stays under `/api`). This is how the desktop-era
workflow maps to a web app: one process, one port.

## Data

The SQLite database lives at `~/.local/share/pacioli/pacioli.db`
(`XDG_DATA_HOME` overrides the base; `PACIOLI_DATA_DIR` overrides it all).
It is fully compatible with the old desktop app's database: migrations run
automatically at startup, and a legacy `data/budget.db` is imported once if
present. Daily backups with 10-file rotation live in
`~/.local/share/pacioli/backups/`.

## AI assistant

Configure the Ollama connection from the chat page (gear icon): model, URL,
timeout, temperature, max tokens and thinking effort. The default is a
non-existent `qwen2.5:3b`, so point it at a model you have pulled, e.g.
`qwen3:8b` or any Qwen3/DeepSeek-R1 thinking model (set *thinking* to `low`
for a good speed/quality balance).

## Testing and quality

```bash
# Backend
cd backend && .venv/bin/ruff check . && .venv/bin/mypy app tests && .venv/bin/pytest -q

# Frontend
cd frontend && npx tsc -b && npm run lint && npm run build
```

## API overview

All endpoints live under `/api`:

| Prefix         | Description                                        |
|----------------|----------------------------------------------------|
| `/api/categories` | Category and subcategory CRUD                   |
| `/api/transactions` | Monthly CRUD + recurring materialization       |
| `/api/budgets` | Monthly budget upsert/delete per category           |
| `/api/reports` | Summary, yearly series, spending, budget vs actual, CSV |
| `/api/chat`    | Per-month chat with the AI assistant                |
| `/api/ai`      | AI configuration and connection test                |

Money amounts are serialized as fixed-precision strings (e.g. `"1234.56"`)
to avoid JSON float64 rounding. The API is fully documented at `/docs`.
