# app/adapters/repositories/generation_telemetry_repository.py
"""Repository for generation telemetry with configurable cleanup."""

from datetime import datetime, timedelta
from typing import Optional

from motor.motor_asyncio import AsyncIOMotorDatabase
from bson import ObjectId

from app.domain.entities.feasibility import GenerationTelemetry
from app.infrastructure.config import TelemetryConfig


class GenerationTelemetryRepository:
    """Repository for generation telemetry."""

    def __init__(
        self,
        db: AsyncIOMotorDatabase,
        config: TelemetryConfig
    ):
        self.db = db
        self.config = config
        self.collection = db.generation_telemetry

    async def save(self, telemetry: GenerationTelemetry) -> bool:
        """
        Save telemetry if enabled and under limits.

        Stores telemetry for BOTH successful AND failed generations.
        """
        if not self.config.enabled:
            return True

        if not self.config.persistence_enabled:
            return True

        # Enforce max records
        count = await self.collection.estimated_document_count()
        if count >= self.config.max_records:
            await self._cleanup_oldest()

        doc = self._to_dict(telemetry)
        result = await self.collection.insert_one(doc)
        return result.acknowledged

    async def _cleanup_oldest(self) -> None:
        """
        Remove oldest records when limit reached.

        Note: MongoDB delete_many() does not support sort/limit.
        We fetch oldest IDs first, then delete explicitly.
        """
        # Find oldest 100 records
        cursor = self.collection.find(
            {},
            {"_id": 1}
        ).sort("generation_timestamp", 1).limit(100)

        oldest = await cursor.to_list(length=100)

        if oldest:
            oldest_ids = [doc["_id"] for doc in oldest]
            await self.collection.delete_many({
                "_id": {"$in": oldest_ids}
            })

    async def cleanup_expired(self) -> int:
        """
        Remove records older than retention_days.

        Returns:
            Number of records deleted
        """
        if not self.config.enabled:
            return 0

        cutoff = datetime.utcnow() - timedelta(
            days=self.config.retention_days
        )

        result = await self.collection.delete_many({
            "generation_timestamp": {"$lt": cutoff}
        })

        return result.deleted_count

    def _to_dict(self, telemetry: GenerationTelemetry) -> dict:
        """Convert telemetry entity to document."""
        return {
            "generation_timestamp": telemetry.generation_timestamp,
            "semester": telemetry.semester,
            "section": telemetry.section,
            "feasibility_confidence": telemetry.feasibility_confidence,
            "generation_seed": telemetry.generation_seed,
            "actual_attempts_used": telemetry.actual_attempts_used,
            "success": telemetry.success,
            "duration_ms": telemetry.duration_ms,
            "bottleneck_subjects": telemetry.bottleneck_subjects,
            "total_backtracks": telemetry.total_backtracks,
            "backtrack_by_reason": telemetry.backtrack_by_reason,
            "conflict_hotspots": telemetry.conflict_hotspots
        }
