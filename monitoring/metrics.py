"""
Prometheus Metrics for Recommendation System
Exposes metrics for HTTP API and Message Processor
"""
from prometheus_client import Counter, Histogram, Gauge, start_http_server
import psutil
import os
import sys
import logging
import threading
import time

logger = logging.getLogger(__name__)

# HTTP API Metrics
http_requests_total = Counter(
    'http_requests_total',
    'Total HTTP requests',
    ['method', 'endpoint', 'status']
)

http_request_duration = Histogram(
    'http_request_duration_seconds',
    'HTTP request duration in seconds',
    ['method', 'endpoint']
)

events_sent_total = Counter(
    'events_sent_total',
    'Total events sent to RabbitMQ',
    ['action']  # click, cart, purchase
)

events_sent_batch_size = Histogram(
    'events_sent_batch_size',
    'Batch size of events sent',
    buckets=[1, 5, 10, 20, 50, 100, 200, 500]
)

# Message Processor Metrics
messages_processed_total = Counter(
    'messages_processed_total',
    'Total messages processed',
    ['action']
)

messages_flushed_total = Counter(
    'messages_flushed_total',
    'Total message batches flushed to Parquet',
    ['trigger']  # size_based, time_based, shutdown
)

parquet_write_duration = Histogram(
    'parquet_write_duration_seconds',
    'Time taken to write batch to Parquet',
    buckets=[0.001, 0.005, 0.01, 0.05, 0.1, 0.5, 1.0, 5.0]
)

parquet_write_size = Histogram(
    'parquet_write_size_messages',
    'Number of messages written per Parquet file',
    buckets=[1, 5, 10, 20, 50, 100, 200, 500]
)

# System Metrics
system_cpu_usage = Gauge(
    'system_cpu_percent',
    'System CPU usage percentage'
)

system_memory_usage = Gauge(
    'system_memory_percent',
    'System memory usage percentage'
)

process_cpu_usage = Gauge(
    'process_cpu_percent',
    'Process CPU usage percentage',
    ['service']  # http_api, processor
)

process_memory_usage = Gauge(
    'process_memory_mb',
    'Process memory usage in MB',
    ['service']
)

# RabbitMQ Metrics
rabbitmq_queue_depth = Gauge(
    'rabbitmq_queue_depth',
    'Number of messages in RabbitMQ queue',
    ['queue']
)

buffer_size = Gauge(
    'processor_buffer_size',
    'Current number of messages in processor buffer'
)


def start_metrics_server(port: int = 8001):
    """
    Start Prometheus metrics HTTP server
    
    Args:
        port: Port to expose metrics on (default: 8001)
    """
    try:
        start_http_server(port)
        logger.info(f"Prometheus metrics server started on port {port}")
    except Exception as e:
        logger.error(f"Failed to start metrics server: {e}")


def update_system_metrics():
    """Update system-level metrics (CPU, memory)"""
    try:
        # System-wide metrics
        system_cpu_usage.set(psutil.cpu_percent(interval=0.1))
        system_memory_usage.set(psutil.virtual_memory().percent)
        
        # Process-specific metrics
        current_process = psutil.Process(os.getpid())
        process_name = os.path.basename(sys.argv[0]) if 'sys' in dir() else 'unknown'
        
        process_cpu_usage.labels(service=process_name).set(current_process.cpu_percent(interval=0.1))
        process_memory_usage.labels(service=process_name).set(current_process.memory_info().rss / 1024 / 1024)  # MB
    except Exception as e:
        logger.debug(f"Error updating system metrics: {e}")


# Background thread to update system metrics periodically
_metrics_thread = None
_running = False


def start_system_metrics_collection(interval: float = 5.0):
    """
    Start background thread to collect system metrics
    
    Args:
        interval: How often to update metrics (seconds)
    """
    global _metrics_thread, _running
    
    if _running:
        return
    
    _running = True
    
    def collect_metrics():
        while _running:
            update_system_metrics()
            time.sleep(interval)
    
    _metrics_thread = threading.Thread(target=collect_metrics, daemon=True)
    _metrics_thread.start()
    logger.info(f"System metrics collection started (interval: {interval}s)")


def stop_system_metrics_collection():
    """Stop background metrics collection"""
    global _running
    _running = False

