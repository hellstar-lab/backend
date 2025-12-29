"""
SSE Manager Service
Manages Server-Sent Events connections and event broadcasting
"""

from typing import Dict, List, Any
import asyncio
from datetime import datetime
import logging

logger = logging.getLogger(__name__)


class SSEManager:
    """Manages SSE connections and event broadcasting"""
    
    def __init__(self):
        # Store active connections: {user_id: [events]}
        self.connections: Dict[str, List[Dict[str, Any]]] = {}
        # Store pending events: {user_id: [events]}
        self.pending_events: Dict[str, List[Dict[str, Any]]] = {}
    
    async def add_connection(self, user_id: str):
        """Register a new SSE connection"""
        if user_id not in self.connections:
            self.connections[user_id] = []
        
        if user_id not in self.pending_events:
            self.pending_events[user_id] = []
        
        logger.info(f"SSE connection added for user {user_id}")
    
    async def remove_connection(self, user_id: str):
        """Remove an SSE connection"""
        if user_id in self.connections:
            del self.connections[user_id]
        
        if user_id in self.pending_events:
            del self.pending_events[user_id]
        
        logger.info(f"SSE connection removed for user {user_id}")
    
    async def send_event(
        self,
        user_id: str,
        event_type: str,
        data: Dict[str, Any]
    ):
        """
        Send event to a specific user.
        
        Args:
            user_id: Target user ID
            event_type: Event type (e.g., 'alert', 'weather_update')
            data: Event data
        """
        if user_id not in self.pending_events:
            self.pending_events[user_id] = []
        
        event = {
            'type': event_type,
            'data': data,
            'timestamp': datetime.utcnow().isoformat()
        }
        
        self.pending_events[user_id].append(event)
        
        logger.info(f"Event queued for user {user_id}: {event_type}")
    
    async def broadcast_event(
        self,
        event_type: str,
        data: Dict[str, Any]
    ):
        """
        Broadcast event to all connected users.
        
        Args:
            event_type: Event type
            data: Event data
        """
        for user_id in list(self.connections.keys()):
            await self.send_event(user_id, event_type, data)
        
        logger.info(f"Event broadcasted to {len(self.connections)} users: {event_type}")
    
    async def get_pending_events(self, user_id: str) -> List[Dict[str, Any]]:
        """
        Get and clear pending events for a user.
        
        Args:
            user_id: User ID
        
        Returns:
            List of pending events
        """
        if user_id not in self.pending_events:
            return []
        
        events = self.pending_events[user_id]
        self.pending_events[user_id] = []
        
        return events
    
    async def get_connection_count(self) -> int:
        """Get number of active connections"""
        return len(self.connections)
    
    async def is_connected(self, user_id: str) -> bool:
        """Check if user is connected"""
        return user_id in self.connections
    
    async def send_weather_update(
        self,
        user_id: str,
        city: str,
        weather_data: Dict[str, Any]
    ):
        """Send weather update event"""
        await self.send_event(
            user_id,
            'weather_update',
            {
                'city': city,
                'weather': weather_data,
                'timestamp': datetime.utcnow().isoformat()
            }
        )
    
    async def send_alert_trigger(
        self,
        user_id: str,
        alert_id: str,
        alert_name: str,
        current_value: float,
        threshold_value: float
    ):
        """Send alert trigger event"""
        await self.send_event(
            user_id,
            'alert_triggered',
            {
                'alertId': alert_id,
                'alertName': alert_name,
                'currentValue': current_value,
                'thresholdValue': threshold_value,
                'timestamp': datetime.utcnow().isoformat()
            }
        )
    
    async def send_notification(
        self,
        user_id: str,
        title: str,
        message: str,
        notification_type: str = 'info'
    ):
        """Send notification event"""
        await self.send_event(
            user_id,
            'notification',
            {
                'title': title,
                'message': message,
                'type': notification_type,
                'timestamp': datetime.utcnow().isoformat()
            }
        )
