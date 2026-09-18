# Testing and quality gates

Backend tests live in `backend/tests` and cover file validation, extraction normalization, action suggestion rules, and CORS preflight configuration.

Run them with:

```bash
cd backend
pytest
```

Frontend quality checks:

```bash
cd apps/web
npm run lint
npm run typecheck
npm run build
```

The Playwright smoke test starts the Next.js app, mocks the API boundary, registers a user, and verifies the dashboard path. Run it with `npm run e2e` after installing dependencies and the Chromium browser.

GitHub Actions runs the backend suite, frontend quality checks, and Chromium E2E test for pull requests and pushes to `main` or `stg-integration`.
