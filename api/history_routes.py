"""
History API Routes
Query history endpoints
"""

from fastapi import APIRouter, HTTPException, Depends, Query
from typing import List, Dict
from datetime import datetime
import logging

from services.auth_service import get_current_user
from firestore_client import db

logger = logging.getLogger(__name__)
router = APIRouter()


@router.get("/queries")
async def get_query_history(
    limit: int = Query(50, ge=1, le=100),
    offset: int = Query(0, ge=0),
    user: dict = Depends(get_current_user)
):
    """
    Get user's query history (last 7 days).
    
    Args:
        limit: Max results (1-100, default 50)
        offset: Pagination offset
        user: Authenticated user
    
    Returns:
        {
            "total": int,
            "queries": [QueryHistoryItem],
            "limit": int,
            "offset": int
        }
    """
    try:
        logger.info(f"Query history request by user {user['uid']}")
        
        # Query Firestore
        query_ref = db.collection('query_history') \
            .where('userId', '==', user['uid']) \
            .order_by('queriedAt', direction='DESCENDING') \
            .limit(limit) \
            .offset(offset)
        
        docs = query_ref.stream()
        
        # Transform to response format
        queries = []
        for doc in docs:
            data = doc.to_dict()
            weather_data = data.get('weatherData', {})
            
            queries.append({
                "id": data.get('id'),
                "city": data.get('city'),
                "country": data.get('country'),
                "queriedAt": data.get('queriedAt').isoformat() if data.get('queriedAt') else None,
                "condition": weather_data.get('condition'),
                "temperature": weather_data.get('temperature'),
                "humidity": weather_data.get('humidity'),
                "windSpeed": weather_data.get('windSpeed')
            })
        
        # Get total count
        total_query = db.collection('query_history').where('userId', '==', user['uid'])
        total_count = len(list(total_query.stream()))
        
        return {
            "total": total_count,
            "queries": queries,
            "limit": limit,
            "offset": offset
        }
    
    except Exception as e:
        logger.error(f"Error in get_query_history: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/queries/{query_id}")
async def delete_query(
    query_id: str,
    user: dict = Depends(get_current_user)
):
    """Delete a specific query from history"""
    try:
        query_ref = db.collection('query_history').document(query_id)
        query_doc = query_ref.get()
        
        if not query_doc.exists:
            raise HTTPException(status_code=404, detail="Query not found")
        
        # Verify ownership
        if query_doc.to_dict().get('userId') != user['uid']:
            raise HTTPException(status_code=403, detail="Not authorized")
        
        query_ref.delete()
        
        return {"message": "Query deleted successfully"}
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error deleting query: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/queries")
async def clear_query_history(user: dict = Depends(get_current_user)):
    """Clear all query history for user"""
    try:
        query_ref = db.collection('query_history').where('userId', '==', user['uid'])
        docs = query_ref.stream()
        
        deleted = 0
        batch = db.batch()
        
        for doc in docs:
            batch.delete(doc.reference)
            deleted += 1
        
        if deleted > 0:
            batch.commit()
        
        return {"message": f"Deleted {deleted} queries"}
    
    except Exception as e:
        logger.error(f"Error clearing history: {e}")
        raise HTTPException(status_code=500, detail=str(e))
