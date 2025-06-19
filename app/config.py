from pydantic_settings import BaseSettings
from typing import List
import os
from dotenv import load_dotenv

load_dotenv()

class Settings(BaseSettings):
    API_KEY: str = os.getenv("API_KEY", "your-secret-key-here")
    ADMIN_USERNAME: str = os.getenv("ADMIN_USERNAME", "admin")
    ADMIN_PASSWORD: str = os.getenv("ADMIN_PASSWORD", "admin123")
    ALLOWED_ORIGINS: List[str] = ["*"]
    IMAGE_DIR: str = os.path.join(os.path.dirname(os.path.dirname(__file__)), "app", "images")
    
    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"

settings = Settings() 