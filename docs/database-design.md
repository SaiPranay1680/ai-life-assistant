# Database Design

**Status:** Planned. No database runs with the current frontend. Types in `apps/web/src/types/index.ts` and JSON fixtures are the **temporary** model.

## Principles

- PostgreSQL is the system of record.
- Files live in object storage; tables store keys and metadata.
- Every tenant-owned row includes `workspace_id`.
- Prefer UUID primary keys.
- Migrations via Alembic only (no manual prod SQL).

## Logical entities (MVP)

```text
User 1───* WorkspaceUser *───1 Workspace
Workspace 1───* Document
Document 1───* ExtractionField
Document 1───* Action
Action 1───* Reminder
Document 1───* Chunk (RAG)
Action *───* AuditEvent
```

### User

Identity from OIDC (`sub`, email). Local columns: `id`, `email`, `name`, `created_at`. No long-lived raw passwords if OIDC is used.

### Workspace

MVP: one personal workspace per user. `id`, `name`, `created_at`. Future: family workspace without rewriting documents if they already have `workspace_id`.

### Document

`id`, `workspace_id`, `storage_key`, `original_filename`, `mime_type`, `size_bytes`, `status`, `document_type` (nullable until classified), `created_by`, timestamps.

**Status machine (playbook):** uploaded → scanning → parsing → extracting → ready_for_review → confirmed / failed. UI stepper is a simplified four-step view.

### Extraction

Either JSONB `payload` on document or child `extraction_fields`: `field_name`, `raw_value`, `normalized_value`, `confidence`, `page_number`, `evidence_snippet`.

Never invent nulls as if they were extracted; store unknown explicitly.

### Action

Matches playbook sketch:

- `id`, `workspace_id`, `source_document_id`
- `title`, `action_type` (PAY, RENEW, REGISTER, REVIEW, FOLLOW_UP, KEEP_FOR_RECORDS)
- `due_at`, `priority`, `status`
- `confidence`, `explanation`, `evidence`
- `requires_confirmation`, `confirmed_by`, `confirmed_at`

Statuses: suggested → confirmed → in_progress → completed | dismissed.

### Reminder

`action_id`, `fire_at`, `channel`, `idempotency_key`, `sent_at`. Jobs must be idempotent (playbook exit criterion).

### Chunk (RAG)

`document_id`, `workspace_id`, `page`, `ordinal`, `text`, `embedding` (pgvector), metadata JSON.

### Audit

Append-only: actor, workspace, entity, action, at, metadata (no document body).

## Indexes (intent)

- `documents (workspace_id, created_at desc)`
- `actions (workspace_id, due_at)`
- `chunks (workspace_id)` + vector index per playbook/pgvector docs
- Unique email on users
- Unique idempotency keys on reminders

## Mapping from current JSON

| Fixture | Future table |
| --- | --- |
| `dashboard.json` user | `users` + `workspaces` |
| `dashboard.json` attention | Derived from `actions` / `documents` |
| `documents.json` | `documents` |
| `actions.json` | `actions` |
| `extraction.json` | extraction fields |
| `timeline.json` | `actions.due_at` or a view |
| `messages.json` | Not stored as canned replies; conversations table optional |

## Migration practice

- Expand/migrate/contract for locking tables.
- Never drop columns in the same release that old app versions still write.
- Review migrations for table rewrites on large data (playbook prompt).

## Backups (production)

Playbook Phase 9: backups and restore runbook verified before go-live. Not configured yet.
