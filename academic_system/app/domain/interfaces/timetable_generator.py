"""Timetable generator service interface."""

from abc import ABC, abstractmethod
from typing import List, Dict, Any, Optional

from app.domain.entities.timetable import Timetable, DayOfWeek, SlotType


class ITimetableGenerator(ABC):
    """
    Port: Timetable generation service interface.

    This service is responsible for generating timetables based on
    faculty availability, subject requirements, and constraints.
    """

    @abstractmethod
    async def generate(
        self,
        semester: int,
        sections: List[str],
        subject_ids: List[str],
        faculty_availability: Dict[str, Dict[DayOfWeek, List[int]]],
        occupied_slots: Optional[List[Dict[str, Any]]] = None
    ) -> Timetable:
        """
        Generate a timetable for the given parameters.

        Args:
            semester: Semester number (1-8)
            sections: List of sections (e.g., ["A", "B"])
            subject_ids: List of subject IDs to schedule
            faculty_availability: Faculty availability mapping
                {faculty_id: {day: [available_slot_numbers]}}

        Returns:
            Generated timetable with all entries

        Raises:
            ValueError: If generation fails due to constraints
        """
        pass

    @abstractmethod
    async def validate_constraints(
        self,
        semester: int,
        sections: List[str],
        subject_ids: List[str],
        faculty_availability: Dict[str, Dict[DayOfWeek, List[int]]]
    ) -> Dict[str, Any]:
        """
        Validate if timetable generation is possible with given inputs.

        Returns:
            Dictionary with:
                - valid: bool
                - errors: List[str] (if invalid)
                - warnings: List[str]
        """
        pass

    @abstractmethod
    def get_time_slots(self) -> List[Dict[str, Any]]:
        """Get configured time slots."""
        pass

    @abstractmethod
    def get_working_days(self) -> List[DayOfWeek]:
        """Get working days for timetable."""
        pass

    @abstractmethod
    def get_lunch_break_slots(self) -> List[int]:
        """Get lunch break slot numbers."""
        pass
