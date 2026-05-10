# Quick Start Guide

## Prerequisites

- Python 3.10 or higher
- MongoDB 4.4 or higher
- pip or poetry for package management

---

## Installation

### 1. Clone/Create Project

The project structure has been created at:
```
C:\Users\91639\OneDrive\Documents\CODES\MANIK_FYP\academic_system\
```

### 2. Install Dependencies

```bash
cd C:\Users\91639\OneDrive\Documents\CODES\MANIK_FYP\academic_system

# Using pip
pip install -r requirements.txt

# Or using poetry
poetry install
```

### 3. Configure Environment

Copy `.env.example` to `.env`:

```bash
cp .env.example .env
```

Edit `.env` with your configuration:

```env
# MongoDB
MONGODB_URL=mongodb://localhost:27017
MONGODB_DATABASE=academic_system

# JWT Secret (change in production!)
JWT_SECRET_KEY=your-super-secret-jwt-key-here

# Application
ENVIRONMENT=development
API_PREFIX=/api/v1
```

### 4. Start MongoDB

Make sure MongoDB is running:

```bash
# Windows (assuming default installation)
mongod

# Or using MongoDB Compass
# Just open the application
```

### 5. Run the Application

```bash
# Development mode with auto-reload
python main.py

# Or using uvicorn directly
uvicorn main:app --reload --host 0.0.0.0 --port 8000
```

The API will be available at:
- API: http://localhost:8000/api/v1
- Swagger Docs: http://localhost:8000/docs
- ReDoc: http://localhost:8000/redoc

---

## Initial Setup

### 1. Create Admin User

Use the register endpoint or create via MongoDB shell:

```python
# Using Python shell
from motor.motor_asyncio import AsyncIOMotorClient
from app.infrastructure.security import hash_password

client = AsyncIOMotorClient("mongodb://localhost:27017")
db = client.academic_system

admin = {
    "email": "admin@example.com",
    "password_hash": hash_password("AdminPass123!"),
    "full_name": "System Admin",
    "role": "admin",
    "is_active": True,
    "created_at": datetime.utcnow(),
    "updated_at": datetime.utcnow()
}

await db.users.insert_one(admin)
```

### 2. Create Faculty Availability

For each faculty, set their availability for timetable generation:

```json
{
  "faculty_id": "FACULTY_ID",
  "day": "MON",
  "slots": [1, 2, 3, 4, 7, 8, 9]
}
```

---

## Common Workflows

### Workflow 1: Generate Timetable

1. Create subjects for the semester
2. Create faculty and set their availability
3. Call the generate timetable endpoint:

```bash
curl -X POST "http://localhost:8000/api/v1/timetable/generate" \
  -H "Authorization: Bearer YOUR_ADMIN_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "semester": 1,
    "sections": ["A", "B"],
    "academic_year": "2024-2025",
    "subject_ids": ["subject_id_1", "subject_id_2"],
    "faculty_availability": {
      "faculty_id_1": {
        "MON": [1, 2, 3, 4, 7, 8, 9],
        "TUE": [1, 2, 3, 7, 8, 9],
        "WED": [1, 2, 3, 4, 7, 8, 9],
        "THU": [1, 2, 3, 7, 8, 9],
        "FRI": [1, 2, 3, 4, 7, 8, 9]
      }
    }
  }'
```

### Workflow 2: Mark Attendance

```bash
curl -X POST "http://localhost:8000/api/v1/attendance/mark" \
  -H "Authorization: Bearer YOUR_FACULTY_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "subject_id": "SUBJECT_ID",
    "section": "A",
    "attendance_date": "2024-01-15",
    "attendance": [
      {"student_id": "STUDENT_1_ID", "status": "present"},
      {"student_id": "STUDENT_2_ID", "status": "absent", "remarks": "Sick"}
    ]
  }'
```

### Workflow 3: Upload Study Material

```bash
curl -X POST "http://localhost:8000/api/v1/materials/upload" \
  -H "Authorization: Bearer YOUR_FACULTY_TOKEN" \
  -F "metadata={\"title\":\"Lecture Notes\",\"subject_id\":\"SUBJECT_ID\",\"semester\":1,\"sections\":[\"A\"],\"tags\":[\"lecture\"]};type=application/json" \
  -F "file=@/path/to/file.pdf"
```

---

## Running Tests

```bash
# Run all tests
pytest

# Run specific test file
pytest tests/test_auth.py

# Run with coverage
pytest --cov=app tests/

# View detailed output
pytest -v
```

---

## Troubleshooting

### MongoDB Connection Error

```
ServerSelectionTimeoutError: No servers found
```

**Solution:** Make sure MongoDB is running:
```bash
# Check if MongoDB is running
mongod

# Or check service status
# Windows: Services > MongoDB
```

### Import Errors

```
ModuleNotFoundError: No module named 'xxx'
```

**Solution:** Install dependencies:
```bash
pip install -r requirements.txt
```

### Port Already in Use

```
OSError: [Errno 48] Address already in use
```

**Solution:** Either stop the process using port 8000 or use a different port:
```bash
uvicorn main:app --port 8001
```

---

## Production Deployment

### Using Gunicorn

```bash
pip install gunicorn

gunicorn main:app \
  --workers 4 \
  --worker-class uvicorn.workers.UvicornWorker \
  --bind 0.0.0.0:8000
```

### Using Docker

```dockerfile
FROM python:3.10-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install -r requirements.txt

COPY . .

EXPOSE 8000

CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
```

### Environment Variables for Production

```env
ENVIRONMENT=production
DEBUG=False
MONGODB_URL=mongodb://your-production-host:27017
JWT_SECRET_KEY=change-this-to-a-random-64-character-string
CORS_ORIGINS=["https://yourdomain.com"]
```

---

## Next Steps

1. Review the [API Documentation](API.md)
2. Check the [Database Schema](DATABASE_SCHEMA.md)
3. Explore the clean architecture in `app/`
4. Customize for your specific requirements
