"""Tests for domain exceptions."""

import pytest
from app.domain.exceptions import FeasibilityError
from app.domain.entities.feasibility import FeasibilityReport, FeasibilityStatus, Recoverability, WarningCollection


def test_feasibility_error_creation():
    """Verify FeasibilityError stores message and report correctly."""
    # Create a sample feasibility report
    report = FeasibilityReport(
        status=FeasibilityStatus.FAIL,
        confidence_score=0,
        recoverability=Recoverability.NEAR_IMPOSSIBLE,
        errors=["No available slots for CS101"],
        warnings=WarningCollection(),
        constraint_scores={},
        suggestions=[]
    )

    # Create the error with message and report
    error = FeasibilityError(
        message="Cannot generate timetable: No available slots",
        report=report
    )

    # Verify attributes are stored correctly
    assert error.message == "Cannot generate timetable: No available slots"
    assert error.report is report
    assert error.report.status == FeasibilityStatus.FAIL
    assert str(error) == "Cannot generate timetable: No available slots"
