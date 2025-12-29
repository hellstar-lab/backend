"""
Authentication API Routes
Login, signup, and token management
"""

from fastapi import APIRouter, HTTPException, Depends, Request, Body
from pydantic import BaseModel, EmailStr, ConfigDict
from typing import Optional
from datetime import datetime
import logging
from passlib.context import CryptContext
from fastapi_limiter.depends import RateLimiter

from services.auth_service import get_current_user, verify_email_verified, verify_google_token, verify_github_token, create_custom_token
from services.otp_service import verify_otp
from firestore_client import db

logger = logging.getLogger(__name__)
router = APIRouter()

# Password Hashing Context (Argon2id)
pwd_context = CryptContext(schemes=["argon2"], deprecated="auto")

class SignupRequest(BaseModel):
    model_config = ConfigDict(extra='forbid')
    email: EmailStr
    password: str
    name: str

class LoginRequest(BaseModel):
    model_config = ConfigDict(extra='forbid')
    email: EmailStr
    password: str

class GoogleLoginRequest(BaseModel):
    model_config = ConfigDict(extra='forbid')
    token: str

class PasswordResetRequest(BaseModel):
    model_config = ConfigDict(extra='forbid')
    email: EmailStr

class PasswordResetConfirm(BaseModel):
    model_config = ConfigDict(extra='forbid')
    email: EmailStr
    code: str
    new_password: str

