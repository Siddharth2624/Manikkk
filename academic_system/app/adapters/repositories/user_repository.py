"""MongoDB implementation of user repository."""

from typing import List, Optional
from bson import ObjectId
from motor.motor_asyncio import AsyncIOMotorDatabase

from app.domain.entities.user import User, UserRole
from app.domain.interfaces.repositories import IUserRepository
from app.infrastructure.security import hash_password


class UserRepository(IUserRepository):
    """MongoDB implementation of IUserRepository."""

    def __init__(self, db: AsyncIOMotorDatabase):
        self.db = db
        self.collection = db.users

    def _to_entity(self, document: dict) -> User:
        """Convert MongoDB document to User entity."""
        return User(
            id=str(document["_id"]),
            email=document["email"],
            password_hash=document["password_hash"],
            full_name=document["full_name"],
            role=UserRole(document["role"]),
            is_active=document.get("is_active", True),
            created_at=document["created_at"],
            updated_at=document["updated_at"],
            semester=document.get("semester"),
            section=document.get("section"),
            roll_number=document.get("roll_number"),
            employee_id=document.get("employee_id"),
            department=document.get("department")
        )

    def _to_document(self, user: User) -> dict:
        """Convert User entity to MongoDB document."""
        doc = {
            "email": user.email,
            "password_hash": user.password_hash,
            "full_name": user.full_name,
            "role": user.role.value,
            "is_active": user.is_active,
            "created_at": user.created_at,
            "updated_at": user.updated_at,
        }
        if user.semester is not None:
            doc["semester"] = user.semester
        if user.section is not None:
            doc["section"] = user.section
        if user.roll_number is not None:
            doc["roll_number"] = user.roll_number
        if user.employee_id is not None:
            doc["employee_id"] = user.employee_id
        if user.department is not None:
            doc["department"] = user.department
        return doc

    async def find_by_id(self, user_id: str) -> Optional[User]:
        """Find user by ID."""
        try:
            document = await self.collection.find_one({"_id": ObjectId(user_id)})
            return self._to_entity(document) if document else None
        except Exception:
            return None

    async def find_by_email(self, email: str) -> Optional[User]:
        """Find user by email."""
        document = await self.collection.find_one({"email": email.lower()})
        return self._to_entity(document) if document else None

    async def find_by_roll_number(self, roll_number: str) -> Optional[User]:
        """Find student by roll number."""
        document = await self.collection.find_one({
            "roll_number": roll_number,
            "role": UserRole.STUDENT.value
        })
        return self._to_entity(document) if document else None

    async def find_by_employee_id(self, employee_id: str) -> Optional[User]:
        """Find faculty by employee ID."""
        document = await self.collection.find_one({
            "employee_id": employee_id,
            "role": UserRole.FACULTY.value
        })
        return self._to_entity(document) if document else None

    async def find_all(
        self,
        role: Optional[UserRole] = None,
        semester: Optional[int] = None,
        section: Optional[str] = None,
        skip: int = 0,
        limit: int = 20
    ) -> List[User]:
        """Find users with optional filters."""
        query = {}
        if role:
            query["role"] = role.value
        if semester:
            query["semester"] = semester
        if section:
            query["section"] = section

        cursor = self.collection.find(query).skip(skip).limit(limit)
        documents = await cursor.to_list(length=limit)
        return [self._to_entity(doc) for doc in documents]

    async def count(self, role: Optional[UserRole] = None) -> int:
        """Count users by role."""
        query = {"role": role.value} if role else {}
        return await self.collection.count_documents(query)

    async def save(self, user: User) -> User:
        """Save or update user."""
        user.updated_at = user.updated_at or datetime.utcnow()

        if user.id:
            # Update existing user
            await self.collection.update_one(
                {"_id": ObjectId(user.id)},
                {"$set": self._to_document(user)}
            )
        else:
            # Create new user
            result = await self.collection.insert_one(self._to_document(user))
            user.id = str(result.inserted_id)

        return user

    async def delete(self, user_id: str) -> bool:
        """Delete user by ID."""
        try:
            result = await self.collection.delete_one({"_id": ObjectId(user_id)})
            return result.deleted_count > 0
        except Exception:
            return False

    async def exists(self, email: str) -> bool:
        """Check if user exists by email."""
        count = await self.collection.count_documents({"email": email.lower()})
        return count > 0

    async def create_user(
        self,
        email: str,
        password: str,
        full_name: str,
        role: UserRole,
        **kwargs
    ) -> User:
        """Create a new user with hashed password."""
        from datetime import datetime

        user = User(
            id="",  # Will be set by save()
            email=email.lower(),
            password_hash=hash_password(password),
            full_name=full_name,
            role=role,
            is_active=True,
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow(),
            **kwargs
        )
        return await self.save(user)
