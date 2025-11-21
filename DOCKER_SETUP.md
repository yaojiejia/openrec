# Docker Setup Guide

This guide explains how to run the entire recommendation system using Docker Compose.

## Quick Start

### 1. Build and Start All Services

```bash
docker-compose up -d
```

This will start:
- **RabbitMQ** (port 5672, Management UI: 15672)
- **Upstream API** (port 8000, Metrics: 8001)
- **Message Processor** (Metrics: 8002)
- **Prometheus** (port 9090)
- **Grafana** (port 3000)

### 2. Check Service Status

```bash
docker-compose ps
```

### 3. View Logs

View all logs:
```bash
docker-compose logs -f
```

View specific service logs:
```bash
docker-compose logs -f upstream
docker-compose logs -f process
docker-compose logs -f rabbitmq
```

### 4. Stop All Services

```bash
docker-compose down
```

To also remove volumes (data):
```bash
docker-compose down -v
```

## Service URLs

- **HTTP API**: http://localhost:8000
  - Health check: http://localhost:8000/health
  - API docs: http://localhost:8000/docs
  
- **RabbitMQ Management**: http://localhost:15672
  - Username: `guest`
  - Password: `guest`

- **Prometheus**: http://localhost:9090

- **Grafana**: http://localhost:3000
  - Username: `admin`
  - Password: `admin`

## Testing the System

### Send a test event:

```bash
curl -X POST http://localhost:8000/update \
  -H "Content-Type: application/json" \
  -d '{
    "user_id": "user_001",
    "item_id": "item_123",
    "action": "click",
    "process_time": null
  }'
```

### Send batch events:

```bash
curl -X POST http://localhost:8000/update/batch \
  -H "Content-Type: application/json" \
  -d '[
    {
      "user_id": "user_001",
      "item_id": "item_123",
      "action": "click"
    },
    {
      "user_id": "user_002",
      "item_id": "item_456",
      "action": "cart"
    }
  ]'
```

## Data Persistence

Data is stored in Docker volumes:
- `rabbitmq_data` - RabbitMQ messages and queues
- `parquet_data` - Processed Parquet files
- `prometheus_data` - Prometheus metrics history
- `grafana_data` - Grafana dashboards and settings

To view volume locations:
```bash
docker volume ls
docker volume inspect openrec_parquet_data
```

## Rebuilding Services

After code changes, rebuild and restart:

```bash
# Rebuild specific service
docker-compose build upstream
docker-compose up -d upstream

# Rebuild all services
docker-compose build
docker-compose up -d
```

## Troubleshooting

### Service won't start

1. Check logs:
   ```bash
   docker-compose logs <service-name>
   ```

2. Check if ports are already in use:
   ```bash
   # Windows PowerShell
   netstat -ano | findstr :8000
   ```

3. Restart a specific service:
   ```bash
   docker-compose restart <service-name>
   ```

### Prometheus can't scrape metrics

1. Check if services are healthy:
   ```bash
   docker-compose ps
   ```

2. Check Prometheus targets: http://localhost:9090/targets

3. Verify network connectivity:
   ```bash
   docker-compose exec prometheus ping upstream
   docker-compose exec prometheus ping process
   ```

### Grafana dashboard not showing data

1. Verify Prometheus datasource is configured: http://localhost:3000/connections/datasources
2. Check if metrics are being collected: http://localhost:9090/graph
3. Verify services are sending metrics:
   - http://localhost:8001/metrics (Upstream)
   - http://localhost:8002/metrics (Processor)

## Environment Variables

You can override default settings using a `.env` file or environment variables:

```env
RABBITMQ_HOST=rabbitmq
RABBITMQ_PORT=5672
RABBITMQ_QUEUE=recommendation-events
RABBITMQ_USERNAME=guest
RABBITMQ_PASSWORD=guest
PARQUET_BASE_PATH=/app/data/parquet
PARQUET_TABLE_NAME=recommendation_events
BATCH_SIZE=20
```

## Development Mode

For development, you can run services individually:

```bash
# Start only infrastructure
docker-compose up -d rabbitmq prometheus grafana

# Run services locally (outside Docker)
python upstream/http_api.py
python -m process.processor
```

