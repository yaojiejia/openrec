# Open Recommendation System

This project implements the RabbitMQ data ingestion layer for an online recommendation system. The system is designed to handle real-time recommendation events with the following data schema:

- **user_id**: User identifier
- **item_id**: Item identifier  
- **process_time**: Processing timestamp

## Architecture

```
┌─────────────┐
│ HTTP Client │
└──────┬──────┘
       │ POST /update
       ▼
┌──────────────────┐
│  HTTP API Service│  (upstream/http_api.py)
│  (FastAPI)       │
└──────┬───────────┘
       │
       ▼
┌──────────────────┐
│ RabbitMQ Producer│  (upstream/rabbitmq_producer.py)
└──────┬───────────┘
       │
       ▼
┌──────────────────┐
│ RabbitMQ Queue   │  (recommendation-events)
│  (Message Broker)│
└──────┬───────────┘
       │
       ▼
┌──────────────────┐
│ Message Processor│  (process/processor.py)
│  - Consumer      │
│  - Transformer   │
│  - Parquet Writer│
└──────┬───────────┘
       │
       ▼
┌──────────────────┐
│  Parquet Files   │  (data/parquet/recommendation_events/)
│  (Date Partitioned)│
└──────────────────┘
```

### Component Overview

1. **HTTP API Service** (`upstream/http_api.py`): FastAPI service that receives HTTP requests and publishes events to RabbitMQ
2. **RabbitMQ**: Message broker that queues events for processing
3. **Message Processor** (`process/processor.py`): Consumes messages, transforms them (adds `hit_flink` field), and writes to Parquet
4. **Parquet Storage**: Columnar storage format with date-based partitioning for efficient querying

## Prerequisites

1. **RabbitMQ Installation**: You need to have RabbitMQ installed and running
   - Download from: https://www.rabbitmq.com/download.html
   - Or use Docker: `docker run -d --hostname my-rabbit --name some-rabbit -p 5672:5672 -p 15672:15672 rabbitmq:3-management`
   - Management UI will be available at http://localhost:15672 (guest/guest)

2. **Python 3.7+**

3. **Python Dependencies**: Install using pip
   ```bash
   pip install -r requirements.txt
   ```

## Setup

1. **Start RabbitMQ** (if not using Docker):
   - On Windows: Download and install from https://www.rabbitmq.com/download.html
   - On Linux/Mac: `sudo systemctl start rabbitmq-server` or `brew services start rabbitmq`
   - Or use Docker: `docker run -d -p 5672:5672 -p 15672:15672 rabbitmq:3-management`

2. **RabbitMQ Queue**: The queue will be created automatically when the producer/consumer connects. No manual setup needed.

3. **Configure Environment** (optional):
   Create a `.env` file to customize settings:
   ```
   RABBITMQ_HOST=localhost
   RABBITMQ_PORT=5672
   RABBITMQ_QUEUE=recommendation-events
   RABBITMQ_USERNAME=guest
   RABBITMQ_PASSWORD=guest
   ```

## Quick Start

### 1. Start RabbitMQ

Using Docker (recommended):
```bash
docker run -d --hostname my-rabbit --name some-rabbit -p 5672:5672 -p 15672:15672 rabbitmq:3-management
```

Management UI: http://localhost:15672 (guest/guest)

### 2. Start HTTP API Service

In one terminal:
```bash
# Activate virtual environment (if using one)
.\venv\Scripts\Activate.ps1  # Windows PowerShell
# or
source venv/bin/activate      # Linux/Mac

# Start the API server
python upstream/http_api.py
```

The API will be available at: http://localhost:8000

### 3. Start Message Processor

In another terminal:
```bash
# Activate virtual environment (if using one)
.\venv\Scripts\Activate.ps1  # Windows PowerShell
# or
source venv/bin/activate      # Linux/Mac

# Start the processor
python -m process.processor
```

The processor will:
- Consume messages from RabbitMQ
- Transform messages (add `hit_flink: true` field)
- Write to Parquet files in `data/parquet/recommendation_events/`
- Expose Prometheus metrics on port 8002

### 4. Start Monitoring (Grafana + Prometheus) - Optional

In a third terminal:
```bash
# Start Prometheus and Grafana
docker-compose -f docker-compose.monitoring.yml up -d
```

Access:
- **Prometheus**: http://localhost:9090
- **Grafana**: http://localhost:3000 (admin/admin)

The dashboard will automatically show:
- HTTP request rates and latency
- Events sent by action type (click/cart/purchase)
- Messages processed
- System CPU and memory usage
- Processor buffer size
- Parquet write performance

### 4. Send Test Events

