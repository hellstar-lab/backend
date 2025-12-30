from fastapi import FastAPI
import uvicorn
import os

app = FastAPI()

@app.get("/health")
def health():
    return {"status": "ok", "message": "Minimal App Running"}

@app.get("/")
def root():
    return {"status": "ok", "message": "Minimal App Root"}

if __name__ == "__main__":
    port = int(os.getenv("PORT", 8000))
    uvicorn.run("app:app", host="0.0.0.0", port=port)
