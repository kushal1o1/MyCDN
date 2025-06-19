from fastapi import FastAPI, HTTPException, Header, Request, Response, File, UploadFile, Form, Depends, status
from fastapi.responses import FileResponse, HTMLResponse, RedirectResponse, JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import APIKeyHeader, HTTPBasic, HTTPBasicCredentials
from fastapi.staticfiles import StaticFiles
import os
from typing import Optional, List
from .config import settings
import secrets
from datetime import datetime, timedelta
import logging
import shutil
from fastapi.templating import Jinja2Templates
import aiofiles
from fastapi.security.utils import get_authorization_scheme_param

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(title="Personal CDN Service")

# Configure templates
templates = Jinja2Templates(directory="app/templates")

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", *settings.ALLOWED_ORIGINS],
    allow_credentials=True,
    allow_methods=["GET", "POST", "OPTIONS"],
    allow_headers=["*"],
    expose_headers=["*"],
)

# Security
security = HTTPBasic()
api_key_header = APIKeyHeader(name="x-api-key")

# Create images directory if it doesn't exist
os.makedirs(settings.IMAGE_DIR, exist_ok=True)

# Mount static files
app.mount("/images/public", StaticFiles(directory=os.path.join(settings.IMAGE_DIR, "public")), name="public_images")
# Do NOT mount private images for public access

async def verify_admin_auth(credentials: HTTPBasicCredentials = Depends(security)) -> bool:
    """Verify admin credentials"""
    is_correct_username = secrets.compare_digest(
        credentials.username.encode("utf8"),
        settings.ADMIN_USERNAME.encode("utf8"),
    )
    is_correct_password = secrets.compare_digest(
        credentials.password.encode("utf8"),
        settings.ADMIN_PASSWORD.encode("utf8"),
    )
    
    if not (is_correct_username and is_correct_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Basic"},
        )
    return True

# Store active sessions
active_sessions = {}

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

@app.get("/", response_class=HTMLResponse)
async def root():
    """Redirect to login page by default"""
    return RedirectResponse(url="/login")

@app.get("/login", response_class=HTMLResponse)
async def login_page(request: Request):
    """Render login page"""
    return templates.TemplateResponse("login.html", {"request": request})

COOKIE_NAME = "session"
COOKIE_VALUE = secrets.token_urlsafe(16)  # Random value for this server instance

@app.get("/dashboard", response_class=HTMLResponse)
async def dashboard(request: Request):
    session_cookie = request.cookies.get(COOKIE_NAME)
    if session_cookie != COOKIE_VALUE:
        return RedirectResponse(url="/login", status_code=303)
    return templates.TemplateResponse("dashboard.html", {"request": request})

@app.get("/logout")
def logout():
    response = RedirectResponse(url="/login", status_code=303)
    response.delete_cookie(COOKIE_NAME)
    return response

@app.get("/api/images")
async def list_images(credentials: HTTPBasicCredentials = Depends(verify_admin_auth)):
    """List all images in public and private folders"""
    try:
        public_files = os.listdir(settings.PUBLIC_IMAGE_DIR)
        private_files = os.listdir(settings.PRIVATE_IMAGE_DIR)
        image_files = {
            "public": [f for f in public_files if f.lower().endswith((".png", ".jpg", ".jpeg", ".gif", ".webp"))],
            "private": [f for f in private_files if f.lower().endswith((".png", ".jpg", ".jpeg", ".gif", ".webp"))]
        }
        return image_files
    except Exception as e:
        logger.error(f"Error listing images: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to list images")

@app.post("/api/upload")
async def upload_image(
    file: UploadFile = File(...),
    category: str = Form(...),
    request: Request = None
):
    """Upload a new image to the selected folder (public/private)"""
    try:
        if not file.content_type.startswith('image/'):
            raise HTTPException(status_code=400, detail="File must be an image")
        filename = file.filename
        if category == "public":
            file_path = os.path.join(settings.PUBLIC_IMAGE_DIR, filename)
        else:
            file_path = os.path.join(settings.PRIVATE_IMAGE_DIR, filename)
        async with aiofiles.open(file_path, 'wb') as out_file:
            content = await file.read()
            await out_file.write(content)
        return {"filename": filename, "category": category}
    except Exception as e:
        logger.error(f"Error uploading file: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to upload file")

@app.delete("/api/images/{category}/{filename}")
async def delete_image(
    category: str,
    filename: str,
    credentials: HTTPBasicCredentials = Depends(verify_admin_auth)
):
    """Delete an image from the selected folder"""
    try:
        if category == "public":
            file_path = os.path.join(settings.PUBLIC_IMAGE_DIR, filename)
        else:
            file_path = os.path.join(settings.PRIVATE_IMAGE_DIR, filename)
        if not os.path.exists(file_path):
            raise HTTPException(status_code=404, detail="Image not found")
        os.remove(file_path)
        return {"message": "Image deleted successfully"}
    except Exception as e:
        logger.error(f"Error deleting image: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to delete image")

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

@app.post("/api/auth/login")
async def login(request: Request, username: str = Form(...), password: str = Form(...)):
    is_correct_username = secrets.compare_digest(
        username.encode("utf8"),
        settings.ADMIN_USERNAME.encode("utf8"),
    )
    is_correct_password = secrets.compare_digest(
        password.encode("utf8"),
        settings.ADMIN_PASSWORD.encode("utf8"),
    )
    if is_correct_username and is_correct_password:
        response = RedirectResponse(url="/dashboard", status_code=303)
        response.set_cookie(
            key=COOKIE_NAME,
            value=COOKIE_VALUE,
            httponly=True,
            max_age=60*60*2,  # 2 hours
            samesite="lax"
        )
        return response
    else:
        return RedirectResponse(url="/login?error=1", status_code=303)

@app.get("/cdn/{filename}")
async def serve_image(
    filename: str,
    request: Request
):
    """Serve a private image if the session is valid"""
    session_cookie = request.cookies.get(COOKIE_NAME)
    if session_cookie != COOKIE_VALUE:
        raise HTTPException(status_code=403, detail="Forbidden")
    file_path = os.path.join(settings.IMAGE_DIR, "private", filename)
    if not os.path.isfile(file_path):
        logger.warning(f"File not found: {filename}")
        raise HTTPException(status_code=404, detail="Image not found")
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

@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {"status": "healthy"}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000) 