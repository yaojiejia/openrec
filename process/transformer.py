"""
Message Transformer
Transforms recommendation events by adding additional fields
"""
import logging
from typing import Dict, Any

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class MessageTransformer:
    """Transforms recommendation messages"""
    
    def transform(self, message: Dict[str, Any]) -> Dict[str, Any]:
        """
        Transform a message by adding the 'hit_flink' field
        
        Args:
            message: Original message with user_id, item_id, process_time
        
        Returns:
            Transformed message with added 'hit_flink' field
        """
        transformed = message.copy()
        transformed['hit_flink'] = True
        logger.debug(f"Transformed message: {transformed}")
        return transformed
    
    def transform_batch(self, messages: list[Dict[str, Any]]) -> list[Dict[str, Any]]:
        """
        Transform a batch of messages
        
        Args:
            messages: List of original messages
        
        Returns:
            List of transformed messages
        """
        return [self.transform(msg) for msg in messages]

