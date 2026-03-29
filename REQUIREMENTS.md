# Project Requirements

This project uses multiple requirements files for different environments:

## Files Overview

- **`requirements.txt`** - Complete list of all installed packages (full dependency tree)
- **`requirements-prod.txt`** - Minimal production dependencies for running the application
- **`requirements-dev.txt`** - Development dependencies including testing, linting, and code quality tools

## Installation

### For Production
```bash
pip install -r requirements-prod.txt
```

### For Development
```bash
pip install -r requirements-dev.txt
```

### For Full Environment (all packages currently installed)
```bash
pip install -r requirements.txt
```

## Core Dependencies

- **FastAPI** - Web framework for building APIs
- **uvicorn** - ASGI server for running FastAPI
- **easyocr** - Optical Character Recognition (OCR) with support for Thai and English
- **opencv-python** - Computer vision and image processing
- **pdf2image** - Convert PDF pages to images
- **PyMuPDF** - PDF text extraction
- **pythainlp** - Thai NLP for spell checking
- **attacut** - Thai word tokenization
- **requests** - HTTP requests library
- **pydantic** - Data validation using Python type annotations

## System Requirements

- Python 3.10+
- For PDF processing: `poppler` must be installed and configured (see `UploadServices.poppler_path` in the code)

## Running the Application

```bash
# Make sure dependencies are installed
pip install -r requirements-prod.txt

# Run the development server with auto-reload
uvicorn app.main:app --reload

# Run the production server
uvicorn app.main:app --host 0.0.0.0 --port 8000
```

## API Endpoints

- `POST /upload` - Upload a document file for OCR processing

The server runs on `http://localhost:8000` by default.
