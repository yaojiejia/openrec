"""
RabbitMQ Consumer for Recommendation System
Consumes messages with schema: item_id, process_time, user_id
"""
import json
import logging
from typing import Callable, Optional
import signal
import sys
import pika
from pika.exceptions import AMQPConnectionError, AMQPChannelError

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class RecommendationConsumer:
    """RabbitMQ consumer for recommendation system data"""
    
    def __init__(
        self,
        host: str = 'localhost',
        port: int = 5672,
        queue: str = 'recommendation-events',
        username: str = 'guest',
        password: str = 'guest'
    ):
        """
        Initialize the RabbitMQ consumer
        
        Args:
            host: RabbitMQ host (default: localhost)
            port: RabbitMQ port (default: 5672)
            queue: Queue name (default: recommendation-events)
            username: RabbitMQ username (default: guest)
            password: RabbitMQ password (default: guest)
        """
        self.host = host
        self.port = port
        self.queue = queue
        self.username = username
        self.password = password
        self.connection = None
        self.channel = None
        self.running = True
        self._connect()
        self._setup_signal_handlers()
    
    def _connect(self):
        """Establish connection to RabbitMQ broker"""
        try:
            # Create connection parameters
            credentials = pika.PlainCredentials(self.username, self.password)
            parameters = pika.ConnectionParameters(
                host=self.host,
                port=self.port,
                credentials=credentials,
                heartbeat=600,
                blocked_connection_timeout=300
            )
            
            # Establish connection
            self.connection = pika.BlockingConnection(parameters)
            self.channel = self.connection.channel()
            
            # Declare queue (idempotent - will create if doesn't exist)
            self.channel.queue_declare(queue=self.queue, durable=True)
            
            logger.info(f"Connected to RabbitMQ broker at {self.host}:{self.port}")
            logger.info(f"Subscribed to queue: {self.queue}")
        except AMQPConnectionError as e:
            logger.error(f"Failed to connect to RabbitMQ: {e}")
            raise
        except Exception as e:
            logger.error(f"Unexpected error connecting to RabbitMQ: {e}")
            raise
    
    def _setup_signal_handlers(self):
        """Setup signal handlers for graceful shutdown"""
        def signal_handler(sig, frame):
            logger.info("Received interrupt signal, shutting down gracefully...")
            self.running = False
        
        signal.signal(signal.SIGINT, signal_handler)
        signal.signal(signal.SIGTERM, signal_handler)
    
    def _validate_message(self, message: dict) -> bool:
        """
        Validate that message contains required fields
        
        Args:
            message: Message dictionary
        
        Returns:
            bool: True if message is valid, False otherwise
        """
        required_fields = ['user_id', 'item_id', 'process_time']
        for field in required_fields:
            if field not in message:
                logger.warning(f"Message missing required field: {field}")
                return False
        return True
    
    def consume(self, message_handler: Optional[Callable] = None):
        """
        Start consuming messages from RabbitMQ
        
        Args:
            message_handler: Optional callback function to process each message.
                            Should accept (message_dict, metadata_dict) as arguments.
                            If None, messages are just logged.
        """
        logger.info("Starting to consume messages...")
        
        def callback(ch, method, properties, body):
            """Internal callback for RabbitMQ message delivery"""
            try:
                # Deserialize message
                message_data = json.loads(body.decode('utf-8'))
                
                # Extract metadata
                metadata = {
                    'queue': self.queue,
                    'delivery_tag': method.delivery_tag,
                    'routing_key': method.routing_key,
                    'exchange': method.exchange,
                    'headers': properties.headers or {},
                    'timestamp': properties.timestamp if hasattr(properties, 'timestamp') else None
                }
                
                # Validate message
                if not self._validate_message(message_data):
                    logger.warning(f"Invalid message, rejecting...")
                    ch.basic_nack(delivery_tag=method.delivery_tag, requeue=False)
                    return
                
                # Process message
                try:
                    if message_handler:
                        message_handler(message_data, metadata)
                    else:
                        self._default_handler(message_data, metadata)
                    
                    # Acknowledge message
                    ch.basic_ack(delivery_tag=method.delivery_tag)
                except Exception as e:
                    logger.error(f"Error processing message: {e}")
                    # Reject and requeue on error
                    ch.basic_nack(delivery_tag=method.delivery_tag, requeue=True)
                    
            except json.JSONDecodeError as e:
                logger.error(f"Failed to decode message: {e}")
                ch.basic_nack(delivery_tag=method.delivery_tag, requeue=False)
            except Exception as e:
                logger.error(f"Unexpected error in callback: {e}")
                ch.basic_nack(delivery_tag=method.delivery_tag, requeue=True)
        
        try:
            # Set QoS to process one message at a time
            self.channel.basic_qos(prefetch_count=1)
            
            # Start consuming
            self.channel.basic_consume(
                queue=self.queue,
                on_message_callback=callback
            )
            
            logger.info("Waiting for messages. To exit press CTRL+C")
            
            # Start consuming (blocking call)
            while self.running:
                try:
                    self.connection.process_data_events(time_limit=1)
                except KeyboardInterrupt:
                    self.running = False
                    break
                    
        except AMQPConnectionError as e:
            logger.error(f"RabbitMQ connection error: {e}")
        except Exception as e:
            logger.error(f"Unexpected error: {e}")
        finally:
            self.close()
    
    def _default_handler(self, message_data: dict, metadata: dict):
        """Default message handler that logs the message"""
        logger.info(
            f"Received message - User: {message_data['user_id']}, "
            f"Item: {message_data['item_id']}, "
            f"Process Time: {message_data['process_time']}, "
            f"Queue: {metadata['queue']}, "
            f"Delivery Tag: {metadata['delivery_tag']}"
        )
    
    def close(self):
        """Close the consumer connection"""
        try:
            if self.channel and not self.channel.is_closed:
                self.channel.stop_consuming()
                self.channel.close()
            if self.connection and not self.connection.is_closed:
                self.connection.close()
            logger.info("Consumer connection closed")
        except Exception as e:
            logger.warning(f"Error closing connection: {e}")


def main():
    """Example usage of the RecommendationConsumer"""
    consumer = RecommendationConsumer(
        host='localhost',
        port=5672,
        queue='recommendation-events'
    )
    
    # Custom message handler example
    def custom_handler(message_data: dict, metadata: dict):
        """Custom handler to process messages"""
        print(f"User {message_data['user_id']} "
              f"interacted with item {message_data['item_id']}")
        # Here you could add logic to forward to Flink or store in Parquet
    
    try:
        consumer.consume(message_handler=custom_handler)
    except KeyboardInterrupt:
        logger.info("Consumer stopped by user")


if __name__ == '__main__':
    main()

