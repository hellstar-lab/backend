"""
Alerts API Routes
Weather alert CRUD operations
"""

from fastapi import APIRouter, HTTPException, Depends, Query
from pydantic import BaseModel
from typing import List, Optional
from datetime import datetime, timedelta
import logging

from services.auth_service import get_current_user
from utils.validators import validate_alert_type, validate_comparison, validate_notification_methods
from utils.geocoding import geocode_city
from firestore_client import db

logger = logging.getLogger(__name__)
router = APIRouter()


class AlertCreate(BaseModel):
    name: str
    type: str
    thresholdValue: float
    comparison: str
    location: str
    notificationMethods: List[str]
    severity: str = "warning"


class AlertUpdate(BaseModel):
    name: Optional[str] = None
    thresholdValue: Optional[float] = None
    notificationMethods: Optional[List[str]] = None
    active: Optional[bool] = None


@router.get("")
async def get_alerts(
    active_only: bool = Query(False),
    user: dict = Depends(get_current_user)
):
    """Get user's weather alerts"""
    try:
        query = db.collection('alerts').where('userId', '==', user['uid'])
        
        if active_only:
            query = query.where('active', '==', True)
        
        query = query.order_by('createdAt', direction='DESCENDING')
        docs = query.stream()
        
        alerts = []
        for doc in docs:
            data = doc.to_dict()
            # Convert datetime to ISO string
            if data.get('createdAt'):
                data['createdAt'] = data['createdAt'].isoformat()
            if data.get('lastTriggered'):
                data['lastTriggered'] = data['lastTriggered'].isoformat()
            
            alerts.append(data)
        
        return alerts
    
    except Exception as e:
        logger.error(f"Error getting alerts: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("")
async def create_alert(
    alert: AlertCreate,
    user: dict = Depends(get_current_user)
):
    """Create a new weather alert"""
    try:
        # Validate inputs
        validate_alert_type(alert.type)
        validate_comparison(alert.comparison)
        validate_notification_methods(alert.notificationMethods)
        
        # Check max alerts (20)
        existing_alerts = db.collection('alerts') \
            .where('userId', '==', user['uid']) \
            .where('active', '==', True) \
            .stream()
        
        if len(list(existing_alerts)) >= 20:
            raise HTTPException(
                status_code=403,
                detail="Maximum 20 active alerts allowed"
            )
        
        # Geocode location
        geocode_data = await geocode_city(alert.location, db)
        
        # Create alert
        alert_ref = db.collection('alerts').document()
        alert_data = {
            'id': alert_ref.id,
            'userId': user['uid'],
            'name': alert.name,
            'type': alert.type,
            'thresholdValue': alert.thresholdValue,
            'comparison': alert.comparison,
            'location': geocode_data['city'],
            'latitude': geocode_data['lat'],
            'longitude': geocode_data['lon'],
            'notificationMethods': alert.notificationMethods,
            'severity': alert.severity,
            'active': True,
            'createdAt': datetime.utcnow(),
            'lastTriggered': None,
            'triggerCount': 0
        }
        
        alert_ref.set(alert_data)
        
        logger.info(f"Alert created: {alert_ref.id} by user {user['uid']}")
        
        # Convert datetime for response
        alert_data['createdAt'] = alert_data['createdAt'].isoformat()
        
        return alert_data
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error creating alert: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/{alert_id}")
async def get_alert(
    alert_id: str,
    user: dict = Depends(get_current_user)
):
    """Get a specific alert"""
    try:
        alert_ref = db.collection('alerts').document(alert_id)
        alert_doc = alert_ref.get()
        
        if not alert_doc.exists:
            raise HTTPException(status_code=404, detail="Alert not found")
        
        alert_data = alert_doc.to_dict()
        
        # Verify ownership
        if alert_data.get('userId') != user['uid']:
            raise HTTPException(status_code=403, detail="Not authorized")
        
        # Convert datetime
        if alert_data.get('createdAt'):
            alert_data['createdAt'] = alert_data['createdAt'].isoformat()
        if alert_data.get('lastTriggered'):
            alert_data['lastTriggered'] = alert_data['lastTriggered'].isoformat()
        
        return alert_data
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting alert: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.put("/{alert_id}")
async def update_alert(
    alert_id: str,
    alert_update: AlertUpdate,
    user: dict = Depends(get_current_user)
):
    """Update an alert"""
    try:
        alert_ref = db.collection('alerts').document(alert_id)
        alert_doc = alert_ref.get()
        
        if not alert_doc.exists:
            raise HTTPException(status_code=404, detail="Alert not found")
        
        alert_data = alert_doc.to_dict()
        
        # Verify ownership
        if alert_data.get('userId') != user['uid']:
            raise HTTPException(status_code=403, detail="Not authorized")
        
        # Build update dict
        update_data = {}
        if alert_update.name is not None:
            update_data['name'] = alert_update.name
        if alert_update.thresholdValue is not None:
            update_data['thresholdValue'] = alert_update.thresholdValue
        if alert_update.notificationMethods is not None:
            validate_notification_methods(alert_update.notificationMethods)
            update_data['notificationMethods'] = alert_update.notificationMethods
        if alert_update.active is not None:
            update_data['active'] = alert_update.active
        
        if update_data:
            alert_ref.update(update_data)
        
        return {"message": "Alert updated successfully"}
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error updating alert: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/{alert_id}")
async def delete_alert(
    alert_id: str,
    user: dict = Depends(get_current_user)
):
    """Delete an alert"""
    try:
        alert_ref = db.collection('alerts').document(alert_id)
        alert_doc = alert_ref.get()
        
        if not alert_doc.exists:
            raise HTTPException(status_code=404, detail="Alert not found")
        
        alert_data = alert_doc.to_dict()
        
        # Verify ownership
        if alert_data.get('userId') != user['uid']:
            raise HTTPException(status_code=403, detail="Not authorized")
        
        alert_ref.delete()
        
        return {"message": "Alert deleted successfully"}
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error deleting alert: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/history/triggered")
async def get_alert_history(
    limit: int = Query(50, ge=1, le=100),
    user: dict = Depends(get_current_user)
):
    """Get alert trigger history"""
    try:
        history_ref = db.collection('alert_history') \
            .where('userId', '==', user['uid']) \
            .order_by('triggeredAt', direction='DESCENDING') \
            .limit(limit)
        
        docs = history_ref.stream()
        
        history = []
        for doc in docs:
            data = doc.to_dict()
            if data.get('triggeredAt'):
                data['triggeredAt'] = data['triggeredAt'].isoformat()
            history.append(data)
        
        return history
    
    except Exception as e:
        logger.error(f"Error getting alert history: {e}")
        raise HTTPException(status_code=500, detail=str(e))
