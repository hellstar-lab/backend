"""
Authentication Service
Firebase Auth integration and token verification
"""

from fastapi import Header, HTTPException, status
from firebase_admin import auth
from typing import Optional, Dict
import logging
import requests
import os

logger = logging.getLogger(__name__)


async def verify_google_token(token: str) -> Dict:
    """
    Verify Google OAuth access token and return user data.
    """
    try:
        # Verify access token by fetching user info
        response = requests.get(
            f"https://www.googleapis.com/oauth2/v3/userinfo?access_token={token}"
        )
        
        if response.status_code != 200:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid Google token"
            )
            
        user_info = response.json()
        
        # Check if audience matches our client ID (optional for access_token but good practice if available in headers)
        # For access_token, the primary check is that it works to get user info.
        
        return {
            "uid": user_info['sub'],
            "email": user_info['email'],
            "email_verified": user_info.get('email_verified', False),
            "name": user_info.get('name'),
            "picture": user_info.get('picture')
        }
        
    except Exception as e:
        logger.error(f"Google auth error: {e}")
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Authentication failed")

async def get_current_user(authorization: Optional[str] = Header(None)) -> Dict:
    """
    Verify Firebase Auth token and return user data.
    """
    if not authorization:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authorization header missing",
            headers={"WWW-Authenticate": "Bearer"}
        )
    
    return await _verify_token(authorization)


async def get_optional_user(authorization: Optional[str] = Header(None)) -> Optional[Dict]:
    """
    Verify token if present, otherwise return None.
    Allows public access to endpoints while capturing user context if available.
    """
    if not authorization:
        return None
    
    try:
        return await _verify_token(authorization)
    except HTTPException:
        # If token is invalid but present, treat as anonymous for optional endpoints
        # OR raise error. Usually better to ignore for optional.
        return None


async def _verify_token(authorization: str) -> Dict:
    """Helper to verify token string"""
    try:
        if not authorization.startswith("Bearer "):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid authorization header format"
            )
        
        token = authorization.split("Bearer ")[-1]
        
        # Verify token with Firebase
        # In dev mode with mock creds, we might need to mock this too if real verification fails
        try:
            decoded_token = auth.verify_id_token(token)
        except Exception:
            # If using mock firestore/creds, auth.verify_id_token might fail.
            # For local dev without real creds, we can't verify real tokens.
            # We should check if we are in a mock environment.
            from config import settings
            if settings.ENVIRONMENT == "development" and settings.FIREBASE_PRIVATE_KEY_ID == "demo-key-id":
                # Mock successful auth for dev
                return {
                    "uid": "mock_user_123",
                    "email": "demo@example.com",
                    "email_verified": True,
                    "name": "Demo User"
                }
            raise

        return {
            "uid": decoded_token['uid'],
            "email": decoded_token.get('email'),
            "email_verified": decoded_token.get('email_verified', False),
            "name": decoded_token.get('name'),
            "picture": decoded_token.get('picture')
        }
    
    except auth.InvalidIdTokenError:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token")
    except auth.ExpiredIdTokenError:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Token expired")
    except Exception as e:
        logger.error(f"Auth error: {e}")
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Authentication failed")


async def verify_email_verified(user: Dict) -> Dict:
    """
    Verify that user's email is verified.
    
    Args:
        user: User data from get_current_user
    
    Returns:
        User data if email is verified
    
    Raises:
        HTTPException: If email is not verified
    """
    if not user.get('email_verified'):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Email not verified"
        )
    
    return user


async def create_custom_token(uid: str) -> str:
    """
    Create a custom Firebase Auth token.
    
    Args:
        uid: User ID
    
    Returns:
        Custom token string
    """
    try:
        custom_token = auth.create_custom_token(uid)
        return custom_token.decode('utf-8')
    
    except Exception as e:
        logger.error(f"Error creating custom token: {e}")
        raise HTTPException(
            status_code=500,
            detail="Failed to create authentication token"
        )


async def verify_github_token(code: str) -> Dict:
    """
    Verify GitHub OAuth code and return user data.
    
    Args:
        code: GitHub authorization code
        
    Returns:
        Dict containing user information (email, name, avatar_url)
        
    Raises:
        HTTPException: If token verification fails
    """
    try:
        # Exchange code for access token
        token_url = "https://github.com/login/oauth/access_token"
        token_data = {
            "client_id": os.getenv("GITHUB_CLIENT_ID"),
            "client_secret": os.getenv("GITHUB_CLIENT_SECRET"),
            "code": code
        }
        token_headers = {"Accept": "application/json"}
        
        token_response = requests.post(token_url, data=token_data, headers=token_headers)
        token_response.raise_for_status()
        token_json = token_response.json()
        
        if "error" in token_json:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail=f"GitHub OAuth error: {token_json.get('error_description', 'Unknown error')}"
            )
        
        access_token = token_json.get("access_token")
        if not access_token:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="No access token received from GitHub"
            )
        
        # Get user info
        user_url = "https://api.github.com/user"
        user_headers = {
            "Authorization": f"Bearer {access_token}",
            "Accept": "application/json"
        }
        
        user_response = requests.get(user_url, headers=user_headers)
        user_response.raise_for_status()
        user_data = user_response.json()
        
        # Get user email if not public
        email = user_data.get("email")
        if not email:
            email_url = "https://api.github.com/user/emails"
            email_response = requests.get(email_url, headers=user_headers)
            email_response.raise_for_status()
            emails = email_response.json()
            
            # Get primary email
            for email_obj in emails:
                if email_obj.get("primary"):
                    email = email_obj.get("email")
                    break
            
            # Fallback to first email
            if not email and emails:
                email = emails[0].get("email")
        
        if not email:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Could not retrieve email from GitHub account"
            )
        
        return {
            "email": email,
            "name": user_data.get("name") or user_data.get("login"),
            "avatar_url": user_data.get("avatar_url"),
            "github_id": str(user_data.get("id"))
        }
        
    except requests.RequestException as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=f"GitHub API error: {str(e)}"
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid GitHub token",
            headers={"WWW-Authenticate": "Bearer"}
        )
