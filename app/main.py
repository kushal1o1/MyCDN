from fastapi import FastAPI, HTTPException, Header, Request, Response
from fastapi.responses import FileResponse
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import APIKeyHeader
import os
from typing import Optional
from .config import settings
import secrets
from datetime import datetime, timedelta

app = FastAPI(title="Personal CDN Service")

# Store active sessions
active_sessions = {}

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["GET"],
    allow_headers=["*"],
)

api_key_header = APIKeyHeader(name="x-api-key")

@app.post("/auth")
async def authenticate(request: Request, api_key: str = Header(None, alias="x-api-key")):
    if not api_key or api_key != settings.API_KEY:
        raise HTTPException(
            status_code=403,
            detail="Invalid or missing API key"
        )
    
    # Generate a session token
    session_token = secrets.token_urlsafe(32)
    # Store session with expiration (1 hour)
    active_sessions[session_token] = {
        "expires": datetime.now() + timedelta(hours=1),
        "origin": request.headers.get("origin")
    }
    
    return {"session_token": session_token}

def verify_session(session_token: str, origin: str):
    if session_token not in active_sessions:
        raise HTTPException(
            status_code=403,
            detail="Invalid session"
        )
    
    session = active_sessions[session_token]
    if datetime.now() > session["expires"]:
        del active_sessions[session_token]
        raise HTTPException(
            status_code=403,
            detail="Session expired"
        )
    
    if origin and origin not in settings.ALLOWED_ORIGINS:
        raise HTTPException(
            status_code=403,
            detail="Origin not allowed"
        )

@app.get("/cdn/{filename}")
async def serve_image(
    filename: str,
    request: Request,
    session_token: Optional[str] = Header(None, alias="x-session-token")
):
    # Verify session
    verify_session(session_token, request.headers.get("origin"))
    
    # Construct file path
    file_path = os.path.join(settings.IMAGE_DIR, filename)
    
    # Check if file exists
    if not os.path.isfile(file_path):
        raise HTTPException(
            status_code=404,
            detail="Image not found"
        )
    
    # Determine content type based on file extension
    content_type = "image/jpeg"  # default
    ext = os.path.splitext(filename)[1].lower()
    if ext == ".png":
        content_type = "image/png"
    elif ext == ".svg":
        content_type = "image/svg+xml"
    elif ext == ".gif":
        content_type = "image/gif"
    elif ext == ".webp":
        content_type = "image/webp"
    
    return FileResponse(
        file_path,
        media_type=content_type,
        filename=filename
    )

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000) 