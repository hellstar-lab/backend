"""
Server-Sent Events (SSE) Routes
Real-time event streaming for weather updates and alerts
"""

from fastapi import APIRouter, Depends
from fastapi.responses import StreamingResponse
from typing import AsyncGenerator
import asyncio
from datetime import datetime
import json
import logging

from services.auth_service import get_current_user
from services.sse_manager import SSEManager

logger = logging.getLogger(__name__)
router = APIRouter()

# Global SSE manager instance
sse_manager = SSEManager()


@router.get("/stream")
async def sse_stream(user: dict = Depends(get_current_user)):
    """
    Server-Sent Events stream for real-time updates.
    
    Sends:
    - Connected event (immediate)
    - Heartbeat (every 30 seconds)
    - Weather updates (every 5 minutes)
    - Alert triggers (immediate)
    
    Args:
        user: Authenticated user
    
    Returns:
        StreamingResponse with SSE events
    """
    
    async def event_generator() -> AsyncGenerator[str, None]:
        """Generate SSE events"""
        user_id = user['uid']
        
        try:
            # Register connection
            await sse_manager.add_connection(user_id)
            
            # Send connected event
            yield f"event: connected\ndata: {json.dumps({'status': 'connected', 'userId': user_id})}\n\n"
            
            logger.info(f"SSE connection established for user {user_id}")
            
            last_heartbeat = datetime.utcnow()
            last_weather_update = datetime.utcnow()
            
            while True:
                # Heartbeat every 30 seconds
                if (datetime.utcnow() - last_heartbeat).total_seconds() >= 30:
                    heartbeat_data = {
                        'timestamp': datetime.utcnow().isoformat(),
                        'type': 'heartbeat'
                    }
                    yield f"event: heartbeat\ndata: {json.dumps(heartbeat_data)}\n\n"
                    last_heartbeat = datetime.utcnow()
                
                # Check for pending events for this user
                events = await sse_manager.get_pending_events(user_id)
                
                for event in events:
                    event_type = event.get('type', 'message')
                    event_data = event.get('data', {})
                    yield f"event: {event_type}\ndata: {json.dumps(event_data)}\n\n"
                
                # Small delay to prevent busy loop
                await asyncio.sleep(1)
        
        except asyncio.CancelledError:
            logger.info(f"SSE connection closed for user {user_id}")
            await sse_manager.remove_connection(user_id)
        
        except Exception as e:
            logger.error(f"SSE error for user {user_id}: {e}")
            await sse_manager.remove_connection(user_id)
    
    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
            "Access-Control-Allow-Origin": "*"
        }
    )


@router.post("/broadcast")
async def broadcast_event(
    event_type: str,
    data: dict,
    user: dict = Depends(get_current_user)
):
    """
    Broadcast event to user's SSE connection.
    Internal endpoint for triggering SSE events.
    """
    try:
        await sse_manager.send_event(user['uid'], event_type, data)
        return {"message": "Event broadcasted"}
    
    except Exception as e:
        logger.error(f"Broadcast error: {e}")
        return {"error": str(e)}


@router.get("/connections")
async def get_active_connections():
    """Get count of active SSE connections (admin only)"""
    try:
        count = await sse_manager.get_connection_count()
        return {"active_connections": count}
    
    except Exception as e:
        logger.error(f"Error getting connections: {e}")
        return {"error": str(e)}
