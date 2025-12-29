"""
Chatbot API Routes
AI chatbot integration with OpenAI GPT-4
"""

from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel
from typing import Optional
from datetime import datetime, timedelta
import logging

from services.auth_service import get_current_user
from services.chatbot_service import ChatbotService
from firestore_client import db

logger = logging.getLogger(__name__)
router = APIRouter()

chatbot_service = ChatbotService()


class ChatMessage(BaseModel):
    message: str
    sessionId: str


@router.post("/message")
async def send_message(
    chat_message: ChatMessage,
    user: dict = Depends(get_current_user)
):
    """
    Send message to AI chatbot.
    
    Args:
        chat_message: User message and session ID
        user: Authenticated user
    
    Returns:
        {
            "response": str,
            "weatherData": dict (optional),
            "timestamp": str
        }
    """
    try:
        # Save user message
        user_msg_ref = db.collection('chatbot_conversations').document()
        user_msg_ref.set({
            'id': user_msg_ref.id,
            'userId': user['uid'],
            'sessionId': chat_message.sessionId,
            'messageType': 'user',
            'content': chat_message.message,
            'createdAt': datetime.utcnow(),
            'expiresAt': datetime.utcnow() + timedelta(days=30)
        })
        
        # Generate bot response
        bot_response, weather_data = await chatbot_service.generate_response(
            chat_message.message,
            user['uid'],
            chat_message.sessionId
        )
        
        # Save bot message
        bot_msg_ref = db.collection('chatbot_conversations').document()
        bot_msg_ref.set({
            'id': bot_msg_ref.id,
            'userId': user['uid'],
            'sessionId': chat_message.sessionId,
            'messageType': 'bot',
            'content': bot_response,
            'weatherData': weather_data,
            'createdAt': datetime.utcnow(),
            'expiresAt': datetime.utcnow() + timedelta(days=30)
        })
        
        return {
            "response": bot_response,
            "weatherData": weather_data,
            "timestamp": datetime.utcnow().isoformat()
        }
    
    except Exception as e:
        logger.error(f"Error in chatbot: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/history/{session_id}")
async def get_chat_history(
    session_id: str,
    limit: int = 50,
    user: dict = Depends(get_current_user)
):
    """Get chat history for a session"""
    try:
        messages_ref = db.collection('chatbot_conversations') \
            .where('userId', '==', user['uid']) \
            .where('sessionId', '==', session_id) \
            .order_by('createdAt', direction='ASCENDING') \
            .limit(limit)
        
        docs = messages_ref.stream()
        
        messages = []
        for doc in docs:
            data = doc.to_dict()
            if data.get('createdAt'):
                data['createdAt'] = data['createdAt'].isoformat()
            if data.get('expiresAt'):
                data['expiresAt'] = data['expiresAt'].isoformat()
            messages.append(data)
        
        return messages
    
    except Exception as e:
        logger.error(f"Error getting chat history: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/sessions")
async def get_chat_sessions(user: dict = Depends(get_current_user)):
    """Get all chat sessions for user"""
    try:
        # Get unique session IDs
        messages_ref = db.collection('chatbot_conversations') \
            .where('userId', '==', user['uid']) \
            .order_by('createdAt', direction='DESCENDING')
        
        docs = messages_ref.stream()
        
        sessions = {}
        for doc in docs:
            data = doc.to_dict()
            session_id = data.get('sessionId')
            
            if session_id and session_id not in sessions:
                sessions[session_id] = {
                    'sessionId': session_id,
                    'lastMessage': data.get('content'),
                    'lastMessageAt': data.get('createdAt').isoformat() if data.get('createdAt') else None
                }
        
        return list(sessions.values())
    
    except Exception as e:
        logger.error(f"Error getting sessions: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/sessions/{session_id}")
async def delete_session(
    session_id: str,
    user: dict = Depends(get_current_user)
):
    """Delete a chat session"""
    try:
        messages_ref = db.collection('chatbot_conversations') \
            .where('userId', '==', user['uid']) \
            .where('sessionId', '==', session_id)
        
        docs = messages_ref.stream()
        
        deleted = 0
        batch = db.batch()
        
        for doc in docs:
            batch.delete(doc.reference)
            deleted += 1
        
        if deleted > 0:
            batch.commit()
        
        return {"message": f"Deleted {deleted} messages"}
    
    except Exception as e:
        logger.error(f"Error deleting session: {e}")
        raise HTTPException(status_code=500, detail=str(e))
