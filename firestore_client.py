"""
Firebase Admin SDK Initialization
Firestore client setup
"""

import firebase_admin
from firebase_admin import credentials, firestore
import logging
import os
from pathlib import Path

logger = logging.getLogger(__name__)

# Initialize Firebase Admin SDK
# Initialize Firebase Admin SDK
db = None

# Define Mocks at Top Level so they are always available
from unittest.mock import MagicMock

class MockDocument:
    def __init__(self, data=None, exists=False):
        self._data = data
        self.exists = exists
        self.id = "mock_id"
    def to_dict(self): return self._data
    def set(self, data, merge=False): self._data = data; self.exists = True
    def update(self, data): 
        if self._data: self._data.update(data)
    def delete(self): self._data = None; self.exists = False
    def get(self): return self

class MockCollection:
    def __init__(self): self.docs = {}
    def document(self, doc_id=None):
        if not doc_id: import uuid; doc_id = str(uuid.uuid4())
        if doc_id not in self.docs: self.docs[doc_id] = MockDocument()
        return self.docs[doc_id]
    def where(self, *args): return self
    def limit(self, *args): return self
    def stream(self): return []
    def order_by(self, *args, **kwargs): return self
    def add(self, data): return (None, None)

class MockFirestore:
    """In-memory Mock Firestore for development"""
    def __init__(self): self.collections = {}
    def collection(self, name):
        if name not in self.collections: self.collections[name] = MockCollection()
        return self.collections[name]
    def batch(self): return MagicMock()
    def transaction(self, *args, **kwargs): return MagicMock()

try:
    # Check if already initialized to prevent reloader errors
    try:
        app = firebase_admin.get_app()
        db = firestore.client()
        logger.info("✅ Firestore already initialized")
    except ValueError:
        # Not initialized, proceed
        # Path to the service account key file
        backend_dir = Path(__file__).parent
        project_root = backend_dir.parent
        key_file_path = project_root / "firestore-key.json"
        
        if key_file_path.exists() and key_file_path.is_file():
            logger.info(f"🔥 Loading Firebase credentials from: {key_file_path}")
            cred = credentials.Certificate(str(key_file_path))
            firebase_admin.initialize_app(cred)
            db = firestore.client()
            logger.info("✅ Firestore initialized from file")
            
        else:
            logger.warning(f"⚠️  Firebase key file not found at: {key_file_path}")
            logger.warning("🔄 Attempting to map environment variables...")
            
            from config import settings
            
            # Sanity check env vars
            if not settings.FIREBASE_PRIVATE_KEY or len(settings.FIREBASE_PRIVATE_KEY) < 50:
                raise ValueError("FIREBASE_PRIVATE_KEY is missing or too short")

            cred_dict = {
                "type": "service_account",
                "project_id": settings.FIREBASE_PROJECT_ID,
                "private_key_id": settings.FIREBASE_PRIVATE_KEY_ID,
                "private_key": settings.FIREBASE_PRIVATE_KEY.replace('\\n', '\n'),
                "client_email": settings.FIREBASE_CLIENT_EMAIL,
                "client_id": settings.FIREBASE_CLIENT_ID,
                "auth_uri": "https://accounts.google.com/o/oauth2/auth",
                "token_uri": "https://oauth2.googleapis.com/token",
                "auth_provider_x509_cert_url": "https://www.googleapis.com/oauth2/v1/certs",
                "client_x509_cert_url": f"https://www.googleapis.com/robot/v1/metadata/x509/{settings.FIREBASE_CLIENT_EMAIL}"
            }
            
            cred = credentials.Certificate(cred_dict)
            firebase_admin.initialize_app(cred)
            db = firestore.client()
            logger.info("✅ Firestore initialized from Environment Variables")

except Exception as e:
    logger.error(f"❌ Failed to initialize Firestore: {str(e)}")
    # import traceback
    # logger.error(traceback.format_exc())
    logger.warning("🔄 Using MockFirestore (Database Disabled)")
    db = MockFirestore()

logger.info("🔥 Firestore client ready")
