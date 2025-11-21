"""
Message Processor
Consumes messages from RabbitMQ, transforms them, and stores in Parquet
"""
import logging
import sys
import os
from typing import Optional
import signal
import threading
import time

# Add parent directory to path
_parent_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _parent_dir not in sys.path:
    sys.path.insert(0, _parent_dir)

from upstream.rabbitmq_consumer import RecommendationConsumer
from upstream.config import (
    RABBITMQ_HOST,
    RABBITMQ_PORT,
    RABBITMQ_QUEUE,
    RABBITMQ_USERNAME,
    RABBITMQ_PASSWORD
)
from .transformer import MessageTransformer
from .parquet_writer import ParquetWriter

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Import metrics
from monitoring.metrics import (
    start_metrics_server,
    start_system_metrics_collection,
    stop_system_metrics_collection,
    messages_processed_total,
    messages_flushed_total,
    parquet_write_duration,
    parquet_write_size,
    buffer_size
)


class MessageProcessor:
    """Processes messages from RabbitMQ: consume -> transform -> store in Parquet"""
    
    def __init__(
        self,
        parquet_base_path: str = "data/parquet",
        parquet_table_name: str = "recommendation_events",
        batch_size: int = 20,
        flush_interval_seconds: float = 5.0
    ):
        """
        Initialize the message processor
        
        Args:
            parquet_base_path: Base path for Parquet storage
            parquet_table_name: Name of the Parquet table/dataset
            batch_size: Number of messages to batch before writing to Parquet
            flush_interval_seconds: Time interval (seconds) to flush buffer even if not full (for near real-time)
        """
        self.batch_size = batch_size
        self.flush_interval = flush_interval_seconds
        self.message_buffer = []
        self.buffer_lock = threading.Lock()
        self.running = True
        self.flush_timer = None
        
        # Initialize components
        self.consumer = RecommendationConsumer(
            host=RABBITMQ_HOST,
            port=RABBITMQ_PORT,
            queue=RABBITMQ_QUEUE,
            username=RABBITMQ_USERNAME,
            password=RABBITMQ_PASSWORD
        )
        
        self.transformer = MessageTransformer()
        self.parquet_writer = ParquetWriter(
            base_path=parquet_base_path,
            table_name=parquet_table_name
        )
        
        # Start Prometheus metrics server
        start_metrics_server(port=8002)
        start_system_metrics_collection(interval=5.0)
        logger.info("Prometheus metrics enabled on port 8002")
        
        logger.info("Message processor initialized")
    
    def _process_message(self, message_data: dict, metadata: dict):
        """
        Process a single message: transform and write to Parquet
        
        Args:
            message_data: Message data from RabbitMQ
            metadata: Message metadata
        """
        try:
            # Transform message
            transformed = self.transformer.transform(message_data)
            
            # Add to buffer (thread-safe)
            with self.buffer_lock:
                self.message_buffer.append(transformed)
                
                # Update buffer size metric
                buffer_size.set(len(self.message_buffer))
                
                # Write batch if buffer is full (size-based flush)
                if len(self.message_buffer) >= self.batch_size:
                    self._flush_buffer(trigger='size_based')
            
            # Track metrics
            action = message_data.get('action', 'unknown')
            messages_processed_total.labels(action=action).inc()
            
            logger.info(
                f"Processed message - User: {message_data['user_id']}, "
                f"Item: {message_data['item_id']}, "
                f"Action: {message_data.get('action', 'unknown')}, "
                f"Hit Flink: {transformed['hit_flink']}"
            )
            
        except Exception as e:
            logger.error(f"Error processing message: {e}")
    
    def _flush_buffer(self, trigger: str = 'unknown'):
        """
        Flush the message buffer to Parquet (thread-safe)
        
        Args:
            trigger: What triggered the flush ('size_based', 'time_based', 'shutdown')
        """
        import time as time_module
        
        with self.buffer_lock:
            if not self.message_buffer:
                return
            
            try:
                # Copy buffer and clear it
                messages_to_write = self.message_buffer.copy()
                self.message_buffer.clear()
                
                # Update buffer size metric
                buffer_size.set(0)
            except Exception as e:
                logger.error(f"Error preparing buffer for flush: {e}")
                return
        
        # Write outside the lock to avoid blocking message processing
        start_time = time_module.time()
        try:
            count = self.parquet_writer.write_batch(messages_to_write)
            
            # Track metrics
            duration = time_module.time() - start_time
            parquet_write_duration.observe(duration)
            parquet_write_size.observe(count)
            messages_flushed_total.labels(trigger=trigger).inc()
            
            logger.info(f"Flushed {count} messages to Parquet (trigger: {trigger})")
        except Exception as e:
            logger.error(f"Error flushing buffer to Parquet: {e}")
    
    def _time_based_flush(self):
        """Background thread function for time-based flushing"""
        while self.running:
            time.sleep(self.flush_interval)
            if self.running and self.message_buffer:
                logger.debug(f"Time-based flush triggered (interval: {self.flush_interval}s)")
                self._flush_buffer(trigger='time_based')
    
    def start(self):
        """Start processing messages"""
        logger.info("Starting message processor...")
        logger.info(f"Batch size: {self.batch_size}")
        logger.info(f"Flush interval: {self.flush_interval} seconds")
        logger.info(f"Parquet table: {self.parquet_writer.table_path}")
        
        # Start time-based flush thread
        self.flush_timer = threading.Thread(target=self._time_based_flush, daemon=True)
        self.flush_timer.start()
        logger.info("Time-based flush thread started")
        
        try:
            # Start consuming with message handler
            self.consumer.consume(message_handler=self._process_message)
        except KeyboardInterrupt:
            logger.info("Processor interrupted by user")
        except Exception as e:
            logger.error(f"Error in processor: {e}")
        finally:
            # Stop time-based flush
            self.running = False
            if self.flush_timer:
                self.flush_timer.join(timeout=1.0)
            
            # Flush any remaining messages
            self._flush_buffer(trigger='shutdown')
            self.consumer.close()
            
            # Stop metrics collection
            stop_system_metrics_collection()
            
            logger.info("Message processor stopped")


def main():
    """Main entry point for the processor"""
    processor = MessageProcessor(
        parquet_base_path="data/parquet",
        parquet_table_name="recommendation_events",
        batch_size=20,  # Flush when 20 messages are buffered
        flush_interval_seconds=5.0  # Or flush every 5 seconds (whichever comes first)
    )
    
    try:
        processor.start()
    except KeyboardInterrupt:
        logger.info("Processor stopped by user")


if __name__ == '__main__':
    main()