@router.post("/signup", dependencies=[Depends(RateLimiter(times=5, seconds=60))])
async def signup(request: SignupRequest):
    """
    User signup endpoint.
    Creates user in Firestore and returns Firebase custom token.
    """
    try:
        email = request.email.lower()
        password = request.password
        name = request.name.strip()
        
        if not name:
            raise HTTPException(status_code=400, detail="Name is required")
            
        # Check if user already exists
        user_ref = db.collection('users').document(email)
        user_doc = user_ref.get()
        
        if user_doc.exists:
            # Check if user was created with a different provider
            # functionality to link accounts could be added here
            raise HTTPException(status_code=400, detail="User already exists")
            
        # Hash password
        password_hash = pwd_context.hash(password)
        
        # Create user
        user_data = {
            'uid': email.replace('@', '_').replace('.', '_'),
            'email': email,
            'name': name,
            'password_hash': password_hash,
            'email_verified': False, # Require email verification
            'created_at': datetime.utcnow(),
            'last_login': datetime.utcnow(),
            'auth_provider': 'email'
        }
        
        user_ref.set(user_data)
        
        # Send OTP for verification automatically
        from services.otp_service import send_otp
        await send_otp(email)
        
        return {
            "message": "User created. Please verify your email.",
            "email": email,
            "requires_verification": True
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Signup error: {e}")
        raise HTTPException(status_code=500, detail="Signup failed")

@router.post("/login", dependencies=[Depends(RateLimiter(times=5, seconds=60))])
async def login(request: LoginRequest):
    """
    User login endpoint.
    Verifies credentials and returns Firebase custom token.
    """
    try:
        email = request.email.lower()
        password = request.password
        
        # Get user
        user_ref = db.collection('users').document(email)
        user_doc = user_ref.get()
        
        if not user_doc.exists:
            raise HTTPException(status_code=401, detail="Invalid credentials")
            
        user_data = user_doc.to_dict()
        
        # Verify password
        # Check if user has a password set (social login users might not)
        if 'password_hash' not in user_data:
            raise HTTPException(status_code=400, detail="Please login with your social provider")
            
        if not pwd_context.verify(password, user_data['password_hash']):
            raise HTTPException(status_code=401, detail="Invalid credentials")
            
        # Check email verification
        if not user_data.get('email_verified'):
             # Send OTP for verification
            from services.otp_service import send_otp
            await send_otp(email)
            
            return {
                "message": "Email not verified. OTP sent.",
                "email": email,
                "requires_verification": True
            }
        
        # Update last login
        user_ref.update({'last_login': datetime.utcnow()})
        
        # Create custom token
        uid = user_data.get('uid')
        custom_token = await create_custom_token(uid)
        
        return {
            "uid": uid,
            "email": email,
            "name": user_data.get('name'),
            "photoURL": user_data.get('photoURL'),
            "email_verified": True,
            "firebase_token": custom_token
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Login error: {e}")
        raise HTTPException(status_code=500, detail="Login failed")

@router.post("/google", dependencies=[Depends(RateLimiter(times=10, seconds=60))])
async def google_login(request: GoogleLoginRequest):
    """
    Google OAuth login endpoint.
    Verifies Google token and creates/updates user in Firestore.
    """
    try:
        user_info = await verify_google_token(request.token)
        email = user_info['email'].lower()
        
        # Check if user exists
        user_ref = db.collection('users').document(email)
        user_doc = user_ref.get()
        
        user_data = {
            'email': email,
            'name': user_info['name'],
            'photoURL': user_info['picture'],
            'email_verified': True, # Google emails are verified
            'last_login': datetime.utcnow(),
            'auth_provider': 'google'
        }
        
        if not user_doc.exists:
            # Create new user
            user_data['uid'] = user_info['uid']
            user_data['created_at'] = datetime.utcnow()
            user_ref.set(user_data)
        else:
            # Update existing user
            user_ref.update(user_data)
            user_data['uid'] = user_doc.to_dict().get('uid', user_info['uid'])
            
        # Create custom token
        custom_token = await create_custom_token(user_data['uid'])
        
        return {
            "uid": user_data['uid'],
            "email": email,
            "name": user_data['name'],
            "photoURL": user_data['photoURL'],
            "email_verified": True,
            "firebase_token": custom_token
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Google login error: {e}")
        raise HTTPException(status_code=500, detail="Google login failed")


@router.post("/github", dependencies=[Depends(RateLimiter(times=10, seconds=60))])
async def github_login(request: Request):
    """
    GitHub OAuth login endpoint.
    Verifies GitHub code and creates/updates user in Firestore.
    """
    try:
        body = await request.json()
        code = body.get("code")
        
        if not code:
            raise HTTPException(status_code=400, detail="GitHub code is required")
        
        user_info = await verify_github_token(code)
        email = user_info['email'].lower()
        
        # Check if user exists
        user_ref = db.collection('users').document(email)
        user_doc = user_ref.get()
        
        user_data = {
            'email': email,
            'name': user_info['name'],
            'photoURL': user_info.get('avatar_url'),
            'email_verified': True,  # GitHub emails are verified
            'last_login': datetime.utcnow(),
            'auth_provider': 'github'
        }
        
        if not user_doc.exists:
            # Create new user
            user_data['uid'] = email.replace('@', '_').replace('.', '_')
            user_data['created_at'] = datetime.utcnow()
            user_ref.set(user_data)
        else:
            # Update existing user
            user_ref.update(user_data)
            user_data['uid'] = user_doc.to_dict().get('uid', email.replace('@', '_').replace('.', '_'))
            
        # Create custom token
        custom_token = await create_custom_token(user_data['uid'])
        
        return {
            "uid": user_data['uid'],
            "email": email,
            "name": user_data['name'],
            "photoURL": user_data.get('photoURL'),
            "email_verified": True,
            "firebase_token": custom_token
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"GitHub login error: {e}")
        raise HTTPException(status_code=500, detail="GitHub login failed")


@router.post("/send-otp", dependencies=[Depends(RateLimiter(times=5, seconds=60))])
async def send_otp_endpoint(request: Request):
    """
    Send OTP to user's email for verification.
    """
    try:
        body = await request.json()
        email = body.get("email", "").lower()
        
        if not email:
            raise HTTPException(status_code=400, detail="Email is required")
            
        # Import OTP service
        from services.otp_service import send_otp
        
        # Send OTP
        await send_otp(email)
        
        return {"message": "OTP sent successfully", "email": email}
        
    except Exception as e:
        logger.error(f"Send OTP error: {e}")
        raise HTTPException(status_code=500, detail="Failed to send OTP")


@router.post("/verify-otp", dependencies=[Depends(RateLimiter(times=5, seconds=60))])
async def verify_otp_endpoint(request: Request):
    """
    Verify OTP and create user session.
    """
    try:
        body = await request.json()
        email = body.get("email", "").lower()
        otp = body.get("otp")
        name = body.get("name")
        
        logger.info(f"OTP verification request - Email: {email}, OTP: {otp}, Name: {name}")
        
        if not email or not otp:
            logger.error("Missing email or OTP")
            raise HTTPException(status_code=400, detail="Email and OTP are required")
        
        # Verify OTP (Async)
        is_valid = await verify_otp(email, otp)
        
        if not is_valid:
            logger.error(f"OTP validation failed for {email}")
            raise HTTPException(status_code=401, detail="Invalid or expired OTP")
        
        logger.info(f"OTP validated successfully for {email}")
        
        # Create or update user in Firestore
        user_ref = db.collection('users').document(email)
        user_doc = user_ref.get()
        
        logger.info(f"User exists: {user_doc.exists}")
        
        if user_doc.exists:
            # Existing user (login)
            logger.info(f"Logging in existing user: {email}")
            user_data = user_doc.to_dict()
            user_ref.update({
                'last_login': datetime.utcnow(),
                'email_verified': True
            })
        else:
            # New user (signup) - name is required
            logger.info(f"Creating new user: {email}, Name provided: '{name}'")
            if not name or name.strip() == '':
                logger.error(f"Name required for new user signup but got: '{name}'")
                raise HTTPException(status_code=400, detail="Name is required for new user signup")
            
            user_data = {
                'uid': email.replace('@', '_').replace('.', '_'),
                'email': email,
                'name': name.strip(),
                'email_verified': True,
                'created_at': datetime.utcnow(),
                'last_login': datetime.utcnow(),
                'auth_provider': 'email'
            }
            user_ref.set(user_data)
            logger.info(f"New user created successfully: {email}")
        
        # Create custom Firebase token
        uid = user_data.get('uid', email.replace('@', '_').replace('.', '_'))
        logger.info(f"Creating Firebase token for UID: {uid}")
        custom_token = await create_custom_token(uid)
        
        logger.info(f"OTP verification complete for {email}")
        return {
            "uid": uid,
            "email": email,
            "name": user_data.get('name', name),
            "email_verified": True,
            "firebase_token": custom_token
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Verify OTP error: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"OTP verification failed: {str(e)}")


@router.post("/request-password-reset", dependencies=[Depends(RateLimiter(times=3, seconds=3600))])
async def request_password_reset(request: PasswordResetRequest = Body(...)):
    """
    Send password reset code to user's email.
    """
    try:
        email = request.email.lower()
        
        # Check if user exists
        user_ref = db.collection('users').document(email)
        user_doc = user_ref.get()
        
        if not user_doc.exists:
            # Don't reveal if user exists or not for security
            logger.warning(f"Password reset requested for non-existent user: {email}")
            return {"message": "If the email exists, a reset code has been sent"}
        
        # Import password reset service
        from services.otp_service import send_password_reset
        
        # Send reset code (Async)
        success = await send_password_reset(email)
        
        if not success:
            raise HTTPException(status_code=500, detail="Failed to send reset code")
        
        return {
            "message": "Password reset code sent successfully",
            "email": email
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Request password reset error: {e}")
        raise HTTPException(status_code=500, detail="Failed to send reset code")


@router.post("/reset-password", dependencies=[Depends(RateLimiter(times=3, seconds=3600))])
async def reset_password_endpoint(request: PasswordResetConfirm = Body(...)):
    """
    Verify reset code and update password.
    """
    try:
        email = request.email.lower()
        code = request.code
        new_password = request.new_password
        
        # Verify reset code (Async)
        is_valid = await verify_otp(email, code)
        
        if not is_valid:
            raise HTTPException(status_code=401, detail="Invalid or expired reset code")
        
        # Check if user exists
        user_ref = db.collection('users').document(email)
        user_doc = user_ref.get()
        
        if not user_doc.exists:
            raise HTTPException(status_code=404, detail="User not found")
        
        # Hash the new password using Argon2id
        password_hash = pwd_context.hash(new_password)
        
        # Update password
        user_ref.update({
            'password_hash': password_hash,
            'password_updated_at': datetime.utcnow()
        })
        
        logger.info(f"Password reset successful for {email}")
        
        return {
            "message": "Password reset successful",
            "email": email
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Reset password error: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Password reset failed")
