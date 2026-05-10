"""Seed test users (5 faculty + 10 students) for testing."""
import asyncio
from motor.motor_asyncio import AsyncIOMotorClient
import bcrypt
import os
from dotenv import load_dotenv
from datetime import datetime

load_dotenv()

# Test user data
FACULTY_USERS = [
    {
        "email": "faculty1@cse.edu",
        "password": "Faculty1",
        "full_name": "Dr. Rajesh Kumar",
        "employee_id": "FAC001",
        "department": "Computer Science"
    },
    {
        "email": "faculty2@cse.edu",
        "password": "Faculty2",
        "full_name": "Dr. Priya Sharma",
        "employee_id": "FAC002",
        "department": "Computer Science"
    },
    {
        "email": "faculty3@cse.edu",
        "password": "Faculty3",
        "full_name": "Dr. Amit Verma",
        "employee_id": "FAC003",
        "department": "Computer Science"
    },
    {
        "email": "faculty4@cse.edu",
        "password": "Faculty4",
        "full_name": "Dr. Sunita Gupta",
        "employee_id": "FAC004",
        "department": "Computer Science"
    },
    {
        "email": "faculty5@cse.edu",
        "password": "Faculty5",
        "full_name": "Dr. Vikram Singh",
        "employee_id": "FAC005",
        "department": "Computer Science"
    }
]

STUDENT_USERS = [
    {
        "email": "student1@cse.edu",
        "password": "Student1",
        "full_name": "Arjun Mehta",
        "roll_number": "2024001",
        "semester": 1,
        "section": "A"
    },
    {
        "email": "student2@cse.edu",
        "password": "Student2",
        "full_name": "Priya Patel",
        "roll_number": "2024002",
        "semester": 1,
        "section": "A"
    },
    {
        "email": "student3@cse.edu",
        "password": "Student3",
        "full_name": "Rahul Sharma",
        "roll_number": "2024003",
        "semester": 1,
        "section": "A"
    },
    {
        "email": "student4@cse.edu",
        "password": "Student4",
        "full_name": "Sneha Reddy",
        "roll_number": "2024004",
        "semester": 1,
        "section": "A"
    },
    {
        "email": "student5@cse.edu",
        "password": "Student5",
        "full_name": "Aditya Kumar",
        "roll_number": "2024005",
        "semester": 1,
        "section": "A"
    },
    {
        "email": "student6@cse.edu",
        "password": "Student6",
        "full_name": "Kavya Nair",
        "roll_number": "2024006",
        "semester": 1,
        "section": "B"
    },
    {
        "email": "student7@cse.edu",
        "password": "Student7",
        "full_name": "Rohan Das",
        "roll_number": "2024007",
        "semester": 1,
        "section": "B"
    },
    {
        "email": "student8@cse.edu",
        "password": "Student8",
        "full_name": "Ishita Joshi",
        "roll_number": "2024008",
        "semester": 1,
        "section": "B"
    },
    {
        "email": "student9@cse.edu",
        "password": "Student9",
        "full_name": "Vivek Iyer",
        "roll_number": "2024009",
        "semester": 1,
        "section": "B"
    },
    {
        "email": "student10@cse.edu",
        "password": "Student10",
        "full_name": "Meera Srinivasan",
        "roll_number": "2024010",
        "semester": 1,
        "section": "B"
    }
]


async def create_faculty(db, faculty_data):
    """Create a faculty user."""
    email = faculty_data["email"]

    # Check if already exists
    existing = await db.users.find_one({"email": email})
    if existing:
        print(f"  Faculty already exists: {email}")
        return None

    # Hash password
    password_bytes = faculty_data["password"].encode('utf-8')
    password_hash = bcrypt.hashpw(password_bytes, bcrypt.gensalt()).decode('utf-8')

    # Create faculty user - omit student-specific fields entirely
    now = datetime.utcnow()
    user = {
        "email": email,
        "password_hash": password_hash,
        "full_name": faculty_data["full_name"],
        "role": "faculty",
        "is_active": True,
        "employee_id": faculty_data["employee_id"],
        "department": faculty_data["department"],
        "created_at": now,
        "updated_at": now
    }
    # Note: semester, section, roll_number omitted for faculty (avoid index conflicts)

    result = await db.users.insert_one(user)
    print(f"  Created faculty: {email}")
    return result.inserted_id