```bash
# Send a single event
curl -X POST "http://localhost:8000/update" \
  -H "Content-Type: application/json" \
  -d '{"user_id": "user_001", "item_id": "item_123", "action": "click"}'

# Check health
curl http://localhost:8000/health
```

### Processor Configuration

The processor uses a hybrid flushing strategy for near real-time performance:
- **Batch size**: 20 messages (flushes when buffer is full)
- **Time-based flush**: Every 5 seconds (flushes even if buffer isn't full)
- **Result**: Maximum 5-second latency with efficient batching

## Usage

### Producer

The producer sends recommendation events to RabbitMQ:

```python
from upstream.rabbitmq_producer import RecommendationProducer

# Initialize producer
producer = RecommendationProducer(
    host='localhost',
    port=5672,
    queue='recommendation-events'
)

# Send a single event
producer.send_event(
    user_id='user_001',
    item_id='item_123'
)

# Send multiple events
events = [
    {'user_id': 'user_001', 'item_id': 'item_123'},
    {'user_id': 'user_002', 'item_id': 'item_456'},
]
producer.send_batch(events)

# Clean up
producer.close()
```

Run the producer example:
```bash
python upstream/rabbitmq_producer.py
```

### Consumer

The consumer reads recommendation events from RabbitMQ:

```python
from upstream.rabbitmq_consumer import RecommendationConsumer

# Initialize consumer
consumer = RecommendationConsumer(
    host='localhost',
    port=5672,
    queue='recommendation-events'
)

# Define custom message handler
def process_message(message_data, metadata):
    print(f"User {message_data['user_id']} viewed item {message_data['item_id']}")
    # Add your processing logic here

# Start consuming
consumer.consume(message_handler=process_message)
```

Run the consumer example:
```bash
python upstream/rabbitmq_consumer.py
```

Or run the combined example:
```bash
python upstream/example_usage.py
```

### HTTP API Service

The HTTP API service exposes REST endpoints to send events to RabbitMQ via HTTP requests:

**Start the API server:**
```bash
python upstream/http_api.py
```

Or using uvicorn directly:
```bash
uvicorn upstream.http_api:app --host 0.0.0.0 --port 8000
```

**Send a single event via HTTP POST:**
```bash
curl -X POST "http://localhost:8000/update" \
  -H "Content-Type: application/json" \
  -d '{
    "user_id": "user_001",
    "item_id": "item_123",
    "action": "click"
  }'
```

**Send multiple events in batch:**
```bash
curl -X POST "http://localhost:8000/update/batch" \
  -H "Content-Type: application/json" \
  -d '[
    {"user_id": "user_001", "item_id": "item_123", "action": "click"},
    {"user_id": "user_002", "item_id": "item_456", "action": "cart"}
  ]'
```

**Health check:**
```bash
curl http://localhost:8000/health
```

**API Documentation:**
Once the server is running, visit:
- Swagger UI: http://localhost:8000/docs
- ReDoc: http://localhost:8000/redoc

**Example using Python requests:**
```python
import requests

# Send single event
response = requests.post(
    "http://localhost:8000/update",
    json={
        "user_id": "user_001",
        "item_id": "item_123",
        "action": "click"
    }
)
print(response.json())

# Send batch events
response = requests.post(
    "http://localhost:8000/update/batch",
    json=[
        {"user_id": "user_001", "item_id": "item_123", "action": "click"},
        {"user_id": "user_002", "item_id": "item_456", "action": "cart"}
    ]
)
print(response.json())
```

## Data Schema

### Input Schema (HTTP API)

Each message sent to the HTTP API follows this JSON schema:

```json
{
    "user_id": "string",
    "item_id": "string",
    "action": "click",  // Required: "click", "cart", or "purchase"
    "process_time": 1234567890.123  // Optional, defaults to current time
}
```

- `user_id`: Unique identifier for the user (required)
- `item_id`: Unique identifier for the item (required)
- `action`: User action type (required) - must be one of: `"click"`, `"cart"`, or `"purchase"`
- `process_time`: Unix timestamp (float) - optional, defaults to current time

### Output Schema (Parquet)

After processing, messages stored in Parquet include an additional field:

```json
{
    "user_id": "string",
    "item_id": "string",
    "action": "click",  // click, cart, or purchase
    "process_time": 1234567890.123,
    "hit_flink": true  // Added by transformer
}
```

- `action`: User action type (click, cart, or purchase)
- `hit_flink`: Boolean field added by the message transformer (always `true`)

## Features

- **HTTP API Service**:
  - RESTful API with `/update` endpoint
  - Batch processing support (`/update/batch`)
  - Automatic request validation
  - Health check endpoint
  - Interactive API documentation (Swagger/ReDoc)
  - Error handling and proper HTTP status codes

- **Producer**:
  - Automatic message serialization (JSON)
  - Persistent message delivery (durable queues)
  - User ID in message headers for routing
  - Batch message sending
  - Error handling and automatic reconnection
  - Connection heartbeat and timeout management

- **Consumer**:
  - Automatic message deserialization
  - Message acknowledgment (ACK/NACK)
  - Message validation
  - Custom message handlers
  - Graceful shutdown handling
  - Quality of Service (QoS) control
  - Automatic requeue on processing errors

- **Message Processor**:
  - Consumes messages from RabbitMQ
  - Transforms messages (adds `hit_flink` field)
  - Hybrid flushing strategy (size-based + time-based)
  - Thread-safe buffer management
  - Writes to Parquet with date partitioning
  - Graceful shutdown with buffer flush

- **Parquet Writer**:
  - Date-based partitioning (year/month/day)
  - Snappy compression
  - Batch writing for efficiency
  - Partition reading support

## Data Flow

1. **HTTP Request** → Client sends event to `/update` endpoint
2. **HTTP API** → Validates and publishes to RabbitMQ queue
3. **RabbitMQ** → Queues message for processing
4. **Processor** → Consumes message, transforms (adds `hit_flink: true`), buffers
5. **Parquet Writer** → Writes buffered messages to Parquet files (batched by size or time)
6. **Storage** → Parquet files stored in `data/parquet/recommendation_events/` with date partitioning

## Parquet Storage

Processed messages are stored in Parquet format with:
- **Location**: `data/parquet/recommendation_events/`
- **Partitioning**: By date (year/month/day)
- **Compression**: Snappy
- **Format**: Columnar storage for efficient querying

Example path structure:
```
data/parquet/recommendation_events/
  year=2025/
    month=11/
      day=21/
        part-20251121_123456_789012.parquet
```

### Reading Parquet Data

```python
from process.parquet_writer import ParquetWriter

writer = ParquetWriter()
df = writer.read_partition(year=2025, month=11, day=21)
print(df)
```

## Next Steps

Future enhancements could include:

1. **Flink Integration**: Real-time stream processing for complex transformations
2. **Recommendation Engine**: ML models that read from Parquet to generate recommendations
3. **Monitoring**: Metrics and alerting for the processing pipeline
4. **Scaling**: Multiple processor instances for higher throughput

## Monitoring

The system includes Prometheus metrics and Grafana dashboards for monitoring.

### Metrics Endpoints

- **HTTP API Metrics**: http://localhost:8001/metrics
- **Processor Metrics**: http://localhost:8002/metrics

### Available Metrics

**HTTP API:**
- `http_requests_total` - Request count by method, endpoint, status
- `http_request_duration_seconds` - Request latency
- `events_sent_total` - Events sent by action type
- `events_sent_batch_size` - Batch size distribution

**Message Processor:**
- `messages_processed_total` - Messages processed by action
- `messages_flushed_total` - Batches flushed by trigger
- `parquet_write_duration_seconds` - Write latency
- `processor_buffer_size` - Current buffer size

**System:**
- `system_cpu_percent` - CPU usage
- `system_memory_percent` - Memory usage
- `process_cpu_percent` - Process CPU by service
- `process_memory_mb` - Process memory by service

### Setup Monitoring

1. **Install dependencies:**
   ```bash
   pip install prometheus-client psutil
   ```

2. **Start Prometheus and Grafana:**
   ```bash
   docker-compose -f docker-compose.monitoring.yml up -d
   ```

3. **Access dashboards:**
   - Prometheus: http://localhost:9090
   - Grafana: http://localhost:3000 (admin/admin)

4. **View metrics:**
   - Metrics are automatically exposed when services start
   - Grafana dashboard is pre-configured with key metrics

See `monitoring/README.md` for detailed metrics documentation.

## Troubleshooting

- **Connection Error**: Ensure RabbitMQ is running and accessible at the configured host and port
- **Queue Not Found**: The queue will be created automatically when the producer/consumer connects
- **Management UI**: Access RabbitMQ management UI at http://localhost:15672 (default: guest/guest) to monitor queues and messages
- **Check RabbitMQ Status**: 
  - Docker: `docker ps | grep rabbitmq`
  - Linux: `sudo systemctl status rabbitmq-server`
  - Check logs: `docker logs some-rabbit` (if using Docker)
- **Metrics Not Showing**: 
  - Ensure `prometheus-client` and `psutil` are installed
  - Check that metrics endpoints are accessible: http://localhost:8001/metrics and http://localhost:8002/metrics
  - Verify Prometheus can reach the services (check `prometheus/prometheus.yml` configuration)

