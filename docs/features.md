# Features & Functionality

Status legend: **Live (mock)** = in `apps/web` with fixture data. **Planned** = playbook MVP, not coded.

---

## Authentication (mock) — Live

**What:** Email/password form. No real identity provider.

**User flow:** `/login` → validate email + password length ≥ 6 → save user JSON + token in `localStorage` → `/dashboard`. Unauthenticated visits to the shell redirect to `/login`. `/` redirects to dashboard or login.

**Business logic:** Does not verify a real password. Copies persona name from `dashboard.json`.

**Dependencies:** `LoginForm`, `auth.service.ts`, `useAuth`, `AppShell` guard.

**Expected:** Loading state on submit; field errors; form error on throw; privacy footnote on the card.

**Screens:** Login (split navy / form).

**Planned:** OIDC (playbook), register, refresh tokens, workspace creation on first login.

---

## Dashboard — Live

**What:** Action-first home. Three attention cards, upcoming actions, shortcut into the assistant.

**User flow:** After login, see greeting (`Good morning/afternoon/evening` + first name), Secure workspace badge, Upload document.

**Business logic:** Data from `getAttentionCards()` and `getActions()` (JSON). Priorities High/Medium/Low.

**Dependencies:** `AttentionCard`, `ActionRow`, TanStack Query keys `attention`, `actions`.

**Expected:** Loading copy while queries run; empty copy if lists are empty.

**Screens:** `/dashboard`.

---

## Smart Inbox (upload) — Live (UI) / Planned (storage)

**What:** Drag-and-drop or choose file. PDF, JPG, PNG, max 20 MB.

**User flow:** `/documents/upload` → file selected → `uploadDocument(file)` → navigate to `/documents/processing?file=...`.

**Business logic:** MIME/extension check and size check in `document.service.ts`. File is **not** stored on a server.

**Dependencies:** `UploadBox`, privacy `NotificationCard`.

**Expected:** Error text on invalid type/size; progress bar while “uploading”; category chips (Bills, Insurance, Warranty).

---

## Document processing — Live (simulated)

**What:** Four-step stepper. Auto-advances every ~900 ms, then routes to review.

**User flow:** Query param `file` shows filename pill. Steps: File uploaded → Reading document → Finding dates/provider/policy → Preparing suggested action.

**Business logic:** Client timers only. Production will poll a job status API.

**Dependencies:** `ProgressStepper`.

**Expected:** User can keep using the app (copy says they will be notified). Current UI auto-redirects to review.

---

## Review extraction — Live (mock fields)

**What:** Left: document preview lines. Right: editable fields after “Edit details”. Confirm continues to actions.

**User flow:** `/documents/review` loads `getExtraction()` from `extraction.json` (car insurance demo).

**Business logic:** Fields start disabled. Confirm does not persist edits to a backend.

**Dependencies:** `ReviewForm` in the review page, `Input`, `Badge`.

**Expected:** High confidence badge; Confirm & continue → `/actions`.

**Planned:** Persist corrections, store evidence page numbers, confidence per field.

---

## Actions — Live (lifecycle manager)

**What:** Suggested actions from reviewed documents (PAY, RENEW, REGISTER, REVIEW, FOLLOW_UP, KEEP_FOR_RECORDS) with confirm / start / complete / dismiss and optional reminders.

**User flow:** `/actions` loads open + completed actions. Suggested cards offer Confirm, Confirm & remind, or Not needed. Confirmed / in-progress rows offer Start, Complete, Dismiss. Completed is read-only. Dismissed stay hidden.

**Business logic:** Status machine `suggested → confirmed → in_progress → completed | dismissed`. API stores `confirmed_by`, `confirmed_at`, `completed_at`. Duplicate actions blocked by `(workspace, document, action_type)`.

**Dependencies:** `ActionCard`, `ActionRow`, `action.service.ts`.

**Expected:** Invalid transitions return 400; dismissing does not recreate the same suggestion.

---

## AI Assistant — Live (scripted replies)

**What:** Chat with sources. Right rail “Try asking” fills the input (does not auto-send).

**User flow:** Seeded conversation “What needs my attention this month?”. Send calls `sendMessage`. Unknown questions get a fallback.

**Business logic:** Lookup in `messages.json` `replies` map. **Not** RAG.

**Dependencies:** `ChatMessage`, `UserMessage`, `AIMessage`, `SourceBadge`.

**Expected:** Thinking… while pending; sources pill when present.

**Planned:** Permission-filtered retrieval, citations to document+page, refusal when evidence is missing, prompt-injection tests.

---

## Document vault — Live

**What:** Searchable list: name, type, important date, status.

**User flow:** `/documents` → filter client-side → Upload button to Smart Inbox.

**Dependencies:** `DocumentCard`, `getDocuments()`.

**Expected:** Empty state when search matches nothing.

---

## Timeline — Live

**What:** Dated events (bill payment, insurance renewal, warranty review).

**Route:** `/timeline`. Data: `timeline.json`.

---

## Settings — Live (local only)

**What:** Profile name (not persisted), email disabled, privacy checkbox, delete-account modal (explains mock), notification checkboxes, Sign out.

**Expected:** Sign out clears localStorage and returns to login. Delete account does not erase data.

---

## Layout chrome — Live

- Dark navy sidebar: LIFE AI, menu, Anita profile.
- Header: title, subtitle, Secure workspace.
- Mobile: hamburger (`Open menu`), overlay, collapsible sidebar (`-translate-x-full` until open).
- Smart Inbox stays active for upload/processing/review paths.

---

## Planned features (not in UI yet)

| Feature | Notes |
| --- | --- |
| Registration / OIDC | Playbook Phase 3 |
| Real file storage | Presigned S3 upload |
| Malware scan | Hook after upload |
| PDF text + OCR fallback | Phase 4 |
| Classification + extraction schemas | Bills, insurance, invoice, warranty, generic |
| Reminder worker + email | Phase 5, idempotent jobs |
| RAG | Phase 6 |
| Audit log UI | Phase 3–5 |
| Privacy export/delete APIs | Phase 3 / 8 |
| Onboarding screens | Designed in playbook Phase 2 |
