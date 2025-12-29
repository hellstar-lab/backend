"""
User API Routes
User profile and settings management
"""

from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel, EmailStr
from typing import Optional
from datetime import datetime
import logging

from services.auth_service import get_current_user
from firestore_client import db

logger = logging.getLogger(__name__)
router = APIRouter()


class UserSettings(BaseModel):
    defaultLocation: Optional[str] = None
    temperatureUnits: Optional[str] = None
    emailNotifications: Optional[bool] = None
    pushNotifications: Optional[bool] = None
    smsNotifications: Optional[bool] = None
    weeklyReports: Optional[bool] = None
    theme: Optional[str] = None
    timeFormat24h: Optional[bool] = None
    autoRefresh: Optional[bool] = None


@router.get("/profile")
async def get_user_profile(user: dict = Depends(get_current_user)):
    """Get user profile"""
    try:
        user_ref = db.collection('users').document(user['uid'])
        user_doc = user_ref.get()
        
        if not user_doc.exists:
            # Create user document if doesn't exist
            user_data = {
                'userId': user['uid'],
                'email': user['email'],
                'name': user.get('name', ''),
                'emailVerified': user.get('email_verified', False),
                'photoURL': user.get('picture'),
                'createdAt': datetime.utcnow(),
                'lastLoginAt': datetime.utcnow(),
                'queryCount': 0,
                'settings': {
                    'defaultLocation': 'New York',
                    'temperatureUnits': 'metric',
                    'emailNotifications': True,
                    'pushNotifications': False,
                    'smsNotifications': False,
                    'weeklyReports': True,
                    'theme': 'dark',
                    'timeFormat24h': False,
                    'autoRefresh': True
                },
                'subscription': {
                    'plan': 'free',
                    'startDate': datetime.utcnow(),
                    'endDate': None,
                    'status': 'active'
                }
            }
            user_ref.set(user_data)
            
            # Convert datetime for response
            user_data['createdAt'] = user_data['createdAt'].isoformat()
            user_data['lastLoginAt'] = user_data['lastLoginAt'].isoformat()
            user_data['subscription']['startDate'] = user_data['subscription']['startDate'].isoformat()
            
            return user_data
        
        user_data = user_doc.to_dict()
        
        # Update last login
        user_ref.update({'lastLoginAt': datetime.utcnow()})
        
        # Convert datetime for response
        if user_data.get('createdAt'):
            user_data['createdAt'] = user_data['createdAt'].isoformat()
        if user_data.get('lastLoginAt'):
            user_data['lastLoginAt'] = user_data['lastLoginAt'].isoformat()
        if user_data.get('subscription', {}).get('startDate'):
            user_data['subscription']['startDate'] = user_data['subscription']['startDate'].isoformat()
        if user_data.get('subscription', {}).get('endDate'):
            user_data['subscription']['endDate'] = user_data['subscription']['endDate'].isoformat()
        
        return user_data
    
    except Exception as e:
        logger.error(f"Error getting user profile: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.put("/settings")
async def update_user_settings(
    settings: UserSettings,
    user: dict = Depends(get_current_user)
):
    """Update user settings"""
    try:
        user_ref = db.collection('users').document(user['uid'])
        
        # Build update dict
        update_data = {}
        if settings.defaultLocation is not None:
            update_data['settings.defaultLocation'] = settings.defaultLocation
        if settings.temperatureUnits is not None:
            if settings.temperatureUnits not in ['metric', 'imperial']:
                raise HTTPException(status_code=400, detail="Invalid temperature units")
            update_data['settings.temperatureUnits'] = settings.temperatureUnits
        if settings.emailNotifications is not None:
            update_data['settings.emailNotifications'] = settings.emailNotifications
        if settings.pushNotifications is not None:
            update_data['settings.pushNotifications'] = settings.pushNotifications
        if settings.smsNotifications is not None:
            update_data['settings.smsNotifications'] = settings.smsNotifications
        if settings.weeklyReports is not None:
            update_data['settings.weeklyReports'] = settings.weeklyReports
        if settings.theme is not None:
            if settings.theme not in ['light', 'dark']:
                raise HTTPException(status_code=400, detail="Invalid theme")
            update_data['settings.theme'] = settings.theme
        if settings.timeFormat24h is not None:
            update_data['settings.timeFormat24h'] = settings.timeFormat24h
        if settings.autoRefresh is not None:
            update_data['settings.autoRefresh'] = settings.autoRefresh
        
        if update_data:
            user_ref.update(update_data)
        
        return {"message": "Settings updated successfully"}
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error updating settings: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/stats")
async def get_user_stats(user: dict = Depends(get_current_user)):
    """Get user statistics"""
    try:
        user_ref = db.collection('users').document(user['uid'])
        user_doc = user_ref.get()
        
        if not user_doc.exists:
            return {
                "queryCount": 0,
                "alertCount": 0,
                "favoriteCount": 0
            }
        
        user_data = user_doc.to_dict()
        
        # Count alerts
        alerts_count = len(list(
            db.collection('alerts')
            .where('userId', '==', user['uid'])
            .where('active', '==', True)
            .stream()
        ))
        
        # Count favorites
        favorites_count = len(list(
            db.collection('users')
            .document(user['uid'])
            .collection('favorite_cities')
            .stream()
        ))
        
        return {
            "queryCount": user_data.get('queryCount', 0),
            "alertCount": alerts_count,
            "favoriteCount": favorites_count
        }
    
    except Exception as e:
        logger.error(f"Error getting user stats: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/account")
async def delete_user_account(user: dict = Depends(get_current_user)):
    """Delete user account and all associated data"""
    try:
        user_id = user['uid']
        
        # Delete user document
        db.collection('users').document(user_id).delete()
        
        # Delete query history
        queries = db.collection('query_history').where('userId', '==', user_id).stream()
        for query in queries:
            query.reference.delete()
        
        # Delete alerts
        alerts = db.collection('alerts').where('userId', '==', user_id).stream()
        for alert in alerts:
            alert.reference.delete()
        
        # Delete alert history
        alert_history = db.collection('alert_history').where('userId', '==', user_id).stream()
        for history in alert_history:
            history.reference.delete()
        
        # Delete chatbot conversations
        conversations = db.collection('chatbot_conversations').where('userId', '==', user_id).stream()
        for conversation in conversations:
            conversation.reference.delete()
        
        # Delete favorites
        favorites = db.collection('users').document(user_id).collection('favorite_cities').stream()
        for favorite in favorites:
            favorite.reference.delete()
        
        logger.info(f"User account deleted: {user_id}")
        
        return {"message": "Account deleted successfully"}
    
    except Exception as e:
        logger.error(f"Error deleting account: {e}")
        raise HTTPException(status_code=500, detail=str(e))
