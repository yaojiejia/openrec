"""
Example script demonstrating RabbitMQ producer and consumer usage
"""
import time
import threading
import sys
import os

# Handle imports whether running as script or module
if __name__ == '__main__':
    # Add parent directory to path when running as script
    sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    from upstream.rabbitmq_producer import RecommendationProducer
    from upstream.rabbitmq_consumer import RecommendationConsumer
else:
    from .rabbitmq_producer import RecommendationProducer
    from .rabbitmq_consumer import RecommendationConsumer


def run_producer():
    """Run producer in a separate thread"""
    producer = RecommendationProducer(
        host='localhost',
        port=5672,
        queue='recommendation-events'
    )
    
    try:
        print("Producer: Starting to send events...")
        for i in range(10):
            user_id = f'user_{i % 3 + 1:03d}'  # Cycle through 3 users
            item_id = f'item_{i + 100}'
            
            producer.send_event(
                user_id=user_id,
                item_id=item_id
            )
            print(f"Producer: Sent event {i+1}/10 - User: {user_id}, Item: {item_id}")
            time.sleep(0.5)
        
        producer.flush()
        print("Producer: All events sent!")
    except Exception as e:
        print(f"Producer error: {e}")
    finally:
        producer.close()


def run_consumer():
    """Run consumer in a separate thread"""
    consumer = RecommendationConsumer(
        host='localhost',
        port=5672,
        queue='recommendation-events'
    )
    
    def message_handler(message_data, metadata):
        print(f"Consumer: Received - User: {message_data['user_id']}, "
              f"Item: {message_data['item_id']}, "
              f"Time: {message_data['process_time']}")
    
    try:
        print("Consumer: Starting to consume messages...")
        consumer.consume(message_handler=message_handler)
    except Exception as e:
        print(f"Consumer error: {e}")
    finally:
        consumer.close()


if __name__ == '__main__':
    print("=" * 60)
    print("RabbitMQ Recommendation System - Example Usage")
    print("=" * 60)
    print("\nThis example demonstrates:")
    print("1. Producer sending 10 sample events")
    print("2. Consumer receiving and processing events")
    print("\nNote: Make sure RabbitMQ is running on localhost:5672")
    print("=" * 60)
    
    # Run consumer in background thread
    consumer_thread = threading.Thread(target=run_consumer, daemon=True)
    consumer_thread.start()
    
    # Give consumer time to connect
    time.sleep(2)
    
    # Run producer in main thread
    run_producer()
    
    # Keep consumer running for a bit to process messages
    print("\nWaiting for consumer to process remaining messages...")
    time.sleep(5)
    
    print("\nExample completed!")

