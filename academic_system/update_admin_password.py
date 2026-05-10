"""Update admin password to meet new requirements."""
import asyncio
from motor.motor_asyncio import AsyncIOMotorClient
import bcrypt
import os
from dotenv import load_dotenv

load_dotenv()

async def update_admin_password():
    """Update admin password in database."""
    client = AsyncIOMotorClient(
        os.getenv("MONGODB_URL"),
        tls=True,
        tlsAllowInvalidCertificates=True,
        serverSelectionTimeoutMS=30000
    )
    db = client[os.getenv("MONGODB_DATABASE", "academic_system")]

    # New admin password
    admin_email = "admin@cse.edu"
    new_password = "Admin123"

    # Hash new password
    password_bytes = new_password.encode('utf-8')
    password_hash = bcrypt.hashpw(password_bytes, bcrypt.gensalt()).decode('utf-8')

    # Update admin password
    result = await db.users.update_one(
        {"email": admin_email},
        {"$set": {"password_hash": password_hash}}
    )

    if result.modified_count > 0:
        print(f"Admin password updated successfully!")
        print(f"   Email: {admin_email}")
        print(f"   New Password: {new_password}")
    else:
        print(f"Admin not found or password already set.")

    client.close()

if __name__ == "__main__":
    asyncio.run(update_admin_password())