async def create_student(db, student_data):
    """Create a student user."""
    email = student_data["email"]

    # Check if already exists
    existing = await db.users.find_one({"email": email})
    if existing:
        print(f"  Student already exists: {email}")
        return None

    # Hash password
    password_bytes = student_data["password"].encode('utf-8')
    password_hash = bcrypt.hashpw(password_bytes, bcrypt.gensalt()).decode('utf-8')

    # Create student user - omit faculty-specific fields entirely
    now = datetime.utcnow()
    user = {
        "email": email,
        "password_hash": password_hash,
        "full_name": student_data["full_name"],
        "role": "student",
        "is_active": True,
        "semester": student_data["semester"],
        "section": student_data["section"],
        "roll_number": student_data["roll_number"],
        "created_at": now,
        "updated_at": now
    }
    # Note: employee_id, department omitted for students (avoid index conflicts)

    result = await db.users.insert_one(user)
    print(f"  Created student: {email}")
    return result.inserted_id


async def seed_users():
    """Seed all test users."""
    # Connect to MongoDB with TLS options
    client = AsyncIOMotorClient(
        os.getenv("MONGODB_URL"),
        tls=True,
        tlsAllowInvalidCertificates=True,
        serverSelectionTimeoutMS=30000
    )
    db = client[os.getenv("MONGODB_DATABASE", "academic_system")]

    print("=" * 60)
    print("SEEDING TEST USERS")
    print("=" * 60)

    # Create faculty
    print("\nCreating Faculty Users (5)...")
    faculty_created = 0
    for faculty in FACULTY_USERS:
        result = await create_faculty(db, faculty)
        if result:
            faculty_created += 1

    # Create students
    print("\nCreating Student Users (10)...")
    students_created = 0
    for student in STUDENT_USERS:
        result = await create_student(db, student)
        if result:
            students_created += 1

    print("\n" + "=" * 60)
    print(f"SEEDING COMPLETE!")
    print(f"  Faculty created: {faculty_created}/5")
    print(f"  Students created: {students_created}/10")
    print(f"  Total users: {faculty_created + students_created}")
    print("=" * 60)

    client.close()


async def save_credentials_to_file():
    """Save all credentials to a file."""
    credentials_file = "CREDENTIALS.txt"

    content = "=" * 70 + "\n"
    content += "ACADEMIC SYSTEM - TEST USER CREDENTIALS\n"
    content += "=" * 70 + "\n\n"

    content += "ADMIN CREDENTIALS:\n"
    content += "-" * 70 + "\n"
    content += "Email: admin@cse.edu | Password: admin123\n\n"

    content += "FACULTY CREDENTIALS (5 users):\n"
    content += "-" * 70 + "\n"
    for f in FACULTY_USERS:
        content += f"Email: {f['email']:<25} | Password: {f['password']:<12} | Name: {f['full_name']}\n"

    content += "\nSTUDENT CREDENTIALS (10 users):\n"
    content += "-" * 70 + "\n"
    for s in STUDENT_USERS:
        content += f"Email: {s['email']:<25} | Password: {s['password']:<12} | Name: {s['full_name']:<20} | Roll: {s['roll_number']}\n"

    content += "\n" + "=" * 70 + "\n"
    content += "PASSWORD REQUIREMENTS: 8+ chars, 1 capital letter, 1 number\n"
    content += "All passwords above meet these requirements.\n"
    content += "=" * 70 + "\n"

    with open(credentials_file, "w") as f:
        f.write(content)

    print(f"\nCredentials saved to: {credentials_file}")


async def main():
    """Main function."""
    await seed_users()
    await save_credentials_to_file()


if __name__ == "__main__":
    asyncio.run(main())
