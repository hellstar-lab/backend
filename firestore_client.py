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
db = None

try:
    # Path to the service account key file
    # Look for firestore-key.json in the parent directory (project root)
    backend_dir = Path(__file__).parent
    project_root = backend_dir.parent
    key_file_path = project_root / "firestore-key.json"
    
    if key_file_path.exists():
        logger.info(f"🔥 Loading Firebase credentials from: {key_file_path}")
        
        # Initialize Firebase with service account file
        cred = credentials.Certificate(str(key_file_path))
        firebase_admin.initialize_app(cred)
        db = firestore.client()
        
        logger.info("✅ Firestore initialized successfully with service account file")
        logger.info(f"📊 Connected to project: {cred.project_id}")
        
    else:
        logger.warning(f"⚠️  Firebase key file not found at: {key_file_path}")
        logger.warning("🔄 Attempting to use environment variables...")
        
        # Fallback to environment variables
        from config import settings
        
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
        logger.info("✅ Firestore initialized from environment variables")

except Exception as e:
    logger.error(f"❌ Failed to initialize Firestore. Error details: {str(e)}")
    import traceback
    logger.error(f"Traceback: {traceback.format_exc()}")
    logger.warning("🔄 Using MockFirestore for development")
    
    from unittest.mock import MagicMock
    
    class MockDocument:
        def __init__(self, data=None, exists=False):
            self._data = data
            self.exists = exists
            self.id = "mock_id"
        def to_dict(self): return self._data
        def set(self, data): self._data = data; self.exists = True
        def delete(self): self._data = None; self.exists = False

    class MockCollection:
        def __init__(self): self.docs = {}
        def document(self, doc_id=None):
            if not doc_id: import uuid; doc_id = str(uuid.uuid4())
            if doc_id not in self.docs: self.docs[doc_id] = MockDocument()
            return self.docs[doc_id]
        def where(self, *args): return self # Chainable
        def limit(self, *args): return self
        def stream(self): return []
        def order_by(self, *args, **kwargs): return self

    class MockFirestore:
        """In-memory Mock Firestore for development"""
        def __init__(self): self.collections = {}
        def collection(self, name):
            if name not in self.collections: self.collections[name] = MockCollection()
            return self.collections[name]
        def batch(self): return MagicMock()
    
    db = MockFirestore()

logger.info("🔥 Firestore client ready")
