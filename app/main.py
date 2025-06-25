import os
import secrets
from datetime import datetime, timedelta
from flask import Flask, render_template, request, redirect, url_for, session, jsonify, send_from_directory, make_response, flash
from flask_cors import CORS
from werkzeug.utils import secure_filename
from fast_captcha import img_captcha
from .config import settings
import logging
import shutil
import aiofiles
from dotenv import load_dotenv

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = Flask(__name__)
app.secret_key = settings.API_KEY
CORS(app, supports_credentials=True, origins=["http://localhost:3000", *settings.ALLOWED_ORIGINS])

# Create images directory if it doesn't exist
image_dir = os.path.join(os.path.dirname(__file__), "images")
os.makedirs(image_dir, exist_ok=True)
settings.IMAGE_DIR = image_dir
settings.PUBLIC_IMAGE_DIR = os.path.join(image_dir, "public")
settings.PRIVATE_IMAGE_DIR = os.path.join(image_dir, "private")
os.makedirs(settings.PUBLIC_IMAGE_DIR, exist_ok=True)
os.makedirs(settings.PRIVATE_IMAGE_DIR, exist_ok=True)

# In-memory store for captcha text
captcha_store = {}

# Session timeout (2 hours)
SESSION_TIMEOUT = 60 * 60 * 2

@app.route("/api/captcha")
def get_captcha():
    img, text = img_captcha()
    session['captcha'] = text
    response = make_response(img.read())
    response.headers.set('Content-Type', 'image/jpeg')
    return response

@app.route("/api/auth/login", methods=["POST"])
def login():
    username = request.form.get('username')
    password = request.form.get('password')
    print(password,username)
    captcha_text = request.form.get('captcha_text')
    correct_captcha = session.get('captcha')
    if not correct_captcha or not captcha_text or captcha_text.lower() != correct_captcha.lower():
        return jsonify({"detail": "Incorrect CAPTCHA"}), 400
    session['captcha'] = None
    if username != settings.ADMIN_USERNAME or password != settings.ADMIN_PASSWORD:
        return jsonify({"detail": "Incorrect username or password"}), 401
    session['username'] = username
    session['expires'] = (datetime.now() + timedelta(seconds=SESSION_TIMEOUT)).timestamp()
    return jsonify({"message": "Login successful"})

@app.before_request
def make_session_permanent():
    session.permanent = True
    if 'expires' in session:
        if datetime.now().timestamp() > session['expires']:
            session.clear()
            if request.endpoint not in ('login_page', 'login'):
                return redirect(url_for('login_page'))

def is_authenticated():
    return 'username' in session and session['username'] == settings.ADMIN_USERNAME

@app.route("/logout")
def logout():
    session.clear()
    return redirect(url_for('login_page'))

@app.route("/login")
def login_page():
    if is_authenticated():
        return redirect(url_for('dashboard'))
    return render_template("login.html")

@app.route("/")
def root():
    if is_authenticated():
        return redirect(url_for('dashboard'))
    return redirect(url_for('login_page'))

@app.route("/dashboard")
def dashboard():
    if not is_authenticated():
        return redirect(url_for('login_page'))
    return render_template("dashboard.html")

@app.route("/api/images")
def list_images():
    if not is_authenticated():
        return jsonify({"detail": "Not authenticated"}), 401
    try:
        public_files = os.listdir(settings.PUBLIC_IMAGE_DIR)
        private_files = os.listdir(settings.PRIVATE_IMAGE_DIR)
        image_files = {
            "public": [f for f in public_files if f.lower().endswith((".png", ".jpg", ".jpeg", ".gif", ".webp"))],
            "private": [f for f in private_files if f.lower().endswith((".png", ".jpg", ".jpeg", ".gif", ".webp"))]
        }
        return jsonify(image_files)
    except Exception as e:
        logger.error(f"Error listing images: {str(e)}")
        return jsonify({"detail": "Failed to list images"}), 500

@app.route("/api/upload", methods=["POST"])
def upload_image():
    if not is_authenticated():
        return jsonify({"detail": "Not authenticated"}), 401
    file = request.files.get('file')
    category = request.form.get('category')
    new_filename = request.form.get('new_filename')
    if not file or not file.content_type.startswith('image/'):
        return jsonify({"detail": "File must be an image"}), 400
    try:
        if new_filename:
            new_filename = os.path.basename(new_filename)
            base_name, _ = os.path.splitext(new_filename)
            _, original_ext = os.path.splitext(file.filename)
            filename = f"{base_name}{original_ext}"
        else:
            filename = secrets.token_hex(8) + os.path.splitext(file.filename)[1]
        if category == "public":
            file_path = os.path.join(settings.PUBLIC_IMAGE_DIR, filename)
        else:
            file_path = os.path.join(settings.PRIVATE_IMAGE_DIR, filename)
        if os.path.exists(file_path):
            return jsonify({"detail": f"File with name '{filename}' already exists."}), 409
        file.save(file_path)
        return jsonify({"filename": filename, "category": category})
    except Exception as e:
        logger.error(f"Error uploading file: {str(e)}")
        return jsonify({"detail": "Failed to upload file"}), 500

@app.route("/api/images/<category>/<filename>", methods=["DELETE"])
def delete_image(category, filename):
    if not is_authenticated():
        return jsonify({"detail": "Not authenticated"}), 401
    try:
        if category == "public":
            file_path = os.path.join(settings.PUBLIC_IMAGE_DIR, filename)
        else:
            file_path = os.path.join(settings.PRIVATE_IMAGE_DIR, filename)
        if not os.path.exists(file_path):
            return jsonify({"detail": "Image not found"}), 404
        os.remove(file_path)
        return jsonify({"message": "Image deleted successfully"})
    except Exception as e:
        logger.error(f"Error deleting image: {str(e)}")
        return jsonify({"detail": "Failed to delete image"}), 500

@app.route("/cdn/<filename>")
def serve_private_image(filename):
    if not is_authenticated():
        return jsonify({"detail": "Forbidden"}), 403
    file_path = os.path.join(settings.PRIVATE_IMAGE_DIR, filename)
    if not os.path.isfile(file_path):
        logger.warning(f"File not found: {filename}")
        return jsonify({"detail": "Image not found"}), 404
    return send_from_directory(settings.PRIVATE_IMAGE_DIR, filename)

@app.route("/health")
def health_check():
    return {"status": "healthy"}

# Static and public images
@app.route('/static/<path:filename>')
def static_files(filename):
    return send_from_directory(os.path.join(os.path.dirname(__file__), 'static'), filename)

@app.route('/images/public/<path:filename>')
def public_images(filename):
    return send_from_directory(settings.PUBLIC_IMAGE_DIR, filename) 