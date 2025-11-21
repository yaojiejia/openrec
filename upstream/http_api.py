"""
HTTP API Service for Recommendation System
Exposes HTTP endpoints to send events to RabbitMQ
"""
import logging
import sys
import os
from typing import Optional, Literal
from fastapi import FastAPI, HTTPException
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field

# Add parent directory to path to allow imports
_parent_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _parent_dir not in sys.path:
    sys.path.insert(0, _parent_dir)

# Import from the upstream package
from upstream.rabbitmq_producer import RecommendationProducer
from upstream.config import (
    RABBITMQ_HOST,
    RABBITMQ_PORT,
    RABBITMQ_QUEUE,
    RABBITMQ_USERNAME,
    RABBITMQ_PASSWORD
)

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Initialize FastAPI app
app = FastAPI(
    title="Recommendation System API",
    description="HTTP API for sending recommendation events to RabbitMQ",
    version="1.0.0"
)

# Initialize RabbitMQ producer (singleton)
producer: Optional[RecommendationProducer] = None


class RecommendationEvent(BaseModel):
    """Schema for recommendation event"""
    user_id: str = Field(..., description="User identifier")
    item_id: str = Field(..., description="Item identifier")
    action: Literal["click", "cart", "purchase"] = Field(..., description="User action: click, cart, or purchase")
    process_time: Optional[float] = Field(None, description="Processing timestamp (optional, defaults to current time)")


class EventResponse(BaseModel):
    """Response model for event submission"""
    success: bool
    message: str
    user_id: str
    item_id: str


@app.on_event("startup")
async def startup_event():
    """Initialize RabbitMQ producer on startup"""
    global producer
    try:
        producer = RecommendationProducer(
            host=RABBITMQ_HOST,
            port=RABBITMQ_PORT,
            queue=RABBITMQ_QUEUE,
            username=RABBITMQ_USERNAME,
            password=RABBITMQ_PASSWORD
        )
        logger.info("RabbitMQ producer initialized successfully")
    except Exception as e:
        logger.warning(f"Failed to initialize RabbitMQ producer: {e}")
        logger.warning("Server will start but /update endpoint will return 503 until RabbitMQ is available")
        producer = None


@app.on_event("shutdown")
async def shutdown_event():
    """Close RabbitMQ producer on shutdown"""
    global producer
    if producer:
        producer.close()
        logger.info("RabbitMQ producer closed")


@app.post("/update", response_model=EventResponse)
async def update_event(event: RecommendationEvent):
    """
    Send a recommendation event to RabbitMQ
    
    Args:
        event: Recommendation event containing user_id, item_id, and optional process_time
    
    Returns:
        EventResponse: Success status and event details
    """
    if producer is None:
        raise HTTPException(
            status_code=503,
            detail="RabbitMQ producer not initialized"
        )
    
    try:
        # Send event to RabbitMQ
        success = producer.send_event(
            user_id=event.user_id,
            item_id=event.item_id,
            action=event.action,
            process_time=event.process_time
        )
        
        if success:
            return EventResponse(
                success=True,
                message="Event sent to RabbitMQ successfully",
                user_id=event.user_id,
                item_id=event.item_id
            )
        else:
            raise HTTPException(
                status_code=500,
                detail="Failed to send event to RabbitMQ"
            )
    
    except Exception as e:
        logger.error(f"Error sending event to RabbitMQ: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Internal server error: {str(e)}"
        )


@app.post("/update/batch")
async def update_events_batch(events: list[RecommendationEvent]):
    """
    Send multiple recommendation events to RabbitMQ in batch
    
    Args:
        events: List of recommendation events
    
    Returns:
        JSON response with batch processing results
    """
    if producer is None:
        raise HTTPException(
            status_code=503,
            detail="RabbitMQ producer not initialized"
        )
    
    try:
        # Convert Pydantic models to dicts
        event_dicts = [
            {
                'user_id': event.user_id,
                'item_id': event.item_id,
                'action': event.action,
                'process_time': event.process_time
            }
            for event in events
        ]
        
        # Send batch to RabbitMQ
        success_count = producer.send_batch(event_dicts)
        
        return JSONResponse(
            status_code=200,
            content={
                "success": True,
                "message": f"Processed {success_count} out of {len(events)} events",
                "total": len(events),
                "successful": success_count,
                "failed": len(events) - success_count
            }
        )
    
    except Exception as e:
        logger.error(f"Error sending batch events to RabbitMQ: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Internal server error: {str(e)}"
        )


@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {
        "status": "healthy",
        "rabbitmq_connected": producer is not None
    }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)

