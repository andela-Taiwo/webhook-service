# Webhook Service

A production-grade FastAPI webhook service with HMAC security, idempotency, and automated event processing for payment systems.

## Features

✅ **Security**
- HMAC-SHA256 signature verification
- Timing-safe signature comparison
- Request authentication

✅ **Idempotency**
- Database-backed duplicate detection
- Automatic duplicate handling
- Complete audit trail

✅ **Event Processing**
- Automatic routing by event type
- Support for payments, invoices, refunds, subscriptions
- Transaction-safe processing with rollback

✅ **Reliability**
- Retry tracking with configurable limits
- Comprehensive error handling
- Status tracking for all events

✅ **Testing**
- 28 comprehensive tests (100% passing)
- TDD approach throughout
- Fast SQLite test database

## Architecture

- **Framework**: FastAPI with async/await
- **Database**: PostgreSQL with SQLModel (async)
- **Migrations**: Alembic (async)
- **Testing**: pytest + pytest-asyncio + SQLite
- **Security**: HMAC-SHA256 webhook signatures
- **Queue**: RabbitMQ (configured, not yet implemented)
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
| `WEBHOOK_SECRET_KEY` | HMAC secret key for signature verification | `change-this-in-production` |
| `WEBHOOK_RABBITMQ_URL` | RabbitMQ connection string | `amqp://guest:guest@localhost:5672/` |

## Webhook API

### Endpoint: POST /api/v1/webhooks

Process incoming webhook events with security verification and idempotency.

**Request Headers:**
```
X-Webhook-Signature: <hmac-sha256-signature>
Content-Type: application/json
```

**Request Body:**
```json
{
  "id": "evt_1234567890",
  "type": "payment_intent.succeeded",
  "data": {
    "object": {
      "id": "pi_1234567890",
      "amount": 5000,
      "currency": "usd",
      "customer_email": "customer@example.com",
      "payment_method": "card"
    }
  }
}
```

**Supported Event Types:**
- `payment_intent.succeeded` → Creates PaymentModel
- `invoice.created` → Creates InvoiceModel
- `invoice.payment_succeeded` → Creates InvoiceModel
- `charge.refunded` → Creates RefundModel
- `customer.subscription.created` → Creates SubscriptionModel
- `customer.subscription.updated` → Updates SubscriptionModel

**Success Response (200 OK):**
```json
{
  "status": "success",
  "event_id": "evt_1234567890",
  "event_type": "payment_intent.succeeded",
  "result": {
    "status": "success",
    "event_id": "evt_1234567890",
    "event_type": "payment_intent.succeeded"
  }
}
```

**Idempotent Response (200 OK):**
```json
{
  "status": "success",
  "message": "Event already processed (idempotent)",
  "event_id": "evt_1234567890"
}
```

**Error Responses:**

- `401 Unauthorized` - Invalid or missing signature
- `500 Internal Server Error` - Processing failed

### Generating Webhook Signatures (for testing)

```python
import hmac
import hashlib
import json

secret_key = "your-webhook-secret"
payload = {
    "id": "evt_test_123",
    "type": "payment_intent.succeeded",
    "data": {"object": {"amount": 5000, "customer_email": "test@example.com"}}
}

payload_str = json.dumps(payload, separators=(",", ":"))
signature = hmac.new(
    secret_key.encode(),
    payload_str.encode(),
    hashlib.sha256
).hexdigest()

print(f"X-Webhook-Signature: {signature}")
```

### Testing the Webhook

```bash
# With valid signature
curl -X POST http://localhost:8000/api/v1/webhooks \
  -H "Content-Type: application/json" \
  -H "X-Webhook-Signature: <your-signature>" \
  -d '{
    "id": "evt_test_123",
    "type": "payment_intent.succeeded",
    "data": {
      "object": {
        "id": "pi_123",
        "amount": 5000,
        "customer_email": "test@example.com",
        "payment_method": "card"
      }
    }
  }'
```

## Testing

```bash
# Run all tests
pytest

# Run tests with coverage
pytest --cov=src --cov-report=html

# Run specific test file
pytest tests/test_webhook_processor.py -v

# Run tests in parallel (faster)
pytest -n auto
```

**Test Statistics:**
- Total tests: 28
- Pass rate: 100%
- Runtime: ~0.5s
- Coverage: Comprehensive

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

## Future Enhancements

The following features are planned for future releases:

### 🔄 RabbitMQ Integration
- **Async queue for failed events**: Implement retry queue using RabbitMQ
- **Dead letter queue**: Store permanently failed events for manual review
- **Background workers**: Process retries asynchronously
- **Priority queuing**: High-priority events processed first

### 📊 Monitoring & Observability
- **Prometheus metrics**: Expose webhook processing metrics
  - Request rate, latency, error rate
  - Event type distribution
  - Retry statistics
- **Grafana dashboards**: Pre-built dashboards for visualization
- **OpenTelemetry tracing**: Distributed tracing for debugging
- **Alert rules**: Automated alerts for failures

### 🔐 Enhanced Security
- **Rate limiting**: Per-IP and per-endpoint rate limits
- **API key authentication**: Optional API key in addition to signatures
- **Signature rotation**: Support for multiple active signature keys
- **Request replay protection**: Timestamp-based replay attack prevention

### 🎯 Advanced Features
- **Webhook replay**: Admin endpoint to replay failed events
- **Event filtering**: Configure which event types to process
- **Custom handlers**: Plugin system for custom event handlers
- **Batch processing**: Process multiple events in a single request
- **Event transformation**: Transform events before processing

### 📈 Performance Optimization
- **Connection pooling**: Optimize database connection management
- **Caching layer**: Redis cache for frequent queries
- **Bulk inserts**: Batch database operations for efficiency
- **Async processing**: Move heavy processing to background tasks

### 🛠️ Developer Experience
- **Web UI**: Admin dashboard for viewing webhook history
- **Event simulator**: Test webhook processing without external calls
- **Webhook logs**: Detailed logs with request/response payloads
- **CLI tools**: Command-line utilities for common tasks

### 📦 Deployment
- **Docker Compose**: Complete local development stack
- **Kubernetes manifests**: Production-ready K8s deployment
- **Helm charts**: Simplified K8s deployments
- **CI/CD pipelines**: Automated testing and deployment

### Implementation Priority

**Phase 1 (High Priority)**
1. RabbitMQ retry queue integration
2. Prometheus metrics
3. Rate limiting
4. Docker Compose setup

**Phase 2 (Medium Priority)**
1. Webhook replay functionality
2. Web UI for webhook history
3. Event simulator
4. OpenTelemetry tracing

**Phase 3 (Future)**
1. Advanced caching
2. Batch processing
3. Plugin system
4. Kubernetes deployment

## Contributing

1. Create a feature branch
2. Make your changes
3. Run linter: `ruff check . --fix`
4. Format code: `ruff format .`
5. Create migration if models changed: `alembic revision --autogenerate -m "description"`
6. Run tests: `pytest`
7. Submit a pull request

**Code Quality Standards:**
- Maintain 100% test coverage for new features
- Follow TDD approach (tests first)
- Use type hints throughout
- Write comprehensive docstrings
- Keep functions focused and small
- Follow the existing architecture patterns

## License

[Your License Here]
