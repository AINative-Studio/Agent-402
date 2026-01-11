"""
Railway entry point for FastAPI application.
This file allows Railway to auto-detect and start the FastAPI app.

Railway will automatically run: uvicorn main:app --host 0.0.0.0 --port $PORT
"""
from app.main import app

# Re-export app for uvicorn to find it
__all__ = ["app"]

if __name__ == "__main__":
    import os
    import uvicorn
    port = int(os.environ.get("PORT", 8000))
    uvicorn.run(app, host="0.0.0.0", port=port)
