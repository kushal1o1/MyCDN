# Personal CDN Service (Flask Version)

A secure CDN service built with Flask that serves static images with authentication and CORS protection.

## Features

- Secure image serving with session-based authentication
- Public/private image categories with separate folders
- Dashboard with tabs for public and private images
- Category-aware upload and delete
- CORS protection for specific domains
- Support for various image formats (JPEG, PNG, SVG, GIF, WebP)
- Proper error handling (403 for invalid/missing session, 404 for missing images)
- Environment variable configuration via `.env`
- Session-based authentication for better security
- Easy integration with React and other frontend frameworks

## Prerequisites

- Python 3.8 or higher (Python 3.10+ recommended for deployment)
- pip (Python package installer)

## Setup

1. Clone the repository:
```bash
git clone <your-repo-url>
cd MyCDN
```

2. Create and activate a virtual environment:
```bash
# Windows
python -m venv venv
venv\Scripts\activate

# Linux/Mac
python -m venv venv
source venv/bin/activate
```

3. Install dependencies:
```bash
pip install -r requirements.txt
```

4. Create a `.env` file in the root directory with your configuration:
```env
API_KEY=your-secret-key-here
ADMIN_USERNAME=admin
ADMIN_PASSWORD=admin123
ALLOWED_ORIGINS=http://localhost:3000,https://my-portfolio.com
```

5. Create the image folders:
```bash
mkdir -p app/images/public app/images/private
```

6. Run the server locally:
```bash
# On Linux/Mac
export FLASK_APP=app.main:app
export FLASK_ENV=development
flask run

# On Windows (CMD)
set FLASK_APP=app.main:app
set FLASK_ENV=development
flask run
```

## Deployment on PythonAnywhere

1. Upload your project to PythonAnywhere.
2. Create a virtualenv with Python 3.10+ and install requirements:
   ```bash
   mkvirtualenv venv310 --python=/usr/bin/python3.10
   pip install -r /home/<yourusername>/MyCDN/requirements.txt
   ```
3. Set the virtualenv path in the PythonAnywhere Web tab.
4. Edit your WSGI file to include:
   ```python
   import sys
   path = '/home/<yourusername>/MyCDN'
   if path not in sys.path:
       sys.path.append(path)
   from app.main import app as application
   ```
5. Set up static file mappings in the Web tab:
   - URL: `/static/` → Directory: `/home/<yourusername>/MyCDN/app/static`
   - URL: `/images/public/` → Directory: `/home/<yourusername>/MyCDN/app/images/public`
6. Reload your web app from the Web tab.

## Usage

### Dashboard
- Upload images as either **public** or **private** using the category selector.
- Switch between **Public** and **Private** tabs to view/manage images in each category.
- Public images are accessible by anyone at `/images/public/<filename>`.
- Private images are only accessible via `/cdn/<filename>` and require authentication.

### Backend API

#### Upload Image
```
POST /api/upload
Form Data:
- file: (image file)
- category: public | private
- new_filename: (optional)
```

#### List Images
```
GET /api/images
Returns:
{
  "public": ["img1.jpg", ...],
  "private": ["img2.jpg", ...]
}
```

#### Delete Image
```
DELETE /api/images/{category}/{filename}
```

#### Serve Public Image
```
GET /images/public/<filename>
```

#### Serve Private Image (requires session)
```
GET /cdn/<filename>
```

---


