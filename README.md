# AI Life Assistant

Personal Action Intelligence Platform.

**Core flow:** Upload → Understand → Extract → Action → Confirm → Remind → Ask

## Documentation (start here)

Full KT, architecture, setup, and decisions: **[docs/README.md](./docs/README.md)**

## Run the frontend

```bash
cd apps/web
cp .env.example .env.local
npm install
npm run dev
```

Open http://localhost:3000 — any valid email and a password of 6+ characters. Data is mocked until FastAPI exists.
