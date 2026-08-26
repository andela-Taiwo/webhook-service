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

## Quick Start with Docker (Recommended)

The fastest way to get started is using Docker Compose, which sets up everything automatically.

### Prerequisites
- Docker 20.10+
- Docker Compose 2.0+

### Start Everything

```bash
# Clone repository
git clone <repository-url>
cd webhook-service

# Start all services (PostgreSQL, RabbitMQ, Webhook Service)
docker-compose up -d

# View logs
docker-compose logs -f

# Services will be available at:
# - Webhook API: http://localhost:8000
# - API Docs: http://localhost:8000/docs
# - Adminer (DB UI): http://localhost:8080
# - RabbitMQ Management: http://localhost:15672 (webhook/webhook)
```

### Using Makefile Commands

```bash
make help          # Show all available commands
make up            # Start all services
make logs          # View logs
make test          # Run tests in Docker
make migrate       # Run database migrations
make shell         # Open shell in container
make clean         # Stop and remove everything
```

## Local Setup (Without Docker)

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


#### Production (docker-compose.prod.yml)
```bash
# Set required environment variables
export POSTGRES_PASSWORD=secure-password
export RABBITMQ_PASSWORD=secure-password
export WEBHOOK_SECRET_KEY=production-secret-key

# Start production stack
docker-compose -f docker-compose.prod.yml up -d

# Scale webhook service
docker-compose -f docker-compose.prod.yml up -d --scale webhook-service=3
```

### Common Docker Commands

```bash
# Development
make up                # Start all services
make down              # Stop all services
make logs              # View all logs
make logs-app          # View app logs only
make shell             # Shell into container
make restart           # Restart services

# Database
make migrate           # Run migrations
make migrate-create MSG="add field"  # Create migration
make db-reset          # Reset database
make backup-db         # Backup database
make shell-db          # PostgreSQL shell

# Testing
make test              # Run tests
make lint              # Run linter
make format            # Format code
make coverage          # Generate coverage

# Cleanup
make clean             # Remove containers
make clean-all         # Remove everything including images
```

### Environment Variables for Docker

Create a `.env` file in the project root:

```env
# Database
POSTGRES_USER=webhook
POSTGRES_PASSWORD=your-secure-password
POSTGRES_DB=webhook

# RabbitMQ
RABBITMQ_USER=webhook
RABBITMQ_PASSWORD=your-secure-password

# Application
WEBHOOK_SECRET_KEY=your-webhook-secret-key
WEBHOOK_ENVIRONMENT=production
WEBHOOK_LOG_LEVEL=INFO

# Optional
VERSION=1.0.0
OTEL_ENDPOINT=http://otel-collector:4317
```

### Health Checks

All services include health checks:

```bash
# Check webhook service health
curl http://localhost:8000/api/v1/health

# Check PostgreSQL
docker-compose exec postgres pg_isready -U webhook

# Check RabbitMQ
docker-compose exec rabbitmq rabbitmq-diagnostics ping

# Check all services
make health
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
