# Monitoring Setup Guide

This guide explains how to set up Grafana + Prometheus monitoring for the recommendation system.

## Quick Start

### 1. Install Dependencies

```bash
pip install prometheus-client psutil
```

### 2. Start Your Services

The services automatically expose metrics when started:

**Terminal 1 - HTTP API:**
```bash
python upstream/http_api.py
```
- API: http://localhost:8000
- Metrics: http://localhost:8001/metrics

**Terminal 2 - Message Processor:**
```bash
python -m process.processor
```
- Metrics: http://localhost:8002/metrics

### 3. Start Prometheus and Grafana

```bash
docker-compose -f docker-compose.monitoring.yml up -d
```

### 4. Access Dashboards

- **Prometheus**: http://localhost:9090
- **Grafana**: http://localhost:3000
  - Username: `admin`
  - Password: `admin`

## Metrics Available

### HTTP API Metrics (Port 8001)
- `http_requests_total` - Total requests by method, endpoint, status
- `http_request_duration_seconds` - Request latency
- `events_sent_total` - Events sent by action (click/cart/purchase)
- `events_sent_batch_size` - Batch size distribution

### Processor Metrics (Port 8002)
- `messages_processed_total` - Messages processed by action
- `messages_flushed_total` - Batches flushed by trigger
- `parquet_write_duration_seconds` - Write latency
- `parquet_write_size_messages` - Messages per write
- `processor_buffer_size` - Current buffer size

### System Metrics (Both)
- `system_cpu_percent` - System CPU usage
- `system_memory_percent` - System memory usage
- `process_cpu_percent` - Process CPU by service
- `process_memory_mb` - Process memory by service

## Troubleshooting

### Prometheus Can't Scrape Metrics

**Windows/Mac:** The config uses `host.docker.internal` which should work automatically.

**Linux:** You may need to change `host.docker.internal` to `172.17.0.1` in `prometheus/prometheus.yml`, or use `network_mode: host` in docker-compose.

### Metrics Not Showing

1. Check metrics endpoints are accessible:
   - http://localhost:8001/metrics
   - http://localhost:8002/metrics

2. Verify Prometheus targets:
   - Go to http://localhost:9090/targets
   - Check if targets are "UP"

3. Check Prometheus logs:
   ```bash
   docker logs prometheus
   ```

### Grafana Dashboard Not Loading

1. Check Grafana logs:
   ```bash
   docker logs grafana
   ```

2. Verify datasource:
   - Go to Configuration > Data Sources
   - Ensure Prometheus is configured and working

3. Import dashboard manually if needed:
   - Go to Dashboards > Import
   - Upload `grafana/dashboards/recommendation-system.json`

## Stopping Monitoring

```bash
docker-compose -f docker-compose.monitoring.yml down
```

To remove data volumes:
```bash
docker-compose -f docker-compose.monitoring.yml down -v
```

