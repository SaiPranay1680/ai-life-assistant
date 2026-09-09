# Project Overview

## Background and purpose

People keep bills, insurance policies, warranties, and important papers in email, WhatsApp, and Downloads folders. Due dates are missed. Renewals surprise them. Asking “what do I need to do this month?” requires opening many files.

**AI Life Assistant** is a personal web application that:

1. Accepts an uploaded PDF or image.
2. Understands the document (parse / OCR).
3. Extracts important fields with evidence (amount, date, provider).
4. Suggests an **Action Card** (pay, renew, review).
5. Requires the **user to confirm** before anything consequential is scheduled.
6. Reminds the user.
7. Answers questions **only from that user’s documents**, with source citations.

The product is **action-first**, not chat-first. The dashboard shows what needs attention. Chat is a helper, not the home screen.

AI is **advisory**. The system must never pay bills, renew policies, cancel contracts, or take legal/medical actions on its own.

## Business requirements (MVP)

**Primary user:** one individual (not a company, not a family workspace yet).

**Domains:**

1. Bills (utility and similar)
2. Insurance
3. Purchases / warranties
4. Important documents (passport and similar)

**Application type:** responsive web app. Native iOS/Android is out of scope for MVP.

**Data rule:** never use real personal documents in development or QA. Use synthetic/demo data (the UI currently uses Anita Rao / BESCOM / ABC Insurance fixtures).

### In scope (MUST for full MVP)

- Secure personal workspace
- Document upload (PDF, JPG, PNG)
- Async processing with status
- Extraction with confidence and source evidence
- Human review / edit
- Suggested actions with explanation
- User confirmation
- Reminders (idempotent jobs)
- Dashboard of what needs attention
- Document vault
- Grounded Q&A with citations
- Audit and basic privacy (export/delete later in foundation)

### Out of scope (explicit)

- Native mobile apps
- Family / household permissions
- Bank account connections and payment execution
- Healthcare diagnosis
- Government transaction automation
- Autonomous renewal or cancellation
- Microservices / Kubernetes (unless a later scale reason appears)
- Custom-trained foundation models
- Enterprise SSO/SCIM, white labeling, marketplace

## Goals and objectives

| Goal | How we will know |
| --- | --- |
| Prove the core loop | A new user can complete the golden demo without an engineer editing the database |
| Trust | User always sees source/evidence; confirms before reminders |
| Privacy | Documents stay in the user’s workspace; no cross-user retrieval |
| Teachability | Architecture stays a **modular monolith** so a small team can own it |
| Depth over breadth | Four domains done well, not twenty domains half-done |

### Success metrics (product)

- Activation: first upload + confirmed action
- Extraction correction rate (how often users edit AI fields)
- Suggested-action acceptance rate
- Reminder completion rate
- AI answer helpfulness and citation use
- AI/OCR cost per active user
- Trust/privacy satisfaction

## Overall application flow

```text
Register / Sign in
    → Dashboard (what needs attention)
    → Smart Inbox: upload document
    → Processing (async in production; timed stepper in current UI)
    → Review extracted fields (user confirms or edits)
    → Suggested Action Card (user confirms reminder or dismisses)
    → Document vault + Timeline
    → Ask: “What needs my attention this month?” → cited answer
```

Golden demo from the playbook:

1. User registers and reaches dashboard.  
2. Uploads an electricity bill.  
3. Sees processing.  
4. Extracts amount and due date with evidence.  
5. User reviews and confirms.  
6. System proposes “Pay electricity bill”.  
7. User confirms and creates a reminder.  
8. Dashboard shows the action.  
9. User uploads an insurance policy.  
10. System proposes renewal.  
11. User asks what needs attention this month.  
12. Assistant answers with sources.

## Target users and use cases

### Primary persona (working name: Anita)

A working adult who:

- Receives bills and policies as PDFs
- Misses due dates
- Does not want a chatbot as the main product
- Is cautious about uploading identity/insurance documents
- Wants to **see and confirm** extracted amounts and dates

Demo profile in the UI: **Anita Rao**, `anita@example.com` (name is taken from mock `dashboard.json`; email is whatever they type at login).

### Jobs-to-be-Done (examples)

- When a bill arrives, I want the due date and amount captured so I am reminded before a late fee.
- When insurance is near expiry, I want a renewal action I can confirm, not an automatic purchase.
- When I ask a question, I want an answer tied to **my** PDF page, not a generic internet answer.

### Secondary personas (later)

- Household coordinator (family workspace — deferred)
- Small-business owner with many invoices (not MVP)

## Assumptions

- Users have a modern browser and can upload files up to 20 MB.
- English/Latin documents first; Indic-language OCR quality is a later risk.
- Currency in demo data is INR (₹).
- One workspace per user in MVP (`workspace_id` on every tenant-owned row in the future database).

## Open product decisions

- Exact identity provider (OIDC vendor) for production
- Email vs push as the first reminder channel
- Whether PWA is in first production release
- Pricing / monetization (not required to start building)

These should be recorded as ADRs when decided (see [architecture.md](./architecture.md)).
