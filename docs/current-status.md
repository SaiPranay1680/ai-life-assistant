# Current implementation status

Last reviewed: 2026-09-18.

The repository contains a working FastAPI backend in `backend/`, alongside the Next.js frontend in `apps/web/`.

Implemented:

- Email/password registration and login with JWT access tokens.
- One personal workspace per user; document, action, reminder, and privacy queries are scoped to it.
- PDF, JPEG, and PNG upload with size/signature validation, duplicate detection, local storage, and basic malware checks.
- Asynchronous Celery/Redis document processing, PyMuPDF extraction, RapidOCR fallback, human review, and rule-based actions.
- In-app reminder records and JSON data export at `GET /privacy/export`.
- Configurable explicit CORS allow-list via `CORS_ALLOW_ORIGINS`.

Not implemented:

- Password reset, OIDC, S3 storage, email/push delivery, production malware scanning, and RAG. The assistant screen still uses fixtures.

The older roadmap documents describe the original mock-first plan. This page reflects the code currently in the repository.
