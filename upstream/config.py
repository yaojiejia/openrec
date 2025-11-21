"""
Configuration file for RabbitMQ recommendation system
"""
import os
from dotenv import load_dotenv

load_dotenv()

# RabbitMQ Configuration
RABBITMQ_HOST = os.getenv('RABBITMQ_HOST', 'localhost')
RABBITMQ_PORT = int(os.getenv('RABBITMQ_PORT', '5672'))
RABBITMQ_QUEUE = os.getenv('RABBITMQ_QUEUE', 'recommendation-events')
RABBITMQ_USERNAME = os.getenv('RABBITMQ_USERNAME', 'guest')
RABBITMQ_PASSWORD = os.getenv('RABBITMQ_PASSWORD', 'guest')

# Message Schema
REQUIRED_FIELDS = ['user_id', 'item_id', 'process_time']

