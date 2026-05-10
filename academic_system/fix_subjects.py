"""Fix existing subjects with invalid subject_type and re-seed."""
import asyncio
from motor.motor_asyncio import AsyncIOMotorClient
import os
from dotenv import load_dotenv
from bson import ObjectId
from datetime import datetime

load_dotenv()

async def fix_subjects():
    """Delete subjects with invalid types and re-seed with correct types."""
    client = AsyncIOMotorClient(
        os.getenv("MONGODB_URL"),
        tls=True,
        tlsAllowInvalidCertificates=True,
        serverSelectionTimeoutMS=30000
    )
    db = client[os.getenv("MONGODB_DATABASE", "academic_system")]

    print("=" * 60)
    print("FIXING SUBJECTS")
    print("=" * 60)

    # Delete all existing subjects
    result = await db.subjects.delete_many({})
    print(f"Deleted {result.deleted_count} existing subjects")

    # Re-seed with correct subject_type values
    subjects = [
        {
            "code": "CS101",
            "name": "Introduction to Programming",
            "semester": 1,
            "subject_type": "core",
            "credits": 4,
            "classes_per_week": 4,
            "description": "Fundamentals of programming using Python"
        },
        {
            "code": "CS102",
            "name": "Mathematics for Computing",
            "semester": 1,
            "subject_type": "core",
            "credits": 3,
            "classes_per_week": 3,
            "description": "Mathematical foundations for computer science"
        },
        {
            "code": "CS103",
            "name": "Digital Logic Design",
            "semester": 1,
            "subject_type": "core",
            "credits": 3,
            "classes_per_week": 3,
            "description": "Introduction to digital circuits and logic design"
        },
        {
            "code": "CS104",
            "name": "Computer Systems",
            "semester": 1,
            "subject_type": "core",
            "credits": 3,
            "classes_per_week": 3,
            "description": "Introduction to computer organization and architecture"
        },
        {
            "code": "HS101",
            "name": "English Communication",
            "semester": 1,
            "subject_type": "elective",
            "credits": 2,
            "classes_per_week": 2,
            "description": "Technical communication and soft skills"
        },
        {
            "code": "CS201",
            "name": "Data Structures",
            "semester": 2,
            "subject_type": "core",
            "credits": 4,
            "classes_per_week": 4,
            "description": "Advanced data structures and algorithms"
        },
        {
            "code": "CS202",
            "name": "Discrete Mathematics",
            "semester": 2,
            "subject_type": "core",
            "credits": 3,
            "classes_per_week": 3,
            "description": "Mathematical logic and discrete structures"
        },
        {
            "code": "CS203",
            "name": "Object Oriented Programming",
            "semester": 2,
            "subject_type": "core",
            "credits": 3,
            "classes_per_week": 3,
            "description": "OOP concepts using Java"
        },
        {
            "code": "CS204",
            "name": "Database Management Systems",
            "semester": 2,
            "subject_type": "core",
            "credits": 3,
            "classes_per_week": 3,
            "description": "Database design and SQL"
        }
    ]

    created_count = 0
    for subject_data in subjects:
        subject = {
            "_id": ObjectId(),
            **subject_data,
            "created_at": datetime.utcnow(),
            "updated_at": datetime.utcnow()
        }
        await db.subjects.insert_one(subject)
        print(f"  Created: {subject_data['code']} - {subject_data['name']}")
        created_count += 1

    print("\n" + "=" * 60)
    print(f"FIXING COMPLETE!")
    print(f"  Subjects created: {created_count}")
    print("=" * 60)

    client.close()

if __name__ == "__main__":
    asyncio.run(fix_subjects())
