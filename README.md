# Clipr 🔗

[![License: MIT](https://img.shields.io/badge/License-MIT-green.svg)](https://github.com/vinay-singh-engineer/clipr/blob/main/LICENSE)
[![CI](https://github.com/vinay-singh-engineer/clipr/actions/workflows/ci.yml/badge.svg)](https://github.com/vinay-singh-engineer/clipr/actions/workflows/ci.yml)

A fast, async URL shortener built with FastAPI, PostgreSQL, and Redis. Shorten URLs, track click counts, set expiry, and see per-IP rate limiting in action — all through a clean REST API with auto-generated Swagger docs.

---

## Preview

Open `http://localhost:8000/docs` after starting the app to explore and test all endpoints interactively.

---

## What It Does

Clipr takes a long URL and returns a 6-character short code. Anyone with the short URL is redirected to the original. Every redirect increments a click counter. URLs can optionally expire after a configurable number of days.

Rate limiting is enforced per IP address on every endpoint using `slowapi`, with counters stored in Redis — so limits persist across app restarts and work correctly across multiple instances.

---

## Tech Stack

| Layer         | Technology                   | Purpose                                           |
|:--------------|:-----------------------------|:--------------------------------------------------|
| Web           | FastAPI                      | Async HTTP framework, auto Swagger UI at `/docs`  |
| Database      | PostgreSQL 15                | Persistent URL storage                            |
| ORM           | SQLAlchemy 2.x (async)       | Async database queries via `asyncpg`              |
| Migrations    | Alembic                      | Schema versioning and database migrations         |
| Rate Limiting | slowapi + Redis              | Per-IP rate limiting, counters stored in Redis    |
| Config        | pydantic-settings            | Environment variable management via `.env`        |
| Container     | Docker Compose               | Local Postgres + Redis + app orchestration        |
| Testing       | pytest + pytest-asyncio      | Async tests with SQLite in-memory                 |
| Linting       | flake8                       | Code style enforcement                            |
| CI            | GitHub Actions               | Lint + test on push to `main` / `development`     |

---

## Architecture

```
Client
   │
   ▼
FastAPI (app/main.py)       ← routes, rate limiting, startup
   │
   ├── app/crud.py           ← create_url, get_url, increment_click
   ├── app/models.py         ← SQLAlchemy URL model
   ├── app/schemas.py        ← Pydantic request/response schemas
   ├── app/database.py       ← async engine, session factory
   ├── app/config.py         ← pydantic-settings (DATABASE_URL, BASE_URL, REDIS_URL)
   └── app/limiter.py        ← slowapi Limiter backed by Redis
   │
   ├── PostgreSQL (Docker)   ← urls table
   └── Redis (Docker)        ← rate limit counters
```

---

## Endpoints

| Method | Endpoint        | Rate Limit  | Description                          |
|:-------|:----------------|:------------|:-------------------------------------|
| GET    | `/health`       | —           | DB connectivity check                |
| POST   | `/shorten`      | 10/min/IP   | Create a short URL                   |
| GET    | `/{code}`       | 60/min/IP   | Redirect to original URL (302)       |
| GET    | `/stats/{code}` | 30/min/IP   | Click count + metadata for a URL     |

---

## How to Run Locally

### Prerequisites

- Docker and Docker Compose
- Python 3.9+

### 1. Clone and configure

```bash
git clone https://github.com/vinay-singh-engineer/clipr.git
cd clipr
cp .env.example .env
```

### 2. Start Postgres and Redis

```bash
# Start only the backing services (recommended for local dev)
docker compose up db redis -d
```

### 3. Install dependencies and run

```bash
pip install -r requirements.txt

uvicorn app.main:app --reload
```

App runs at `http://localhost:8000`. Swagger UI at `http://localhost:8000/docs`.

### 4. Run the full stack (app + db in Docker)

```bash
docker compose up --build
```

---

## Usage Examples

### Shorten a URL

```bash
curl -X POST http://localhost:8000/shorten \
  -H "Content-Type: application/json" \
  -d '{"url": "https://example.com/some/very/long/path"}'
```

```json
{
  "code": "aB3xYz",
  "short_url": "http://localhost:8000/aB3xYz",
  "original_url": "https://example.com/some/very/long/path",
  "expires_at": null
}
```

### Shorten with expiry (TTL)

```bash
curl -X POST http://localhost:8000/shorten \
  -H "Content-Type: application/json" \
  -d '{"url": "https://example.com", "ttl_days": 7}'
```

### Redirect

```bash
curl -L http://localhost:8000/aB3xYz
# Follows the 302 redirect to the original URL
```

### View stats

```bash
curl http://localhost:8000/stats/aB3xYz
```

```json
{
  "code": "aB3xYz",
  "original_url": "https://example.com/some/very/long/path",
  "click_count": 3,
  "created_at": "2026-05-24T10:00:00Z",
  "expires_at": null
}
```

### Rate limiting

Exceeding the limit returns a `429 Too Many Requests`:

```bash
# Hit /shorten more than 10 times in a minute from the same IP
curl -X POST http://localhost:8000/shorten \
  -H "Content-Type: application/json" \
  -d '{"url": "https://example.com"}'
# HTTP 429
# {"error": "Rate limit exceeded: 10 per 1 minute"}
```

---

## Extending the Schema

The app uses `Base.metadata.create_all()` on startup — tables are created automatically when the app first runs. No migration needed out of the box.

Alembic is included for when the schema needs to change after the database already exists (adding a column, a new table, renaming a field). In that case:

```bash
# After editing a model, generate a migration
alembic revision --autogenerate -m "add custom_alias column"

# Apply it
alembic upgrade head

# Roll back if needed
alembic downgrade -1
```

---

## Run Tests

Tests use SQLite in-memory — no Postgres required.

```bash
pytest tests/ -v --cov=app --cov-report=term-missing
```

---

## Project Structure

```
clipr/
├── app/
│   ├── main.py           # FastAPI app — routes, rate limiting, startup
│   ├── config.py         # pydantic-settings — DATABASE_URL, BASE_URL
│   ├── database.py       # Async SQLAlchemy engine and session factory
│   ├── models.py         # URL table definition
│   ├── schemas.py        # Pydantic request/response schemas
│   ├── crud.py           # Database operations — create, get, increment
│   └── limiter.py        # slowapi Limiter instance
├── alembic/
│   ├── env.py            # Async Alembic migration environment
│   └── versions/
│       └── 0001_initial_schema.py
├── tests/
│   └── test_main.py      # 10 async tests using SQLite in-memory
├── docker-compose.yml    # Postgres + app services
├── Dockerfile
├── requirements.txt
├── alembic.ini
├── .env.example
├── pytest.ini
├── .flake8
└── .github/
    └── workflows/
        └── ci.yml
```

---

## Key Design Decisions

**FastAPI over Flask**
FastAPI's async-first design means every database call is non-blocking — the server can handle other requests while waiting for Postgres. SQLAlchemy 2.x with `asyncpg` provides fully async ORM queries. The auto-generated Swagger UI at `/docs` lets anyone explore and test the API without writing a single curl command.

**What is an ORM and why SQLAlchemy**
An ORM (Object Relational Mapper) lets you interact with a database using Python objects instead of writing raw SQL strings. SQLAlchemy maps each database table to a Python class — the `urls` table becomes the `URL` class, and each row becomes an instance of it.

Without ORM:
```sql
INSERT INTO urls (code, original_url) VALUES ('aB3xYz', 'https://example.com');
SELECT * FROM urls WHERE code = 'aB3xYz';
```

With SQLAlchemy:
```python
url = URL(code="aB3xYz", original_url="https://example.com")
db.add(url)

url = await db.execute(select(URL).where(URL.code == "aB3xYz"))
```

Benefits: no raw SQL in application code, automatic SQL injection prevention, database portability (swap Postgres for SQLite in tests with a single config change), and Python-native query composition. SQLAlchemy 2.x with `asyncpg` adds fully async query execution — queries don't block the event loop while waiting for the database.

**slowapi + Redis for rate limiting**
`slowapi` mirrors Flask-Limiter's API but integrates natively with FastAPI's dependency injection. Limits are declared as decorators per endpoint, making the policy visible at a glance.

Redis is used as the rate limit counter store for three reasons:
- **Persistence** — counters survive app restarts. With in-memory storage, restarting the app resets all counters, effectively bypassing the limit.
- **Multi-instance correctness** — if you run two app instances behind a load balancer, each would have its own in-memory counter. A client could hit the limit on instance A, switch to instance B, and get a fresh counter. Redis is shared across all instances so the limit is enforced globally.
- **Speed** — Redis is an in-memory data store purpose-built for this kind of fast counter increment. A rate limit check adds sub-millisecond overhead per request.

**Alembic for migrations**
SQLAlchemy's `Base.metadata.create_all()` is used on startup for convenience in development, but Alembic is included for production use — it provides a full migration history, safe rollbacks, and `--autogenerate` to detect model changes.

**SQLite for testing**
Tests run against SQLite in-memory via `aiosqlite`. No Docker or Postgres required in CI — fast, isolated, and deterministic. The async SQLAlchemy session is overridden per test via FastAPI's dependency injection.

**Optional TTL**
Short URLs can expire after a configurable number of days. Expired URLs return `410 Gone` rather than `404` — a meaningful distinction that tells the client the resource existed but is no longer available.

---

## License

MIT — use freely, attribute appreciated.

---

## 💻 Author

[Vinay Singh](https://vinay-singh-engineer.github.io/portfolio)
