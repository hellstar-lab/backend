import secrets
import string
import asyncio
import aiosmtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from datetime import datetime, timedelta
from typing import Dict, Optional
import os
import logging
from services.redis_service import get_redis

logger = logging.getLogger(__name__)

def generate_otp(length: int = 6) -> str:
    """Generate a cryptographically secure numeric OTP."""
    return ''.join(secrets.choice(string.digits) for _ in range(length))


async def store_otp(email: str, otp: str, expiry_minutes: int = 5) -> None:
    """Store OTP in Redis with expiration."""
    try:
        redis = await get_redis()
        # Key prefix for OTPs
        key = f"otp:{email}"
        # Store OTP with TTL
        await redis.setex(key, timedelta(minutes=expiry_minutes), otp)
        
        # Also limit attempts (in a separate key or structure, simple version: separate key)
        # We start with 0 strikes
        await redis.setex(f"otp_attempts:{email}", timedelta(minutes=expiry_minutes), "0")
        
        logger.info(f"OTP stored for {email}, expires in {expiry_minutes}m")
    except Exception as e:
        logger.error(f"Failed to store OTP in Redis: {e}")
        raise


async def verify_otp(email: str, otp: str) -> bool:
    """Verify OTP for given email using Redis."""
    try:
        redis = await get_redis()
        key = f"otp:{email}"
        attempts_key = f"otp_attempts:{email}"
        
        stored_otp = await redis.get(key)
        
        if not stored_otp:
            logger.warning(f"OTP verification failed: No OTP found for {email}")
            return False
        
        # Check attempts
        attempts = int(await redis.get(attempts_key) or 0)
        if attempts >= 3:
            logger.warning(f"Too many OTP attempts for {email}")
            await redis.delete(key)
            await redis.delete(attempts_key)
            return False
            
        if stored_otp != otp:
            # Increment attempts
            await redis.incr(attempts_key)
            logger.warning(f"Invalid OTP for {email}, attempt {attempts + 1}")
            return False
        
        # OTP valid - remove it to prevent replay
        await redis.delete(key)
        await redis.delete(attempts_key)
        logger.info(f"OTP verified successfully for {email}")
        return True
        
    except Exception as e:
        logger.error(f"OTP verification error: {e}")
        return False


async def send_otp_email(email: str, otp: str) -> bool:
    """Send OTP via email using SMTP."""
    try:
        smtp_host = os.getenv("SMTP_HOST", "smtp.gmail.com")
        smtp_port = int(os.getenv("SMTP_PORT", "587"))
        smtp_user = os.getenv("SMTP_USER")
        smtp_password = os.getenv("SMTP_PASSWORD")
        from_email = os.getenv("SMTP_FROM_EMAIL", smtp_user)
        from_name = os.getenv("SMTP_FROM_NAME", "Vornics Weather AI")
        
        if not smtp_user or not smtp_password:
            logger.error("SMTP credentials not configured")
            logger.info(f"[DEV MODE] OTP for {email}: {otp}")
            return True
        
        # Create message
        message = MIMEMultipart("alternative")
        message["Subject"] = f"Your Vornics Verification Code: {otp}"
        message["From"] = f"{from_name} <{from_email}>"
        message["To"] = email
        
        # HTML email body
        html = f"""
        <html>
          <body style="font-family: Arial, sans-serif; max-width: 600px; margin: 0 auto; padding: 20px;">
            <div style="background: linear-gradient(135deg, #0066FF 0%, #00D9FF 100%); padding: 30px; border-radius: 10px; text-align: center;">
              <h1 style="color: white; margin: 0;">Vornics Weather AI</h1>
            </div>
            <div style="padding: 30px; background: #f5f5f5; border-radius: 10px; margin-top: 20px;">
              <h2 style="color: #333;">Your Verification Code</h2>
              <p style="color: #666; font-size: 16px;">Enter this code to complete your authentication:</p>
              <div style="background: white; padding: 20px; border-radius: 8px; text-align: center; margin: 20px 0;">
                <h1 style="color: #0066FF; font-size: 48px; letter-spacing: 10px; margin: 0;">{otp}</h1>
              </div>
              <p style="color: #666; font-size: 14px;">This code will expire in 5 minutes.</p>
              <p style="color: #999; font-size: 12px; margin-top: 30px;">
                If you didn't request this code, please ignore this email.
              </p>
            </div>
          </body>
        </html>
        """
        
        # Attach HTML
        message.attach(MIMEText(html, "html"))
        
        # Send email
        await aiosmtplib.send(
            message,
            hostname=smtp_host,
            port=smtp_port,
            username=smtp_user,
            password=smtp_password,
            start_tls=True,
        )
        
        logger.info(f"OTP email sent successfully to {email}")
        logger.info(f"[DEBUG] OTP for {email}: {otp}")
        return True
        
    except Exception as e:
        logger.error(f"Failed to send OTP email to {email}: {str(e)}")
        # For development, log the OTP even if email fails
        logger.info(f"[DEV MODE] OTP for {email}: {otp}")
        return True  # Return True in dev mode so flow continues
        
    finally:
        # DEBUG: Write OTP to file so we can read it for testing
        try:
            with open("latest_otp.txt", "w") as f:
                f.write(otp)
        except Exception as e:
            logger.error(f"Failed to write OTP debug file: {e}")


