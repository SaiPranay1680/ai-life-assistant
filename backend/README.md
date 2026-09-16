# AI Life Assistant Backend

This backend provides the FastAPI API layer for the AI Life Assistant project. It is designed to support:

- PostgreSQL persistence
- OIDC-based authentication
- JWT access tokens and refresh tokens
- Role-based authorization for app features
- Document and conversation-related data models

This project is intended to be used by multiple developers collaborating on the authentication and application backend before the frontend is fully wired to OIDC/JWT.

---

## 1. Project structure

```text
backend/
  .env.example
  requirements.txt
  README.md
  app/
    __init__.py
    db.py
    main.py
    models/
      __init__.py
      user.py
      oauth.py
      refresh_token.py
      documents.py
  migrations/
    initial.sql
  scripts/
    check_db.py
    run_migration.py
  alembic.ini
  alembic/
    env.py
```

---

## 2. Prerequisites

Before running this project, make sure the following are installed:

- Python 3.11 or above
- PostgreSQL 14+ (or 15)
- `psql` client (optional but recommended)
- Git
- A terminal such as PowerShell, CMD, Git Bash, or Bash

For Windows users, PostgreSQL installation commonly adds `psql` to PATH. If not, use the PostgreSQL SQL Shell or pgAdmin.

---

## 3. Install PostgreSQL

### Option A: Install locally on Windows

1. Download PostgreSQL from the official PostgreSQL installer.
2. Install it with default settings.
3. Note the PostgreSQL username/password created during install.
4. Start the PostgreSQL service.
5. Open `psql` or pgAdmin.

### Option B: Use Docker

If you do not want to install PostgreSQL locally, use Docker:

```bash
docker run --name ai-pg \
  -e POSTGRES_USER=postgres \
  -e POSTGRES_PASSWORD=postgres \
  -e POSTGRES_DB=postgres \
  -p 5432:5432 \
  -d postgres:15
```

Then connect to PostgreSQL as the `postgres` user.

---

## 4. Create PostgreSQL user and database

The project expects a database named `ai_life_assistant` and a role named `ai_app`.

### Connect as postgres

```bash
psql -U postgres -h localhost
```

If prompted, use the PostgreSQL password you created during install.

### Create the role and database

```sql
CREATE USER ai_app WITH LOGIN PASSWORD '1627';
CREATE DATABASE ai_life_assistant OWNER ai_app;
GRANT ALL PRIVILEGES ON DATABASE ai_life_assistant TO ai_app;
```

### If the role already exists, reset the password

```sql
ALTER USER ai_app WITH PASSWORD '1627';
```

### Grant schema permissions

```sql
\c ai_life_assistant
GRANT USAGE, CREATE ON SCHEMA public TO ai_app;
GRANT ALL PRIVILEGES ON ALL TABLES IN SCHEMA public TO ai_app;
GRANT ALL PRIVILEGES ON ALL SEQUENCES IN SCHEMA public TO ai_app;
ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT ALL ON TABLES TO ai_app;
ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT ALL ON SEQUENCES TO ai_app;
```

### Verify the setup

```sql
\du
\l
```

You should see:

- role: `ai_app`
- database: `ai_life_assistant`

---

## 5. Database connection configuration

Copy the sample environment file and update it with your local DB credentials.

From the project root:

```bash
cd backend
copy .env.example .env
```

On macOS/Linux:

```bash
cp .env.example .env
```

Then update `.env`:

```env
DATABASE_URL=postgresql+asyncpg://ai_app:1627@localhost:5432/ai_life_assistant
OIDC_CLIENT_ID=REPLACE_CLIENT_ID
OIDC_CLIENT_SECRET=REPLACE_CLIENT_SECRET
OIDC_AUTHORIZATION_ENDPOINT=
OIDC_TOKEN_ENDPOINT=
OIDC_USERINFO_ENDPOINT=
JWT_PRIVATE_KEY=""
JWT_PUBLIC_KEY=""
JWT_ALGORITHM=RS256
ACCESS_TOKEN_EXPIRE_MINUTES=15
REFRESH_TOKEN_EXPIRE_DAYS=30
```

Important notes:

- The username and password in `DATABASE_URL` must exactly match the PostgreSQL user you created.
- The DB name must be `ai_life_assistant`.
- If you change the password in PostgreSQL, update the `DATABASE_URL` too.
- Do not commit `.env` to Git. Keep it local only.

---

## 6. Apply the database schema

The project includes the initial schema migration in:

```text
backend/migrations/initial.sql
```

### Method 1: Use the project migration runner

From the project root:

```bash
python backend/scripts/run_migration.py
```

This script reads the SQL file and executes it against PostgreSQL.

