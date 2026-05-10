"""Create admin user for testing."""
import asyncio
from motor.motor_asyncio import AsyncIOMotorClient
import bcrypt
import os
from dotenv import load_dotenv
from datetime import datetime

load_dotenv()

async def create_admin():
    """Create an admin user in the database."""
    # Connect to MongoDB
    client = AsyncIOMotorClient(os.getenv("MONGODB_URL"))
    db = client[os.getenv("MONGODB_DATABASE", "academic_system")]

    # Admin user data
    admin_email = "admin@cse.edu"
    admin_password = "Admin123"
    admin_name = "System Administrator"

    # Check if admin already exists
    existing = await db.users.find_one({"email": admin_email})
    if existing:
        print(f"Admin user already exists!")
        print(f"   Email: {admin_email}")
        print(f"   Password: {admin_password}")
        client.close()
        return

    # Hash password using bcrypt directly
    password_bytes = admin_password.encode('utf-8')
    password_hash = bcrypt.hashpw(password_bytes, bcrypt.gensalt()).decode('utf-8')

    # Create admin user
    from datetime import datetime
    now = datetime.utcnow()
    admin_user = {
        "email": admin_email,
        "password_hash": password_hash,
        "full_name": admin_name,
        "role": "admin",
        "is_active": True,
        "semester": None,
        "section": None,
        "roll_number": None,
        "employee_id": None,
        "department": None,
        "created_at": now,
        "updated_at": now
    }

    # Insert admin
    result = await db.users.insert_one(admin_user)

    print(f"Admin user created successfully!")
    print(f"   Email: {admin_email}")
    print(f"   Password: {admin_password}")
    print(f"   ID: {result.inserted_id}")

    client.close()

if __name__ == "__main__":
    asyncio.run(create_admin())
