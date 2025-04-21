from fastapi import FastAPI, HTTPException, Header, Request
from fastapi.responses import FileResponse
from fastapi.middleware.cors import CORSMiddleware
import os
from typing import Optional
from .config import settings

app = FastAPI(title="Personal CDN Service")

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["GET"],
    allow_headers=["*"],
)

def verify_api_key(api_key: Optional[str] = Header(None, alias="x-api-key")):
    if not api_key or api_key != settings.API_KEY:
        raise HTTPException(
            status_code=403,
            detail="Invalid or missing API key"
        )

@app.get("/cdn/{filename}")
async def serve_image(
    filename: str,
    request: Request,
    api_key: Optional[str] = Header(None, alias="x-api-key")
):
    # Verify API key
    verify_api_key(api_key)
    
    # Verify origin
    origin = request.headers.get("origin")
    if origin and origin not in settings.ALLOWED_ORIGINS:
        raise HTTPException(
            status_code=403,
            detail="Origin not allowed"
        )
    
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