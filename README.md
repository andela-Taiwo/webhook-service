# Webhook Service

A FastAPI-based webhook service for handling payment, invoice, and refund webhooks with PostgreSQL database backend.

## Architecture

- **Framework**: FastAPI with async/await
- **Database**: PostgreSQL with SQLModel (async)
- **Migrations**: Alembic (async)
- **Package Manager**: uv
- **Python**: 3.13+

## Prerequisites

- Python 3.13 or higher
- PostgreSQL 14+ (or Docker)
- uv package manager

### Install uv

```bash
# macOS/Linux
curl -LsSf https://astral.sh/uv/install.sh | sh

# Windows
powershell -c "irm https://astral.sh/uv/install.ps1 | iex"
```

## Local Setup

### 1. Clone the Repository

```bash
git clone <repository-url>
cd webhook-service
```

### 2. Set Up PostgreSQL Database

#### Option A: Using Docker (Recommended)

```bash
docker run --name webhook-postgres \
  -e POSTGRES_USER=webhook \
  -e POSTGRES_PASSWORD=webhook \
  -e POSTGRES_DB=webhook \
  -p 5432:5432 \
  -d postgres:16-alpine
```

#### Option B: Using Local PostgreSQL

Create a database and user:

```sql
CREATE DATABASE webhook;
CREATE USER webhook WITH PASSWORD 'webhook';
GRANT ALL PRIVILEGES ON DATABASE webhook TO webhook;
```

### 3. Environment Configuration

Create a `.env` file in the project root:

```bash
# .env
WEBHOOK_DATABASE_URL=postgresql+asyncpg://webhook:webhook@localhost:5432/webhook
WEBHOOK_ENVIRONMENT=local
WEBHOOK_LOG_JSON=false
```

### 4. Install Dependencies

```bash
# Create virtual environment and install dependencies
uv sync
```

This will:
- Create a virtual environment in `.venv`
- Install all dependencies from `pyproject.toml`

### 5. Activate Virtual Environment

```bash
# macOS/Linux
source .venv/bin/activate

# Windows
.venv\Scripts\activate
```

### 6. Configure Alembic

Edit `alembic.ini` to set the database URL (or it will be read from environment):

```ini
# alembic.ini (line 89)
# Leave commented out to use DATABASE_URL from .env
# sqlalchemy.url = postgresql+asyncpg://webhook:webhook@localhost:5432/webhook
```

Update `alembic/env.py` to use your SQLModel models:

```python
# alembic/env.py
from src.core.config import settings
from src.db.database import engine
from sqlmodel import SQLModel

# Import all models so Alembic can detect them
from src.db.models.payment import PaymentModel, InvoiceModel, RefundModel

target_metadata = SQLModel.metadata

# ... rest of the configuration
```

### 7. Run Database Migrations

```bash
# Create initial migration
alembic revision --autogenerate -m "initial migration"

# Apply migrations
alembic upgrade head
```

### 8. Run the Application

```bash
# Using uvicorn directly
uvicorn src.main:app --reload --host 0.0.0.0 --port 8000

# Or using fastapi CLI (if available)
fastapi dev src/main.py
```

The API will be available at:
- API: http://localhost:8000
- Interactive docs: http://localhost:8000/docs
- Alternative docs: http://localhost:8000/redoc

## Database Models

### PaymentModel
- `id`: UUID (primary key)
- `user_name`: String (indexed)
- `amount`: Float
- `payment_method`: String
- `payment_date`: DateTime (timezone-aware, auto-generated)

### InvoiceModel
- `id`: UUID (primary key)
- `user_name`: String (indexed)
- `invoice_number`: String (indexed, unique)
- `amount_due`: Float
- `due_date`: DateTime
- `issued_date`: DateTime (timezone-aware, auto-generated)

### RefundModel
- `id`: UUID (primary key)
- `user_name`: String (indexed)
- `amount`: Float
- `refund_reason`: String
- `refund_date`: DateTime (timezone-aware, auto-generated)

## Common Commands

### Database Migrations

```bash
# Create a new migration after model changes
alembic revision --autogenerate -m "description of changes"

# Apply migrations
alembic upgrade head

# Rollback one migration
alembic downgrade -1

# View migration history
alembic history

# View current revision
alembic current
```

### Development

```bash
# Install new dependency
uv add package-name

# Install dev dependency
uv add --dev package-name

# Update dependencies
uv sync

# Run linter
ruff check .

# Format code
ruff format .
```

### Database Management

```bash
# Connect to PostgreSQL
psql -U webhook -d webhook

# Reset database (WARNING: destroys all data)
alembic downgrade base
alembic upgrade head
```

## Project Structure

```
webhook-service/
├── alembic/                    # Database migrations
│   ├── versions/              # Migration files
│   └── env.py                 # Alembic configuration
├── src/
│   ├── api/                   # API routes
│   │   └── v1/
│   │       └── endpoints/     # API endpoints
│   ├── core/                  # Core configuration
│   │   ├── config.py         # Settings
│   │   └── logging.py        # Logging setup
│   ├── db/                    # Database layer
│   │   ├── database.py       # Engine & session
│   │   ├── deps.py           # DB dependencies
│   │   └── models/           # SQLModel models
│   ├── middleware/            # FastAPI middleware
│   ├── schema/               # Pydantic schemas
│   └── services/             # Business logic
├── .env                       # Environment variables (not in git)
├── alembic.ini               # Alembic config
├── pyproject.toml            # Project dependencies
└── README.md                 # This file
```

## Environment Variables

All environment variables use the `WEBHOOK_` prefix:

| Variable | Description | Default |
|----------|-------------|---------|
| `WEBHOOK_DATABASE_URL` | PostgreSQL connection string | `postgresql+asyncpg://webhook:webhook@localhost:5432/webhook` |
| `WEBHOOK_ENVIRONMENT` | Environment (local/test/staging/production) | `local` |
| `WEBHOOK_HOST` | Server host | `0.0.0.0` |
| `WEBHOOK_PORT` | Server port | `8000` |
| `WEBHOOK_LOG_LEVEL` | Logging level | `INFO` |
| `WEBHOOK_LOG_JSON` | JSON formatted logs | `true` |
| `WEBHOOK_OTEL_ENABLED` | Enable OpenTelemetry | `true` |
| `WEBHOOK_METRICS_ENABLED` | Enable metrics | `true` |

## Testing

```bash
# Run tests (when test suite is added)
pytest

# Run tests with coverage
pytest --cov=src --cov-report=html
```

## Troubleshooting

### Database Connection Issues

**Error**: `could not connect to server`

**Solution**: Ensure PostgreSQL is running:
```bash
# Check if container is running
docker ps

# Start container if stopped
docker start webhook-postgres
```

### Migration Issues

**Error**: `Can't locate revision identified by 'xxxxx'`

**Solution**: Reset Alembic:
```bash
# Delete alembic_version table
psql -U webhook -d webhook -c "DROP TABLE IF EXISTS alembic_version;"

# Rerun migrations
alembic upgrade head
```

### Import Errors

**Error**: `ModuleNotFoundError: No module named 'src'`

**Solution**: Ensure virtual environment is activated and dependencies are installed:
```bash
source .venv/bin/activate
uv sync
```

## Contributing

1. Create a feature branch
2. Make your changes
3. Run linter: `ruff check . --fix`
4. Format code: `ruff format .`
5. Create migration if models changed: `alembic revision --autogenerate -m "description"`
6. Test your changes
7. Submit a pull request

## License

[Your License Here]
