## Project Setup Guide
### 1. Install Dependencies
Install all required packages from `requirements.txt`:
```bash
pip install -r requirements.txt
```

### 2. Create Virtual Environment
Create a virtual environment for the project:
```bash
python -m venv venv
```
Windows:
```bash
venv\Scripts\activate
```

### 3. Install Poppler
Poppler is required for PDF processing (e.g., pdf2image).
Steps:
  Download Poppler
  Extract the file
  Move to:
```bash
C:\poppler-25.07.0\Library\bin
```

### 4. Environment Variables
Create a `.env` file:
```env
DATABASE_URL=your_database_url
GOOGLE_CLIENT_ID=your_google_client_id
GOOGLE_CLIENT_SECRET=your_google_client_secret
POPPLER_PATH=C:\poppler-25.07.0\Library\bin
```

### 5. Run Project
```bash
uvicorn app.main:app --reload
```
