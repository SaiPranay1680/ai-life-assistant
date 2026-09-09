# Troubleshooting

## Frontend will not start

**Symptom:** `npm run dev` fails or port 3000 in use.  
**Check:** Another Next/uvicorn process. Change nothing in code; stop the other process or use a different port.  
**Heap errors during install:** `$env:NODE_OPTIONS='--max-old-space-size=8192'` then `npm install`.

## Blank page or infinite “Loading workspace…”

**Cause:** `AuthProvider` hydrates from `localStorage` on a timeout; `AppShell` waits for `ready && user`.  
**Fix:** Confirm JS is enabled. Clear site data if `ala-auth-user` is corrupted JSON. Sign in again.

## Redirect loop between `/` and `/login`

**Cause:** User in storage but guard failing, or opposite.  
**Fix:** Application tab → Local Storage → delete `ala-auth-user` and `ala-token`.

## Login always succeeds / feels insecure

**Expected.** Mock auth only checks email format and password length. Do not expose this build as a real product.

## Upload does nothing / file rejected

Allowed: PDF, JPG, PNG, ≤ 20 MB. Check the error under the drop zone. Browser file picker must be used; drag-and-drop needs the file types above.

## Processing never reaches review

Steps advance on a timer (~900 ms × remaining steps + 700 ms). If you stay on the page, you should land on `/documents/review`. If you navigate away, the timer unmounts.

## Assistant always gives the same fallback

Only exact keys in `src/data/messages.json` `replies` (trimmed) have custom answers. Seeded first question is built into React state, not only JSON.

## Dashboard still says “Anita”

Display name comes from `src/data/dashboard.json` `user.name`, not from the email field.

## `NEXT_PUBLIC_API_URL` has no effect

Mock services do not call Axios. Changing the env var does not load real data until services are wired.

## TypeScript / ESLint

```bash
cd apps/web
npm run lint
npm run typecheck
```

React 19 lint forbids **synchronous** `setState` inside `useEffect`. Hydrate auth with `setTimeout(0)` or initialize from a child that receives data as props (see review page `ReviewForm`).

## Cannot delete `backend/.venv` on Windows (historical)

Python/Celery locked `.pyd` files. Stop those PIDs, then delete. The backend folder is gone in the current tree.

## Docker commands fail

Docker Desktop was not installed on at least one developer machine. Frontend does not need Docker.

## Chrome DevTools / MCP cannot upload files

Some automation hosts block paths outside a configured workspace. Use the file picker locally, or open `/documents/processing?file=your.pdf`.

## Need to reset demo data

JSON fixtures are in source control. User-specific mock state is only `localStorage`. Clearing it resets login, not documents (documents are not user-written).
