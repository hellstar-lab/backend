from fastapi import FastAPI
import uvicorn
import os

# Initialize FastAPI app with NO dependencies/middleware
app = FastAPI(title="Safe Boot Mode")

@app.get("/health")
def health():
    """Safe Boot Health Check"""
    return {"status": "ok", "mode": "safe_boot"}

@app.get("/")
def root():
    return {"status": "ok", "message": "Safe Boot Active"}

# Note: Start command is now handled by Gunicorn in render.yaml
# But we keep this for local testing
if __name__ == "__main__":
    port = int(os.getenv("PORT", 8000))
    uvicorn.run("app:app", host="0.0.0.0", port=port, reload=False)
