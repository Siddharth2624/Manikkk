# Academic Management System

A scalable, multi-semester academic timetable and attendance management system built with **FastAPI** + **MongoDB**.

## Quick Start

```bash
cd academic_system
pip install -r requirements.txt
python main.py
```

API: http://localhost:8000/api/v1
Docs: http://localhost:8000/docs

## Features

- ✅ **8 Semesters** support (extended from 1)
- ✅ **Multiple Sections** per semester
- ✅ **JWT Authentication** with role-based access control
- ✅ **Automated Timetable Generation** (preserves original algorithm)
- ✅ **Attendance Tracking** with 75% threshold alerts
- ✅ **Study Materials** upload/download
- ✅ **Clean Architecture** for maintainability

## Project Structure

```
academic_system/
├── app/
│   ├── domain/          # Core business entities & interfaces
│   ├── use_cases/       # Application logic
│   ├── adapters/        # Repositories, controllers, services
│   └── infrastructure/  # Config, database, security
├── tests/              # Test suite
├── main.py             # Application entry point
└── requirements.txt    # Dependencies
```

## Documentation

- [QUICKSTART.md](academic_system/QUICKSTART.md) - Setup guide
- [API.md](academic_system/API.md) - API endpoints
- [DATABASE_SCHEMA.md](academic_system/DATABASE_SCHEMA.md) - MongoDB design
- [ARCHITECTURE.md](academic_system/ARCHITECTURE.md) - Architecture overview

## Tech Stack

- **Framework**: FastAPI 0.109
- **Database**: MongoDB with Motor (async)
- **Authentication**: JWT + bcrypt
- **Python**: 3.10+

## Roles

- **Admin**: Manage users, subjects, generate timetables
- **Faculty**: Mark attendance, upload materials, view schedule
- **Student**: View timetable, check attendance, download materials

---

Developed by Manik Bhagat
