"""Seed sample subjects for timetable generation testing."""
import asyncio
from motor.motor_asyncio import AsyncIOMotorClient
import os
from dotenv import load_dotenv
from bson import ObjectId
from datetime import datetime

load_dotenv()

# Sample subjects for Semester 1
SEMESTER_1_SUBJECTS = [
    {
        "code": "CS101",
        "name": "Introduction to Programming",
        "semester": 1,
        "sections": ["A", "B"],
        "subject_type": "core",
        "credits": 4,
        "classes_per_week": 4,
        "description": "Fundamentals of programming using Python"
    },
    {
        "code": "CS102",
        "name": "Mathematics for Computing",
        "semester": 1,
        "sections": ["A", "B"],
        "subject_type": "core",
        "credits": 3,
        "classes_per_week": 3,
        "description": "Mathematical foundations for computer science"
    },
    {
        "code": "CS103",
        "name": "Digital Logic Design",
        "semester": 1,
        "sections": ["A", "B"],
        "subject_type": "core",
        "credits": 3,
        "classes_per_week": 3,
        "description": "Introduction to digital circuits and logic design"
    },
    {
        "code": "CS104",
        "name": "Computer Systems",
        "semester": 1,
        "sections": ["A", "B"],
        "subject_type": "core",
        "credits": 3,
        "classes_per_week": 3,
        "description": "Introduction to computer organization and architecture"
    },
    {
        "code": "HS101",
        "name": "English Communication",
        "semester": 1,
        "sections": ["A", "B"],
        "subject_type": "elective",
        "credits": 2,
        "classes_per_week": 2,
        "description": "Technical communication and soft skills"
    }
]

# Sample subjects for Semester 2
SEMESTER_2_SUBJECTS = [
    {
        "code": "CS201",
        "name": "Data Structures",
        "semester": 2,
        "sections": ["A", "B"],
        "subject_type": "core",
        "credits": 4,
        "classes_per_week": 4,
        "description": "Advanced data structures and algorithms"
    },
    {
        "code": "CS202",
        "name": "Discrete Mathematics",
        "semester": 2,
        "sections": ["A", "B"],
        "subject_type": "core",
        "credits": 3,
        "classes_per_week": 3,
        "description": "Mathematical logic and discrete structures"
    },
    {
        "code": "CS203",
        "name": "Object Oriented Programming",
        "semester": 2,
        "sections": ["A", "B"],
        "subject_type": "core",
        "credits": 3,
        "classes_per_week": 3,
        "description": "OOP concepts using Java"
    },
    {
        "code": "CS204",
        "name": "Database Management Systems",
        "semester": 2,
        "sections": ["A", "B"],
        "subject_type": "core",
        "credits": 3,
        "classes_per_week": 3,
        "description": "Database design and SQL"
    }
]


async def seed_subjects():
    """Seed sample subjects to the database."""
    client = AsyncIOMotorClient(
        os.getenv("MONGODB_URL"),
        tls=True,
        tlsAllowInvalidCertificates=True,
        serverSelectionTimeoutMS=30000
    )
    db = client[os.getenv("MONGODB_DATABASE", "academic_system")]

    print("=" * 60)
    print("SEEDING SAMPLE SUBJECTS")
    print("=" * 60)

    all_subjects = SEMESTER_1_SUBJECTS + SEMESTER_2_SUBJECTS
    created_count = 0
    skipped_count = 0

    for subject_data in all_subjects:
        # Check if subject already exists by code
        existing = await db.subjects.find_one({"code": subject_data["code"]})
        if existing:
            print(f"  Subject already exists: {subject_data['code']} - {subject_data['name']}")
            skipped_count += 1
            continue

        # Create new subject
        subject = {
            "_id": str(ObjectId()),
            **subject_data,
            "created_at": datetime.utcnow(),
            "updated_at": datetime.utcnow()
        }

        await db.subjects.insert_one(subject)
        print(f"  Created: {subject_data['code']} - {subject_data['name']}")
        created_count += 1

    print("\n" + "=" * 60)
    print(f"SEEDING COMPLETE!")
    print(f"  Subjects created: {created_count}")
    print(f"  Subjects skipped: {skipped_count}")
    print(f"  Total subjects available: {created_count + skipped_count}")
    print("=" * 60)

    client.close()


if __name__ == "__main__":
    asyncio.run(seed_subjects())
