from fastapi import FastAPI, HTTPException, Header, Request, Response, File, UploadFile, Form, Depends, status
from fastapi.responses import FileResponse, HTMLResponse, RedirectResponse, JSONResponse
from fastapi.templating import Jinja2Templates
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
    allow_methods=["GET", "POST", "OPTIONS", "DELETE"],
    allow_headers=["*"],
    expose_headers=["*"],
)

# Security
security = HTTPBasic()

# Create images directory if it doesn't exist
image_dir = os.path.join(os.path.dirname(__file__), "images")
os.makedirs(image_dir, exist_ok=True)
settings.IMAGE_DIR = image_dir
settings.PUBLIC_IMAGE_DIR = os.path.join(image_dir, "public")
settings.PRIVATE_IMAGE_DIR = os.path.join(image_dir, "private")
os.makedirs(settings.PUBLIC_IMAGE_DIR, exist_ok=True)
os.makedirs(settings.PRIVATE_IMAGE_DIR, exist_ok=True)

# Mount static files
static_dir = os.path.join(os.path.dirname(__file__), "static")
os.makedirs(static_dir, exist_ok=True)
app.mount("/static", StaticFiles(directory=static_dir), name="static")
app.mount("/images/public", StaticFiles(directory=settings.PUBLIC_IMAGE_DIR), name="public_images")

async def get_current_user(credentials: HTTPBasicCredentials = Depends(security)):
    is_correct_username = secrets.compare_digest(
        credentials.username.encode("utf8"), settings.ADMIN_USERNAME.encode("utf8")
    )
    is_correct_password = secrets.compare_digest(
        credentials.password.encode("utf8"), settings.ADMIN_PASSWORD.encode("utf8")
    )
    if not (is_correct_username and is_correct_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Basic"},
        )
    return credentials.username

async def get_current_session_user(request: Request) -> str:
    session = get_session(request)
    if not session:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Not authenticated",
        )
    return session["username"]

# Store active sessions
active_sessions = {}

COOKIE_NAME = "session"

@app.post("/api/auth/login")
async def login(credentials: HTTPBasicCredentials = Depends(security)):
    is_correct_username = secrets.compare_digest(
        credentials.username.encode("utf8"), settings.ADMIN_USERNAME.encode("utf8")
    )
    is_correct_password = secrets.compare_digest(
        credentials.password.encode("utf8"), settings.ADMIN_PASSWORD.encode("utf8")
    )
    if not (is_correct_username and is_correct_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
        )

    session_token = secrets.token_urlsafe(32)
    active_sessions[session_token] = {
        "username": credentials.username,
        "expires": datetime.now() + timedelta(hours=2)
    }
    response = JSONResponse(content={"message": "Login successful"})
    response.set_cookie(
        key=COOKIE_NAME,
        value=session_token,
        httponly=True,
        max_age=60*60*2,  # 2 hours
        samesite="lax",
    )
    return response

def get_session(request: Request) -> Optional[dict]:
    session_token = request.cookies.get(COOKIE_NAME)
    if not session_token or session_token not in active_sessions:
        return None
    
    session = active_sessions[session_token]
    if datetime.now() > session["expires"]:
        del active_sessions[session_token]
        return None
        
    return session

@app.get("/", response_class=HTMLResponse)
async def root(request: Request):
    if get_session(request):
        return RedirectResponse(url="/dashboard")
    return RedirectResponse(url="/login")

@app.get("/login", response_class=HTMLResponse)
async def login_page(request: Request):
    if get_session(request):
        return RedirectResponse(url="/dashboard")
    return templates.TemplateResponse("login.html", {"request": request})

@app.get("/dashboard", response_class=HTMLResponse)
async def dashboard(request: Request):
    if not get_session(request):
        return RedirectResponse(url="/login", status_code=303)
    return templates.TemplateResponse("dashboard.html", {"request": request})

@app.get("/logout")
def logout():
    response = RedirectResponse(url="/login", status_code=303)
    response.delete_cookie(COOKIE_NAME)
    # Also remove from active sessions
    # This part needs the token, which is not sent on logout
    # This is a limitation of this simple session management
    return response

@app.get("/api/images")
async def list_images(username: str = Depends(get_current_session_user)):
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
    username: str = Depends(get_current_session_user)
):
    """Upload a new image to the selected folder (public/private)"""
    try:
        if not file.content_type.startswith('image/'):
            raise HTTPException(status_code=400, detail="File must be an image")
        
        filename = secrets.token_hex(8) + os.path.splitext(file.filename)[1]
        
        if category == "public":
            file_path = os.path.join(settings.PUBLIC_IMAGE_DIR, filename)
        else: # private
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
    username: str = Depends(get_current_session_user)
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

@app.get("/cdn/{filename}")
async def serve_private_image(filename: str, request: Request):
    """Serve a private image if the session is valid"""
    session = get_session(request)
    if not session:
        raise HTTPException(status_code=403, detail="Forbidden")
        
    file_path = os.path.join(settings.PRIVATE_IMAGE_DIR, filename)
    if not os.path.isfile(file_path):
        logger.warning(f"File not found: {filename}")
        raise HTTPException(status_code=404, detail="Image not found")
        
    return FileResponse(file_path, filename=filename)

@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {"status": "healthy"}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("app.main:app", host="0.0.0.0", port=8000, reload=True) 