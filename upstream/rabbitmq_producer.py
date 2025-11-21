"""
RabbitMQ Producer for Recommendation System
Produces messages with schema: item_id, process_time, user_id
"""
import json
import time
from typing import Optional
import logging
import pika
from pika.exceptions import AMQPConnectionError, AMQPChannelError

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class RecommendationProducer:
    """RabbitMQ producer for recommendation system data"""
    
    def __init__(
        self,
        host: str = 'localhost',
        port: int = 5672,
        queue: str = 'recommendation-events',
        username: str = 'guest',
        password: str = 'guest'
    ):
        """
        Initialize the RabbitMQ producer
        
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
        self._connect()
    
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
        except AMQPConnectionError as e:
            logger.error(f"Failed to connect to RabbitMQ: {e}")
            raise
        except Exception as e:
            logger.error(f"Unexpected error connecting to RabbitMQ: {e}")
            raise
    
    def send_event(self, user_id: str, item_id: str, action: str, process_time: Optional[float] = None) -> bool:
        """
        Send a recommendation event to RabbitMQ
        
        Args:
            user_id: User identifier
            item_id: Item identifier
            action: User action (click, cart, or purchase)
            process_time: Processing timestamp (default: current time)
        
        Returns:
            bool: True if message was sent successfully, False otherwise
        """
        if process_time is None:
            process_time = time.time()
        
        event = {
            'user_id': user_id,
            'item_id': item_id,
            'action': action,
            'process_time': process_time
        }
        
        try:
            # Ensure channel is open
            if self.channel.is_closed:
                self._connect()
            
            # Publish message
            self.channel.basic_publish(
                exchange='',
                routing_key=self.queue,
                body=json.dumps(event).encode('utf-8'),
                properties=pika.BasicProperties(
                    delivery_mode=2,  # Make message persistent
                    headers={'user_id': user_id}  # Add user_id as header for routing
                )
            )
            
            logger.info(
                f"Message sent successfully - Queue: {self.queue}, "
                f"User: {user_id}, Item: {item_id}, Action: {action}"
            )
            return True
        except (AMQPConnectionError, AMQPChannelError) as e:
            logger.error(f"Failed to send message: {e}")
            # Try to reconnect
            try:
                self._connect()
            except Exception:
                pass
            return False
        except Exception as e:
            logger.error(f"Unexpected error sending message: {e}")
            return False
    
    def send_batch(self, events: list) -> int:
        """
        Send multiple events in batch
        
        Args:
            events: List of dicts with 'user_id', 'item_id', 'action', and optionally 'process_time'
        
        Returns:
            int: Number of successfully sent messages
        """
        success_count = 0
        for event in events:
            if self.send_event(
                user_id=event['user_id'],
                item_id=event['item_id'],
                action=event['action'],
                process_time=event.get('process_time')
            ):
                success_count += 1
        return success_count
    
    def flush(self):
        """Flush all pending messages (no-op for RabbitMQ, messages are sent immediately)"""
        # RabbitMQ sends messages immediately, so this is a no-op
        # But we can ensure the connection is still alive
        if self.connection and not self.connection.is_closed:
            self.connection.process_data_events(time_limit=0)
        logger.info("All pending messages flushed")
    
    def close(self):
        """Close the producer connection"""
        try:
            if self.channel and not self.channel.is_closed:
                self.channel.close()
            if self.connection and not self.connection.is_closed:
                self.connection.close()
            logger.info("Producer connection closed")
        except Exception as e:
            logger.warning(f"Error closing connection: {e}")


def main():
    """Example usage of the RecommendationProducer"""
    producer = RecommendationProducer(
        host='localhost',
        port=5672,
        queue='recommendation-events'
    )
    
    try:
        # Send some sample events
        sample_events = [
            {'user_id': 'user_001', 'item_id': 'item_123', 'action': 'click'},
            {'user_id': 'user_002', 'item_id': 'item_456', 'action': 'cart'},
            {'user_id': 'user_001', 'item_id': 'item_789', 'action': 'purchase'},
        ]
        
        print("Sending sample events...")
        for event in sample_events:
            producer.send_event(
                user_id=event['user_id'],
                item_id=event['item_id'],
                action=event['action']
            )
            time.sleep(0.1)  # Small delay between messages
        
        # Flush to ensure all messages are sent
        producer.flush()
        print("All events sent successfully!")
        
    except KeyboardInterrupt:
        print("\nInterrupted by user")
    finally:
        producer.close()


if __name__ == '__main__':
    main()

