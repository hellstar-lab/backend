from fastapi import FastAPI
import uvicorn
import os

# Initialize FastAPI app with NO dependencies/middleware
app = FastAPI(title="Minimal Green Baseline")

@app.get("/health")
def health():
    """Absolute minimum health check"""
    return {"status": "ok", "message": "Green Baseline Established"}

@app.get("/")
def root():
    return {"status": "ok", "message": "Root is up"}

if __name__ == "__main__":
    port = int(os.getenv("PORT", 8000))
    # Run with reload=False to prevent reloader overhead
    uvicorn.run("app:app", host="0.0.0.0", port=port, reload=False)