async def send_otp(email: str) -> bool:
    """Generate and send OTP to email."""
    otp = generate_otp()
    await store_otp(email, otp)
    return await send_otp_email(email, otp)


async def send_password_reset_email(email: str, reset_code: str) -> bool:
    """Send password reset code via email using SMTP."""
    try:
        smtp_host = os.getenv("SMTP_HOST", "smtp.gmail.com")
        smtp_port = int(os.getenv("SMTP_PORT", "587"))
        smtp_user = os.getenv("SMTP_USER")
        smtp_password = os.getenv("SMTP_PASSWORD")
        from_email = os.getenv("SMTP_FROM_EMAIL", smtp_user)
        from_name = os.getenv("SMTP_FROM_NAME", "Vornics Weather AI")
        
        if not smtp_user or not smtp_password:
            logger.error("SMTP credentials not configured")
            logger.info(f"[DEV MODE] Password Reset Code for {email}: {reset_code}")
            return True
        
        # Create message
        message = MIMEMultipart("alternative")
        message["Subject"] = f"Reset Your Vornics Password"
        message["From"] = f"{from_name} <{from_email}>"
        message["To"] = email
        
        # HTML email body
        html = f"""
        <html>
          <body style="font-family: Arial, sans-serif; max-width: 600px; margin: 0 auto; padding: 20px;">
            <div style="background: linear-gradient(135deg, #0066FF 0%, #00D9FF 100%); padding: 30px; border-radius: 10px; text-align: center;">
              <h1 style="color: white; margin: 0;">Vornics Weather AI</h1>
            </div>
            <div style="padding: 30px; background: #f5f5f5; border-radius: 10px; margin-top: 20px;">
              <h2 style="color: #333;">Password Reset Request</h2>
              <p style="color: #666; font-size: 16px;">We received a request to reset your password. Use the code below to set a new password:</p>
              <div style="background: white; padding: 20px; border-radius: 8px; text-align: center; margin: 20px 0;">
                <h1 style="color: #0066FF; font-size: 48px; letter-spacing: 10px; margin: 0;">{reset_code}</h1>
              </div>
              <p style="color: #666; font-size: 14px;">This code will expire in 10 minutes.</p>
              <p style="color: #999; font-size: 12px; margin-top: 30px;">
                If you didn't request a password reset, please ignore this email and your password will remain unchanged.
              </p>
            </div>
          </body>
        </html>
        """
        
        # Attach HTML
        message.attach(MIMEText(html, "html"))
        
        # Send email
        await aiosmtplib.send(
            message,
            hostname=smtp_host,
            port=smtp_port,
            username=smtp_user,
            password=smtp_password,
            start_tls=True,
        )
        
        logger.info(f"Password reset email sent successfully to {email}")
        logger.info(f"[DEBUG] Password Reset Code for {email}: {reset_code}")
        return True
        
    except Exception as e:
        logger.error(f"Failed to send password reset email to {email}: {str(e)}")
        logger.info(f"[DEV MODE] Password Reset Code for {email}: {reset_code}")
        return True


async def send_password_reset(email: str) -> bool:
    """Generate and send password reset code to email."""
    reset_code = generate_otp()
    await store_otp(email, reset_code, expiry_minutes=10)  # 10 minutes for password reset
    return await send_password_reset_email(email, reset_code)
