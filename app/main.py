from fastapi import FastAPI, HTTPException, Header, Request, Response
from fastapi.responses import FileResponse
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import APIKeyHeader
import os
from typing import Optional
from .config import settings
import secrets
from datetime import datetime, timedelta
import logging

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(title="Personal CDN Service")

# Store active sessions
active_sessions = {}

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", *settings.ALLOWED_ORIGINS],
    allow_credentials=True,
    allow_methods=["GET", "POST", "OPTIONS"],
    allow_headers=["*"],
    expose_headers=["*"],
)

api_key_header = APIKeyHeader(name="x-api-key")

def create_session_token(origin: str) -> str:
    """Create a new session token and store it"""
    session_token = secrets.token_urlsafe(32)
    active_sessions[session_token] = {
        "expires": datetime.now() + timedelta(hours=1),
        "origin": origin
    }
    return session_token

def verify_session(session_token: str, origin: str) -> bool:
    """Verify if a session token is valid"""
    if not session_token:
        logger.warning("No session token provided")
        return False
    
    if session_token not in active_sessions:
        logger.warning(f"Invalid session token: {session_token}")
        return False
    
    session = active_sessions[session_token]
    
    # Check if session has expired
    if datetime.now() > session["expires"]:
        logger.info(f"Session expired for token: {session_token}")
        del active_sessions[session_token]
        return False
    
    # Verify origin
    if origin and origin not in ["http://localhost:3000", *settings.ALLOWED_ORIGINS]:
        logger.warning(f"Invalid origin: {origin}")
        return False
    
    return True

@app.post("/auth")
async def authenticate(request: Request, api_key: str = Header(None, alias="x-api-key")):
    """Authenticate and get a session token"""
    try:
        if not api_key or api_key != settings.API_KEY:
            logger.warning("Invalid or missing API key")
            raise HTTPException(
                status_code=403,
                detail="Invalid or missing API key"
            )
        
        origin = request.headers.get("origin")
        session_token = create_session_token(origin)
        
        logger.info(f"New session created for origin: {origin}")
        return {"session_token": session_token}
        
    except Exception as e:
        logger.error(f"Authentication error: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail="Internal server error"
        )

@app.get("/cdn/{filename}")
async def serve_image(
    filename: str,
    request: Request,
    token: Optional[str] = None,
    session_token: Optional[str] = Header(None, alias="x-session-token")
):
    """Serve an image if the session is valid"""
    try:
        # Use either query parameter token or header token
        actual_token = token or session_token
        
        # Verify session
        if not verify_session(actual_token, request.headers.get("origin")):
            raise HTTPException(
                status_code=403,
                detail="Invalid or expired session"
            )
        
        # Construct file path
        file_path = os.path.join(settings.IMAGE_DIR, filename)
        
        # Check if file exists
        if not os.path.isfile(file_path):
            logger.warning(f"File not found: {filename}")
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
        
        logger.info(f"Serving file: {filename}")
        return FileResponse(
            file_path,
            media_type=content_type,
            filename=filename
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error serving image {filename}: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail="Internal server error"
        )

@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {"status": "healthy"}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000) 