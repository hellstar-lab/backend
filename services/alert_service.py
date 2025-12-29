"""
Alert Service
Background service for monitoring weather conditions and triggering alerts
"""

import asyncio
from datetime import datetime
import logging
from typing import List, Dict, Any

from firestore_client import db
from services.weather_service import WeatherService
from services.sse_manager import SSEManager

logger = logging.getLogger(__name__)


class AlertService:
    """Service for monitoring weather alerts"""
    
    def __init__(self):
        self.weather_service = WeatherService()
        self.sse_manager = SSEManager()
        self.is_running = False
    
    async def start_monitoring(self):
        """Start the monitoring loop"""
        self.is_running = True
        logger.info("Alert monitoring service started")
        
        while self.is_running:
            try:
                await self.check_alerts()
                # Check every 15 minutes
                await asyncio.sleep(900)
            except Exception as e:
                logger.error(f"Error in alert monitoring loop: {e}")
                await asyncio.sleep(60)  # Retry after 1 minute on error
    
    async def stop_monitoring(self):
        """Stop the monitoring loop"""
        self.is_running = False
        logger.info("Alert monitoring service stopped")
    
    async def check_alerts(self):
        """Check all active alerts against current weather"""
        try:
            # Get all active alerts
            alerts_ref = db.collection('alerts').where('active', '==', True)
            alerts = list(alerts_ref.stream())
            
            logger.info(f"Checking {len(alerts)} active alerts")
            
            for alert_doc in alerts:
                await self._process_alert(alert_doc)
                
        except Exception as e:
            logger.error(f"Error checking alerts: {e}")
    
    async def _process_alert(self, alert_doc):
        """Process a single alert"""
        try:
            alert_data = alert_doc.to_dict()
            alert_id = alert_doc.id
            
            # Get current weather for alert location
            weather = await self.weather_service.get_current_weather(
                alert_data['latitude'],
                alert_data['longitude']
            )
            
            # Check condition
            is_triggered, current_value = self._check_condition(alert_data, weather)
            
            if is_triggered:
                await self._trigger_alert(alert_id, alert_data, current_value)
            
        except Exception as e:
            logger.error(f"Error processing alert {alert_doc.id}: {e}")
    
    def _check_condition(self, alert_data: Dict, weather: Dict) -> tuple[bool, float]:
        """Check if alert condition is met"""
        alert_type = alert_data['type']
        threshold = alert_data['thresholdValue']
        comparison = alert_data['comparison']
        
        # Get current value based on type
        current_value = 0.0
        if alert_type == 'temperature':
            current_value = weather.get('temperature', 0)
        elif alert_type == 'humidity':
            current_value = weather.get('humidity', 0)
        elif alert_type == 'wind_speed':
            current_value = weather.get('windSpeed', 0)
        elif alert_type == 'precipitation':
            current_value = weather.get('precipitation', 0)
        
        # Compare
        is_met = False
        if comparison == 'greater_than':
            is_met = current_value > threshold
        elif comparison == 'less_than':
            is_met = current_value < threshold
        elif comparison == 'equals':
            is_met = current_value == threshold
            
        return is_met, current_value
    
    async def _trigger_alert(self, alert_id: str, alert_data: Dict, current_value: float):
        """Trigger an alert and send notifications"""
        try:
            # Check cooldown (don't trigger if triggered recently)
            last_triggered = alert_data.get('lastTriggered')
            if last_triggered:
                # If triggered in last 24 hours, skip
                # Note: In production, this logic might be more complex
                last_triggered_dt = last_triggered
                if (datetime.utcnow() - last_triggered_dt).total_seconds() < 86400:
                    return

            logger.info(f"Triggering alert {alert_id} for user {alert_data['userId']}")
            
            # Update alert document
            db.collection('alerts').document(alert_id).update({
                'lastTriggered': datetime.utcnow(),
                'triggerCount': firestore.Increment(1)
            })
            
            # Create history entry
            db.collection('alert_history').add({
                'alertId': alert_id,
                'userId': alert_data['userId'],
                'alertName': alert_data['name'],
                'triggeredAt': datetime.utcnow(),
                'currentValue': current_value,
                'thresholdValue': alert_data['thresholdValue'],
                'location': alert_data['location'],
                'notificationSent': True,
                'notificationMethods': alert_data['notificationMethods']
            })
            
            # Send SSE notification
            await self.sse_manager.send_alert_trigger(
                alert_data['userId'],
                alert_id,
                alert_data['name'],
                current_value,
                alert_data['thresholdValue']
            )
            
            # TODO: Send Email/SMS/Push notifications based on notificationMethods
            # This would integrate with SendGrid/Twilio here
            
        except Exception as e:
            logger.error(f"Error triggering alert {alert_id}: {e}")

from firebase_admin import firestore
