# AI Life Assistant

AI Life Assistant is a personal action intelligence platform that helps users manage documents, extract important information, create actions, send reminders, and interact with an AI assistant.

The project has:
- a FastAPI backend
- a PostgreSQL database
- a Next.js frontend
- RBAC with User and Admin roles
- a seeded default admin account for fresh developer environments

---

## Project overview

This repository contains the full application setup for local development:

- Frontend: `apps/web`
- Backend: `backend`
- Documentation: `docs`
- Main project setup guides: root `README.md`

---

## Default developer/admin account

The project includes a seeded admin account so that every new developer can log in using the same admin credentials on a fresh database.

Default admin credentials:

- Username: `Admin`
- Email: `admin@gmail.com`
- Password: `16271627`
- Role: `admin`

Important:
- This is the application login user for the website/admin dashboard.
- The PostgreSQL database user/password is separate and still uses `ai_app` / `1627` unless you intentionally change it.
- The login form uses **email + password**. The username `Admin` is the display name, not the login field.

Full click-by-click login instructions: [How to log in (for developers)](#how-to-log-in-for-developers).

---

## How to log in (for developers)

Do this after the stack is running (Docker or local). The UI lives at **http://localhost:3000**. The API lives at **http://localhost:8000**.

### Before you try

1. Frontend is up: open http://localhost:3000 — you should see the AI Life Assistant login split screen.
2. Backend is up: open http://localhost:8000/health — you should see `{"status":"ok"}`.
3. Use **http://localhost:3000**, not `127.0.0.1`, unless `FRONTEND_URL` also includes that origin (CORS will block login otherwise).
4. Do **not** use the Postgres password (`1627`) on the website. Website login is `admin@gmail.com` / `16271627` (or an account you registered).

### Sign in with the seeded admin (fastest)

This is what most developers should do on a fresh database.

1. Open http://localhost:3000. If you are not already on `/login`, go there.
2. Leave the form on **Welcome back** (sign-in mode). If you see **Create your account**, click **Already have an account? Sign in**.
3. Email address: `admin@gmail.com`
4. Password: `16271627`
5. Click **Sign in**.
6. On success you are redirected to **`/admin`** (admin role). You should see the admin dashboard, not the normal user dashboard.

If login fails, jump to [Login troubleshooting](#login-troubleshooting).

### Sign in as a normal user

1. Open http://localhost:3000/login.
2. Stay in sign-in mode.
3. Enter that user’s **email** and **password**.
4. Click **Sign in**.
5. On success you are redirected to **`/dashboard`**.

There is no “username login”. Only email + password.

### Create a new local account (register)

Use this when you need a non-admin user.

1. Open http://localhost:3000/login.
2. Click **New here? Create an account**.
3. Enter a **username** (at least 2 characters), **email**, and **password** (at least 6 characters).
4. Click **Create account**.
5. The API creates the user in PostgreSQL, issues a JWT, and (if SMTP is configured) sends:
   - an account-created confirmation email
   - a separate 6-digit **account verification** OTP
6. The UI should take you to **`/verify-account`**. Enter the 6-digit code from email, or skip verification for now and go to `/dashboard` (an unverified banner will still appear).
7. After you sign in later, the same email + password work on the login page. New users land on `/dashboard`, not `/admin`.

If SMTP is not configured, register and login still work. Verification emails are skipped until you set Gmail SMTP in `.env` (see [Email / OTP (optional for login)](#email--otp-optional-for-login)).

### Forgot password

This only works for **email/password** accounts that have a `password_hash`. It does not reset passwords for OIDC-only identities.

1. On the login page, click **Forgot password?**.
2. Enter the registered email and click **Send OTP**.
3. The UI always shows a generic success path (“if an account exists…”). The API does not tell you whether the email is registered.
4. Open **`/verify-reset-otp`**, enter the 6-digit code from email, watch the countdown, resend if needed.
5. After a valid OTP, you get a short-lived reset token (not the OTP) and land on **`/reset-password`**.
6. Enter and confirm a new password (min 6 characters), then return to login and sign in with the new password.

### After login: session and roles

- The browser stores the JWT in `localStorage` (`ala-token`) and a small user object (`ala-auth-user`).
- Session length follows `ACCESS_TOKEN_EXPIRE_MINUTES` (Docker example: 60 minutes). When the token expires, the app sends you back to `/login`.
- `role=admin` → `/admin`. `role=user` → `/dashboard`.
- Dashboard verification status comes from **`GET /me`** (`email_verified`), not from frontend-only state. Unverified users see **Account Not Verified** and a **Verify Account** button (`/verify-account`). The seeded admin is already verified.

### Email / OTP (optional for login)

Login itself does **not** need SMTP. You only need Google SMTP for register confirmation, verification OTP, and forgot-password OTP.

In the **root** `.env` (used by Docker backend + Celery worker):

```text
SMTP_HOST=smtp.gmail.com
SMTP_PORT=587
SMTP_USER=your_gmail_address@gmail.com
SMTP_PASSWORD=your_16_character_app_password
SMTP_FROM_EMAIL=your_gmail_address@gmail.com
SMTP_FROM_NAME=AI Life Assistant
```

Never put these in `NEXT_PUBLIC_*` variables. Restart `backend` and `celery-worker` after changing SMTP.

### How login works under the hood

```text
Browser (/login)
    POST /auth/login  { email, password }
        → FastAPI checks PostgreSQL user
        → bcrypt verify
        → JWT access token
    Browser stores token
    Redirect: admin → /admin   user → /dashboard
```

Useful API checks (optional):

```bash
# Health
curl http://localhost:8000/health

# Login (expect access_token + user)
curl -X POST http://localhost:8000/auth/login ^
  -H "Content-Type: application/json" ^
  -d "{\"email\":\"admin@gmail.com\",\"password\":\"16271627\"}"
```

On macOS/Linux, use `\` instead of `^` for line continuation.

Interactive API explorer: http://localhost:8000/docs → `POST /auth/login`.

### Login troubleshooting

| Symptom | What to check |
| --- | --- |
| Form says “Invalid email or password” | Email is `admin@gmail.com`, password is exactly `16271627`. Re-seed: `python scripts/seed.py` (local) or recreate Docker DB. |
| Button spins then CORS / network error | Backend down, or you opened `127.0.0.1:3000` while `FRONTEND_URL=http://localhost:3000`. |
| Frontend loads, login always fails | `NEXT_PUBLIC_API_URL` must be `http://localhost:8000` (browser URL). Rebuild frontend if you changed it. |
| Redirects to `/dashboard` instead of `/admin` | User `role` is not `admin`. Re-run seed. |
| Immediately bounced back to login | Token expired or 401 on another API. Sign in again. Confirm `JWT_SECRET` is the same for the running backend. |
| Forgot-password / verify emails never arrive | SMTP not set, or Celery worker not running. Login still works without mail. |
| Using Postgres password `1627` on the website | That is the **database** role, not the app user. Use `16271627`. |

---

## Run with Docker (recommended)

This is the fastest way for a new developer to run the **full stack** (PostgreSQL, Redis, FastAPI, Celery worker, Celery beat, Next.js) without installing Python, Node, Postgres, or Redis on the host.

You only need:

- [Docker Desktop](https://www.docker.com/products/docker-desktop/) (Windows/Mac) or Docker Engine + Compose v2 (Linux)
- Git

### What starts

```text
                    Docker Compose
                         │
        ┌────────────────┼────────────────┐
        │                │                │
     Next.js          FastAPI          Celery
     :3000             :8000           worker + beat
        │                │                │
        └────────────────┼────────────────┘
                         │
                    ┌────┴────┐
                    │         │
               PostgreSQL   Redis
             (internal)   (internal)
```

After startup:

| Service | URL / notes |
| --- | --- |
| Frontend (Next.js) | http://localhost:3000 |
| Backend (FastAPI) | http://localhost:8000 |
| API docs (Swagger) | http://localhost:8000/docs |
| PostgreSQL | **not** published on the host — only other containers can reach `postgres:5432` |
| Redis | **not** published on the host — only other containers can reach `redis:6379` |
| Celery worker / beat | no HTTP port |

Follow [How to log in (for developers)](#how-to-log-in-for-developers). For a fresh database, use `admin@gmail.com` / `16271627` and you should land on `/admin`.

---

### Step 1 — Clone the repository

```bash
git clone <your-repository-url>
cd ai-life-assistant
```

---

### Step 2 — Create your environment file

Compose reads secrets from a root `.env` file (gitignored). Copy the template:

**Windows (PowerShell):**

```powershell
copy .env.example .env
```

**macOS / Linux:**

```bash
cp .env.example .env
```

Open `.env` and change at least:

- `POSTGRES_PASSWORD` — Docker Postgres password
- `DATABASE_URL` — **must use the same user, password, and database name** as `POSTGRES_*` (host must stay `postgres`, not `localhost`)
- `JWT_SECRET` — any long random string (do not leave the example value on a shared machine)

Example shape (placeholders only):

```env
POSTGRES_DB=ai_life_assistant
POSTGRES_USER=ai_app
POSTGRES_PASSWORD=change_me

DATABASE_URL=postgresql+asyncpg://ai_app:change_me@postgres:5432/ai_life_assistant
REDIS_URL=redis://redis:6379/0
CELERY_BROKER_URL=redis://redis:6379/0
CELERY_RESULT_BACKEND=redis://redis:6379/1

FRONTEND_URL=http://localhost:3000
NEXT_PUBLIC_API_URL=http://localhost:8000
JWT_SECRET=change_me_generate_a_long_random_string
```

**Important:**

- Never commit `.env`.
- Inside Docker, database and Redis hosts are service names (`postgres`, `redis`), not `localhost`.
- `NEXT_PUBLIC_API_URL` and `FRONTEND_URL` must use `localhost`, because the **browser** runs on your machine, not inside the Docker network.
- If you change `POSTGRES_PASSWORD`, update the password inside `DATABASE_URL` too.

Leave `STORAGE_BACKEND=local` and `CLAMAV_REQUIRED=false` for a first run.

---

### Step 3 — Free ports 3000 and 8000

Docker publishes:

- `3000` → frontend
- `8000` → backend

If you already run Next.js or Uvicorn on the host, stop them first. Postgres on host port `5432` does **not** conflict, because Compose does not publish Postgres to the host.

---

### Step 4 — Start everything

From the **repository root** (the folder that contains `docker-compose.yml`):

```bash
docker compose up --build
```

The first build can take several minutes (Python OCR/ML wheels and `npm run build`). Later starts are faster.

Wait until you see the backend healthy and the frontend listening. Then open http://localhost:3000.

SQL migrations run **automatically** when the `backend` container starts (`python scripts/run_migration.py`). You do not run Alembic for this project.

---

### Step 5 — Start in the background (optional)

```bash
docker compose up -d --build
```

Check status:

```bash
docker compose ps
```

Follow logs:

```bash
docker compose logs -f
```

One service:

```bash
docker compose logs -f backend
docker compose logs -f frontend
docker compose logs -f celery-worker
docker compose logs -f celery-beat
docker compose logs -f postgres
docker compose logs -f redis
```

---

### Step 6 — Stop

Stop containers (keeps database, Redis, and uploaded files in Docker volumes):

```bash
docker compose down
```

Start again later without rebuilding (if images already exist):

```bash
docker compose up
```

**Delete all Docker data** for this project (database reset — destructive):

```bash
docker compose down -v
```

---

### Daily Docker workflow

| Task | Command |
| --- | --- |
| Start (foreground, rebuild) | `docker compose up --build` |
| Start (background) | `docker compose up -d --build` |
| Stop | `docker compose down` |
| Status | `docker compose ps` |
| Logs (all) | `docker compose logs -f` |
| Restart API only | `docker compose restart backend` |
| Shell in API container | `docker compose exec backend bash` |
| Open Postgres inside Docker | `docker compose exec postgres psql -U ai_app -d ai_life_assistant` |
| Re-run SQL migrations | `docker compose exec backend python scripts/run_migration.py` |

After you change frontend env such as `NEXT_PUBLIC_API_URL`, rebuild the frontend image:

```bash
docker compose up -d --build frontend
```

---

### How containers talk to each other

| Caller | Address to use | Why |
| --- | --- | --- |
| Your browser → UI | `http://localhost:3000` | Browser is on the host |
| Your browser → API | `http://localhost:8000` | JS in the browser cannot see Docker DNS names |
| FastAPI / Celery → DB | `postgres:5432` | Docker service name |
| FastAPI / Celery → Redis | `redis:6379` | Docker service name |

Do **not** put `localhost` in `DATABASE_URL` or Redis URLs inside `.env` when using Compose. `localhost` inside a container means that container, not your laptop and not Postgres.

Open the app as **http://localhost:3000** (not `127.0.0.1`) unless you also add `http://127.0.0.1:3000` to `FRONTEND_URL` (CORS).

---

### Optional: ClamAV (malware scan)

Default Docker setup does **not** require ClamAV (`CLAMAV_REQUIRED=false`).

To run ClamAV with the stack:

1. In `.env` set `CLAMAV_HOST=clamav` and `CLAMAV_REQUIRED=true`
2. Start with both Compose files:

```bash
docker compose -f docker-compose.yml -f docker-compose.clamav.yml up --build
```

The first ClamAV start can take several minutes while virus definitions download.

---

### Docker troubleshooting

| Symptom | What to try |
| --- | --- |
| `env file .env not found` | You skipped Step 2. Copy `.env.example` to `.env`. |
| Port 3000 or 8000 already allocated | Stop the other app using that port, or change the left-hand port in `docker-compose.yml` (e.g. `"3001:3000"`). |
| Frontend loads but API calls fail | Confirm backend is up: http://localhost:8000/health. Confirm `NEXT_PUBLIC_API_URL=http://localhost:8000`. Rebuild frontend if you changed that variable. |
| CORS / login blocked | Use `http://localhost:3000` and keep `FRONTEND_URL=http://localhost:3000`. |
| Documents stay on “Processing” | `docker compose logs -f celery-worker` — worker must be running and Redis healthy. |
| Backend never becomes healthy | `docker compose logs -f backend` and `docker compose logs -f postgres`. Check `DATABASE_URL` password matches `POSTGRES_PASSWORD`. |
| Need a clean database | `docker compose down -v` then `docker compose up --build`. This wipes Postgres data. |

---

## Local setup without Docker (manual)

Use this path only if you are **not** using `docker compose`. You must install Python, Node, PostgreSQL, and Redis yourself and start FastAPI, Celery, and Next.js in separate terminals.

### Prerequisites

Install:

- Python 3.11+
- Node.js 18+
- npm
- PostgreSQL 14+ or 15+
- Redis (for Celery)
- `psql` client (recommended)
- Git
- VS Code or any terminal of your choice

---

## 1. Clone the project and open the repository

```bash
git clone <your-repository-url>
cd ai-life-assistant
```

---

## 2. Install PostgreSQL and create the database

### Option A: Install PostgreSQL locally on Windows

1. Install PostgreSQL from the official installer.
2. Start the PostgreSQL service.
3. Open `psql` or pgAdmin.

### Option B: Use Docker

If you prefer Docker instead of a local install:

```bash
docker run --name ai-pg \
  -e POSTGRES_USER=postgres \
  -e POSTGRES_PASSWORD=postgres \
  -e POSTGRES_DB=postgres \
  -p 5432:5432 \
  -d postgres:15
```

Then connect as `postgres` in PostgreSQL.

### Create the PostgreSQL app role and database

Open a terminal and run:

```bash
psql -U postgres -h localhost
```

Then run the SQL below:

```sql
CREATE USER ai_app WITH LOGIN PASSWORD '1627';
CREATE DATABASE ai_life_assistant OWNER ai_app;
GRANT ALL PRIVILEGES ON DATABASE ai_life_assistant TO ai_app;
```

If the user already exists, update its password:

```sql
ALTER USER ai_app WITH PASSWORD '1627';
```

Grant schema permissions:

```sql
\c ai_life_assistant
GRANT USAGE, CREATE ON SCHEMA public TO ai_app;
GRANT ALL PRIVILEGES ON ALL TABLES IN SCHEMA public TO ai_app;
GRANT ALL PRIVILEGES ON ALL SEQUENCES IN SCHEMA public TO ai_app;
ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT ALL ON TABLES TO ai_app;
ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT ALL ON SEQUENCES TO ai_app;
```

Verify the setup:

```sql
\du
\l
```

You should see:
- role: `ai_app`
- database: `ai_life_assistant`

---

## 3. Configure backend environment variables

Inside the backend folder, copy the sample env file if present:

```bash
cd backend
copy .env.example .env
```

On macOS/Linux:

```bash
cp .env.example .env
```

Then make sure the `.env` file contains values like this:

```env
DATABASE_URL=postgresql+asyncpg://ai_app:1627@localhost:5432/ai_life_assistant
FRONTEND_URL=http://localhost:3000
JWT_SECRET=dev-only-change-me
JWT_ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=1440
REDIS_URL=redis://localhost:6379/0
CELERY_BROKER_URL=redis://localhost:6379/0
CELERY_RESULT_BACKEND=redis://localhost:6379/1
```

Notes:
- `DATABASE_URL` should match the PostgreSQL user and database you created above.
- Keep `.env` local to your machine and do not commit it to Git.
- These values are for local development only.

---

## 4. Install Python dependencies

Create a virtual environment for the backend and install dependencies:

### Windows PowerShell

```powershell
cd backend
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
```

### macOS/Linux

```bash
cd backend
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

This project uses packages such as:
- FastAPI
- SQLAlchemy
- asyncpg
- Uvicorn
- passlib
- python-dotenv
- Celery
- Redis client dependencies

---

## 5. Apply the database schema and migrations

The project includes the migration script and SQL files under the backend folder.

### Method 1: Run the migration script

From the repo root:

```bash
python backend/scripts/run_migration.py
```

### Method 2: Run the SQL file directly

```bash
psql -U ai_app -d ai_life_assistant -f backend/migrations/initial.sql
```

This creates the needed database tables for users, profiles, workspaces, documents, actions, reminders, and related records.

You can validate the tables with:

```bash
psql -U ai_app -d ai_life_assistant -c "\dt"
```

---

## 6. Seed the default admin account

Once the database is ready, run the seed script to create or update the default admin user.

From the project root:

```bash
cd backend
# activate venv first if not already active
python scripts/seed.py
```

### What the seed script does

The seed file will:
- check whether `admin@gmail.com` already exists
- create the admin user if it is missing
- update the admin user if it already exists
- set username to `Admin`
- set role to `admin`
- set email to `admin@gmail.com`
- set password to `16271627`
- activate the account and verify the email
- create the admin profile and workspace if needed

This makes the admin account reusable across new clones or fresh databases.

---

## 7. Run the backend

After the database is created and the seed is complete, start the API:

```bash
cd backend
uvicorn app.main:app --reload --port 8000
```

Check health:

```bash
http://localhost:8000/health
```

Expected response:

```json
{"status": "ok"}
```

---

## 8. Install frontend dependencies and start the app

Open a separate terminal and run:

```bash
cd apps/web
npm install
npm run dev
```

Then open:

```text
http://localhost:3000
```

---

## 9. Log in with the default admin account

Step-by-step (UI, register, forgot password, session, troubleshooting): [How to log in (for developers)](#how-to-log-in-for-developers).

Quick admin credentials on http://localhost:3000/login:

- Email: `admin@gmail.com` (this is the login field — not the username)
- Password: `16271627`

Admins are redirected to `/admin`. Normal users are redirected to `/dashboard`.

---

## 10. Role-based access control

This project supports two main roles:

- `user`
- `admin`

Rules:
- Normal users can use the standard dashboard flow.
- Admin users can access the admin dashboard.
- Admin users can see overall site stats, manage users, delete user accounts, and update user information.

---

## 11. Full setup summary

Use this order every time you set up a fresh environment:

```bash
# 1. Create PostgreSQL role and database
psql -U postgres -h localhost
# then run SQL to create ai_app and ai_life_assistant

# 2. Configure backend env
cd backend
copy .env.example .env
# or cp .env.example .env

# 3. Install Python dependencies
python -m venv .venv
# Windows PowerShell:
.\.venv\Scripts\Activate.ps1
# macOS/Linux:
pip install -r requirements.txt

# 4. Apply schema
python scripts/run_migration.py

# 5. Seed default admin account
python scripts/seed.py

# 6. Start backend
uvicorn app.main:app --reload --port 8000

# 7. Start frontend
cd ../apps/web
npm install
npm run dev
```

---

## 12. Common issues and fixes

### PostgreSQL connection failed

Check:
- PostgreSQL is running
- `DATABASE_URL` matches the local values
- the `ai_app` role exists
- the `ai_life_assistant` database exists

Example fix:

```sql
ALTER USER ai_app WITH PASSWORD '1627';
```

### Admin login fails

See the table in [Login troubleshooting](#login-troubleshooting).

Quick checks:
- you signed in with **email** `admin@gmail.com`, not username `Admin`
- the password is exactly `16271627` (not the Postgres password `1627`)
- the database is migrated and you ran the seed script

Run:

```bash
cd backend
python scripts/seed.py
```

### Permission denied for schema public

Run:

```sql
\c ai_life_assistant
GRANT USAGE, CREATE ON SCHEMA public TO ai_app;
GRANT ALL PRIVILEGES ON ALL TABLES IN SCHEMA public TO ai_app;
GRANT ALL PRIVILEGES ON ALL SEQUENCES IN SCHEMA public TO ai_app;
```

### `uvicorn` not found

Activate the virtual environment and install dependencies again:

```bash
cd backend
source .venv/bin/activate  # or .\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
```

---

## 13. Important notes

- Do not commit `.env` files.
- Do not commit virtual environment folders.
- Keep local PostgreSQL credentials private.
- The admin credentials in the app are separate from the database role credentials.
- Use `python scripts/seed.py` whenever you want to restore the default seeded admin user.

---

## 14. Project documentation

Additional technical and design documentation is available in:

- [docs/README.md](./docs/README.md)
- [backend/README.md](./backend/README.md)

This completes the local setup path for running the app, migrating the database, seeding the admin account, and starting both the backend and frontend for development.
