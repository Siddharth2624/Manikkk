"""MongoDB implementation of attendance repository."""

from typing import List, Optional
from datetime import date, datetime
from bson import ObjectId
from motor.motor_asyncio import AsyncIOMotorDatabase

from app.domain.entities.attendance import AttendanceRecord, AttendanceSummary, AttendanceStatus
from app.domain.interfaces.repositories import IAttendanceRepository


class AttendanceRepository(IAttendanceRepository):
    """MongoDB implementation of IAttendanceRepository."""

    def __init__(self, db: AsyncIOMotorDatabase): # type: ignore
        self.db = db
        self.collection = db.attendances

    def _to_entity(self, document: dict) -> AttendanceRecord:
        """Convert MongoDB document to AttendanceRecord entity."""
        # Handle date conversion - MongoDB stores as datetime, entity expects date
        doc_date = document.get("date")
        if doc_date:
            if isinstance(doc_date, datetime):
                doc_date = doc_date.date()
            elif isinstance(doc_date, str):
                # Parse ISO date string
                from datetime import datetime as dt
                doc_date = dt.fromisoformat(doc_date).date()

        # Handle marked_at - MongoDB returns datetime
        doc_marked_at = document.get("marked_at")
        if doc_marked_at is None:
            doc_marked_at = datetime.utcnow()
        elif isinstance(doc_marked_at, date) and not isinstance(doc_marked_at, datetime):
            # Convert date to datetime
            doc_marked_at = datetime.combine(doc_marked_at, datetime.min.time())

        # Handle updated_at - MongoDB returns datetime
        doc_updated_at = document.get("updated_at")
        if doc_updated_at is None:
            doc_updated_at = datetime.utcnow()
        elif isinstance(doc_updated_at, date) and not isinstance(doc_updated_at, datetime):
            # Convert date to datetime
            doc_updated_at = datetime.combine(doc_updated_at, datetime.min.time())

        return AttendanceRecord(
            id=str(document["_id"]),
            student_id=document["student_id"],
            subject_id=document["subject_id"],
            faculty_id=document["faculty_id"],
            date=doc_date,
            status=AttendanceStatus(document["status"]),
            remarks=document.get("remarks"),
            marked_at=doc_marked_at,
            updated_at=doc_updated_at
        )

    def _to_document(self, attendance: AttendanceRecord) -> dict:
        """Convert AttendanceRecord entity to MongoDB document."""
        # Convert date to datetime for MongoDB (BSON cannot encode date objects)
        doc_date = attendance.date
        if isinstance(doc_date, date) and not isinstance(doc_date, datetime):
            doc_date = datetime.combine(doc_date, datetime.min.time())

        return {
            "student_id": attendance.student_id,
            "subject_id": attendance.subject_id,
            "faculty_id": attendance.faculty_id,
            "date": doc_date,
            "status": attendance.status.value,
            "remarks": attendance.remarks,
            "marked_at": attendance.marked_at,
            "updated_at": attendance.updated_at
        }

    def _date_for_query(self, attendance_date: date) -> datetime:
        """Convert date to datetime for MongoDB queries."""
        if isinstance(attendance_date, datetime):
            return attendance_date
        return datetime.combine(attendance_date, datetime.min.time())

    async def save(self, attendance: AttendanceRecord) -> AttendanceRecord:
        """Save or update attendance record."""
        attendance.updated_at = datetime.utcnow()

        # Check if record exists
        existing = await self.collection.find_one({
            "student_id": attendance.student_id,
            "subject_id": attendance.subject_id,
            "date": self._date_for_query(attendance.date)
        })

        if existing:
            await self.collection.update_one(
                {"_id": existing["_id"]},
                {"$set": self._to_document(attendance)}
            )
            attendance.id = str(existing["_id"])
        else:
            result = await self.collection.insert_one(self._to_document(attendance))
            attendance.id = str(result.inserted_id)

        return attendance

    async def save_batch(self, attendances: List[AttendanceRecord]) -> bool:
        """Save multiple attendance records."""
        operations = []
        for attendance in attendances:
            attendance.updated_at = datetime.utcnow()
            operations.append({
                "filter": {
                    "student_id": attendance.student_id,
                    "subject_id": attendance.subject_id,
                    "date": self._date_for_query(attendance.date)
                },
                "update": {"$set": self._to_document(attendance)},
                "upsert": True
            })

        if operations:
            from pymongo import UpdateOne
            result = await self.collection.bulk_write([
                UpdateOne(op["filter"], op["update"], upsert=op["upsert"])
                for op in operations
            ])
            return result.acknowledged

        return True

    async def find_by_student_and_subject(
        self,
        student_id: str,
        subject_id: str,
        start_date: Optional[date] = None,
        end_date: Optional[date] = None
    ) -> List[AttendanceRecord]:
        """Find attendance records for a student in a subject."""
        query = {
            "student_id": student_id,
            "subject_id": subject_id
        }

        if start_date or end_date:
            date_query = {}
            if start_date:
                date_query["$gte"] = self._date_for_query(start_date)
            if end_date:
                # Include the entire end date by using end of day
                end_datetime = datetime.combine(end_date, datetime.max.time())
                date_query["$lte"] = end_datetime
            query["date"] = date_query

        cursor = self.collection.find(query).sort("date", 1)
        documents = await cursor.to_list(length=None)
        return [self._to_entity(doc) for doc in documents]

    async def find_by_subject_and_date(
        self,
        subject_id: str,
        attendance_date: date
    ) -> List[AttendanceRecord]:
        """Find all attendance records for a subject on a date."""
        cursor = self.collection.find({
            "subject_id": subject_id,
            "date": self._date_for_query(attendance_date)
        })
        documents = await cursor.to_list(length=None)
        return [self._to_entity(doc) for doc in documents]

    async def get_summary(
        self,
        student_id: str,
        subject_id: str
    ) -> Optional[AttendanceSummary]:
        """Get attendance summary for a student in a subject."""
        records = await self.find_by_student_and_subject(student_id, subject_id)

        if not records:
            return None

        return AttendanceSummary.from_records(student_id, subject_id, records)

    async def get_all_summaries(
        self,
        student_id: str
    ) -> List[AttendanceSummary]:
        """Get attendance summaries for all subjects of a student."""
        pipeline = [
            {"$match": {"student_id": student_id}},
            {"$group": {
                "_id": "$subject_id",
                "total": {"$sum": 1},
                "present": {
                    "$sum": {"$cond": [{"$eq": ["$status", "present"]}, 1, 0]}
                },
                "absent": {
                    "$sum": {"$cond": [{"$in": ["$status", ["absent", "excused"]]}, 1, 0]}
                }
            }}
        ]

        results = await self.collection.aggregate(pipeline).to_list(length=None)

        summaries = []
        for result in results:
            total = result["total"]
            present = result["present"]
            absent = result["absent"]
            percentage = (present / total * 100) if total > 0 else 0

            summaries.append(AttendanceSummary(
                student_id=student_id,
                subject_id=result["_id"],
                total_classes=total,
                present_count=present,
                absent_count=absent,
                excused_count=0,
                percentage=round(percentage, 2),
                is_below_threshold=percentage < 75.0
            ))

        return summaries

    async def find_by_date_range(
        self,
        subject_id: str,
        start_date: date,
        end_date: date
    ) -> List[AttendanceRecord]:
        """Find attendance records within a date range."""
        cursor = self.collection.find({
            "subject_id": subject_id,
            "date": {
                "$gte": self._date_for_query(start_date),
                "$lte": datetime.combine(end_date, datetime.max.time())
            }
        }).sort("date", 1)
        documents = await cursor.to_list(length=None)
        return [self._to_entity(doc) for doc in documents]

    async def delete(self, attendance_id: str) -> bool:
        """Delete attendance record."""
        try:
            result = await self.collection.delete_one({"_id": ObjectId(attendance_id)})
            return result.deleted_count > 0
        except Exception:
            return False
