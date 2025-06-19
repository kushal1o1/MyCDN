# Personal CDN Service

A secure CDN service built with FastAPI that serves static images with authentication and CORS protection.

## Features

- Secure image serving with session-based authentication
- Public/private image categories with separate folders
- Dashboard with tabs for public and private images
- Category-aware upload and delete
- CORS protection for specific domains
- Support for various image formats (JPEG, PNG, SVG, GIF, WebP)
- Proper error handling (403 for invalid/missing session, 404 for missing images)
- Environment variable configuration
- Session-based authentication for better security
- Easy integration with React and other frontend frameworks

## Prerequisites

- Python 3.8 or higher
- pip (Python package installer)

## Setup

1. Clone the repository:
```bash
git clone <your-repo-url>
cd personal-cdn
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
ALLOWED_ORIGINS=["https://my-portfolio.com", "http://localhost:3000"]
```

5. Create the image folders:
```bash
mkdir -p app/images/public app/images/private
```

6. Run the server:
```bash
uvicorn app.main:app --reload
```

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

