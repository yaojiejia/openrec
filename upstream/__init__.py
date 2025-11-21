"""
Upstream package for recommendation system (RabbitMQ integration)
"""
from .rabbitmq_producer import RecommendationProducer
from .rabbitmq_consumer import RecommendationConsumer
from .config import (
    RABBITMQ_HOST,
    RABBITMQ_PORT,
    RABBITMQ_QUEUE,
    RABBITMQ_USERNAME,
    RABBITMQ_PASSWORD,
    REQUIRED_FIELDS
)

__all__ = [
    'RecommendationProducer',
    'RecommendationConsumer',
    'RABBITMQ_HOST',
    'RABBITMQ_PORT',
    'RABBITMQ_QUEUE',
    'RABBITMQ_USERNAME',
    'RABBITMQ_PASSWORD',
    'REQUIRED_FIELDS'
]

