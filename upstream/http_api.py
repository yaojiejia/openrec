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

# Import metrics
from monitoring.metrics import (
    start_metrics_server,
    start_system_metrics_collection,
    http_requests_total,
    http_request_duration,
    events_sent_total,
    events_sent_batch_size
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
    """Initialize RabbitMQ producer and metrics on startup"""
    global producer
    
    # Start Prometheus metrics server
    start_metrics_server(port=8001)
    start_system_metrics_collection(interval=5.0)
    logger.info("Prometheus metrics enabled on port 8001")
    
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
        event: Recommendation event containing user_id, item_id, action, and optional process_time
    
    Returns:
        EventResponse: Success status and event details
    """
    import time as time_module
    start_time = time_module.time()
    
    try:
        if producer is None:
            http_requests_total.labels(method='POST', endpoint='/update', status='503').inc()
            raise HTTPException(
                status_code=503,
                detail="RabbitMQ producer not initialized"
            )
        
        # Send event to RabbitMQ
        success = producer.send_event(
            user_id=event.user_id,
            item_id=event.item_id,
            action=event.action,
            process_time=event.process_time
        )
        
        if success:
            # Track metrics
            events_sent_total.labels(action=event.action).inc()
            http_requests_total.labels(method='POST', endpoint='/update', status='200').inc()
            
            return EventResponse(
                success=True,
                message="Event sent to RabbitMQ successfully",
                user_id=event.user_id,
                item_id=event.item_id
            )
        else:
            http_requests_total.labels(method='POST', endpoint='/update', status='500').inc()
            raise HTTPException(
                status_code=500,
                detail="Failed to send event to RabbitMQ"
            )
    
    except HTTPException:
        raise
    except Exception as e:
        http_requests_total.labels(method='POST', endpoint='/update', status='500').inc()
        logger.error(f"Error sending event to RabbitMQ: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Internal server error: {str(e)}"
        )
    finally:
        duration = time_module.time() - start_time
        http_request_duration.labels(method='POST', endpoint='/update').observe(duration)


@app.post("/update/batch")
async def update_events_batch(events: list[RecommendationEvent]):
    """
    Send multiple recommendation events to RabbitMQ in batch
    
    Args:
        events: List of recommendation events
    
    Returns:
        JSON response with batch processing results
    """
    import time as time_module
    start_time = time_module.time()
    
    try:
        if producer is None:
            http_requests_total.labels(method='POST', endpoint='/update/batch', status='503').inc()
            raise HTTPException(
                status_code=503,
                detail="RabbitMQ producer not initialized"
            )
        
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
        
        # Track metrics
        events_sent_batch_size.observe(len(events))
        for event in events:
            events_sent_total.labels(action=event.action).inc()
        http_requests_total.labels(method='POST', endpoint='/update/batch', status='200').inc()
        
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
    
    except HTTPException:
        raise
    except Exception as e:
        http_requests_total.labels(method='POST', endpoint='/update/batch', status='500').inc()
        logger.error(f"Error sending batch events to RabbitMQ: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Internal server error: {str(e)}"
        )
    finally:
        duration = time_module.time() - start_time
        http_request_duration.labels(method='POST', endpoint='/update/batch').observe(duration)


@app.get("/health")
async def health_check():
    """Health check endpoint"""
    http_requests_total.labels(method='GET', endpoint='/health', status='200').inc()
    return {
        "status": "healthy",
        "rabbitmq_connected": producer is not None
    }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)