### Method 2: Run the SQL file directly with psql

```bash
psql -U ai_app -d ai_life_assistant -f backend/migrations/initial.sql
```

### Expected result

The migration creates tables such as:

- `users`
- `user_profiles`
- `organizations`
- `user_organizations`
- `roles`
- `user_roles`
- `oauth_accounts`
- `refresh_tokens`
- `audit_logs`
- `documents`
- `messages`
- `timelines`

---

## 7. Validate the database connection

You can test the DB connectivity using the project script:

```bash
python backend/scripts/check_db.py
```

This script should successfully execute a simple SQL query.

You can also verify the tables:

```bash
psql -U ai_app -d ai_life_assistant -c "\dt"
```

---

## 8. Install Python dependencies

From the project root:

```bash
cd backend
python -m venv .venv
```

### Windows PowerShell

```powershell
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
```

### macOS/Linux

```bash
source .venv/bin/activate
pip install -r requirements.txt
```

Installed packages include:

- FastAPI
- Uvicorn
- SQLAlchemy
- asyncpg
- Alembic
- python-dotenv
- passlib
- python-jose
- authlib
- psycopg2-binary

---

## 9. Run the backend

Once dependencies are installed and the database is ready, start the API:

```bash
cd backend
uvicorn app.main:app --reload --port 8000
```

Then open:

```text
http://localhost:8000/health
```

You should get a JSON response like:

```json
{"status": "ok"}
```

---

## 10. OIDC and JWT setup for developers

This project is intentionally structured for future OIDC/JWT work.

### Required environment variables

For the app to do JWT/OIDC properly, each developer will need values like:

- `OIDC_CLIENT_ID`
- `OIDC_CLIENT_SECRET`
- `OIDC_AUTHORIZATION_ENDPOINT`
- `OIDC_TOKEN_ENDPOINT`
- `OIDC_USERINFO_ENDPOINT`
- `JWT_PRIVATE_KEY`
- `JWT_PUBLIC_KEY`
- `JWT_ALGORITHM`

Example values depend on the identity provider (Google, Azure AD, Keycloak, Auth0, Okta, etc.).

### Recommended identity flow

Use a standard OIDC authorization code flow with PKCE when the frontend is involved.

Typical backend responsibilities:

- redirect user to IdP login
- exchange code for tokens
- fetch user info
- create or update local user record
- save `oauth_accounts` mapping
- issue JWT access token and refresh token
- validate access token on protected routes

---

## 11. Security guidance

Before production, ensure the following:

- use SSL/TLS in all environments
- keep JWT signing keys in a secret manager
- do not store raw refresh tokens in plain text
- hash refresh tokens before saving
- use HttpOnly secure cookies for refresh tokens if possible
- validate audience, issuer, and expiry on every JWT
- log authentication events to `audit_logs`

---

## 12. Git workflow for team collaboration

When pushing to Git, keep the application secrets local.

```bash
git status
git add .
git commit -m "Add backend DB schema and initial auth scaffolding"
git push origin main
```

Important:

- `.env` should not be committed
- `.venv` should not be committed
- local PostgreSQL credentials should stay private

---

## 13. Quick developer checklist

Use this checklist before starting work:

- [ ] PostgreSQL installed and running
- [ ] `ai_app` role exists
- [ ] `ai_life_assistant` database exists
- [ ] database credentials match `.env`
- [ ] migration script successfully executed
- [ ] Python dependencies installed
- [ ] backend starts on port 8000
- [ ] `/health` returns status OK

---

## 14. Common issues and fixes

### Password authentication failed for user `ai_app`

Cause: PostgreSQL password mismatch.

Fix:

```sql
ALTER USER ai_app WITH PASSWORD '1627';
```

Then verify `.env` matches exactly.

### Permission denied for schema public

Cause: the role lacks privileges.

Fix:

```sql
\c ai_life_assistant
GRANT USAGE, CREATE ON SCHEMA public TO ai_app;
GRANT ALL PRIVILEGES ON ALL TABLES IN SCHEMA public TO ai_app;
GRANT ALL PRIVILEGES ON ALL SEQUENCES IN SCHEMA public TO ai_app;
```

### `uvicorn` command not found

Cause: environment not activated or dependencies not installed.

Fix:

```bash
pip install -r requirements.txt
```

---

## 15. Summary

This backend is ready to connect to PostgreSQL, run migrations, and serve the API. The database schema is already created and the project is structured for JWT and OIDC implementation by the next developer.

The most important connection values are:

```text
DB User: ai_app
DB Password: 1627
DB Name: ai_life_assistant
Host: localhost
Port: 5432
```

Once those values match the local PostgreSQL instance and `.env`, the backend can connect and the project is ready for secure auth development.
