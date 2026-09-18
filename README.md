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

---

## Prerequisites

Before running the project, install the following:

- Python 3.11+
- Node.js 18+
- npm
- PostgreSQL 14+ or 15+
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

Use these credentials on the login page:

- Username: `Admin`
- Email: `admin@gmail.com`
- Password: `16271627`

The app should redirect logged-in admins to the admin dashboard.

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

Check:
- the admin user exists in the database
- the password is exactly `16271627`
- the database is migrated
- you ran the seed script

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
