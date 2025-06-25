import os
from dotenv import load_dotenv

load_dotenv()

class Settings:
    API_KEY = os.getenv("API_KEY", "your-secret-key-here")
    ADMIN_USERNAME = os.getenv("ADMIN_USERNAME", "admin")
    ADMIN_PASSWORD = os.getenv("ADMIN_PASSWORD", "admin123")
    ALLOWED_ORIGINS = os.getenv("ALLOWED_ORIGINS", "http://localhost:3000").split(",")
    IMAGE_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "app", "images")
    PUBLIC_IMAGE_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "app", "images", "public")
    PRIVATE_IMAGE_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "app", "images", "private")
    # You can add more settings as needed

settings = Settings() 