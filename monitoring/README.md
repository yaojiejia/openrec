# Monitoring Setup

This directory contains Prometheus metrics instrumentation for the recommendation system.

## Metrics Exposed

### HTTP API Metrics (Port 8001)
- `http_requests_total` - Total HTTP requests by method, endpoint, and status
- `http_request_duration_seconds` - HTTP request latency
- `events_sent_total` - Total events sent to RabbitMQ by action type
- `events_sent_batch_size` - Batch size distribution

### Message Processor Metrics (Port 8002)
- `messages_processed_total` - Total messages processed by action type
- `messages_flushed_total` - Total batches flushed by trigger type
- `parquet_write_duration_seconds` - Time to write batches to Parquet
- `parquet_write_size_messages` - Number of messages per write
- `processor_buffer_size` - Current buffer size

### System Metrics (Both Services)
- `system_cpu_percent` - System CPU usage
- `system_memory_percent` - System memory usage
- `process_cpu_percent` - Process CPU usage by service
- `process_memory_mb` - Process memory usage by service

## Accessing Metrics

- HTTP API metrics: http://localhost:8001/metrics
- Processor metrics: http://localhost:8002/metrics

## Setup

1. Install dependencies:
   ```bash
   pip install prometheus-client psutil
   ```

2. Start services - metrics are automatically enabled

3. Start Prometheus and Grafana:
   ```bash
   # Using the unified docker-compose.yml
   docker-compose up -d prometheus grafana
   ```

4. Access:
   - Prometheus: http://localhost:9090
   - Grafana: http://localhost:3000 (admin/admin)

