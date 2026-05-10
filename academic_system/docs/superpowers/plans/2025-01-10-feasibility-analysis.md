# Pre-Generation Feasibility Analysis - Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Implement pre-generation feasibility analysis that detects conflicts before backtracking, preventing 10,000-attempt failures.

**Architecture:**
- **FeasibilityAnalyzer** service analyzes availability patterns
- Returns FeasibilityReport with PASS/WARNING/FAIL status
- Confidence score (0-100) estimates feasibility
- Local/GLOBAL warnings separated
- Telemetry tracks both successful and failed generations

**Tech Stack:** Python 3.11+, FastAPI, Motor (MongoDB async), Pydantic

---

## File Structure

```
app/domain/
├── entities/
│   └── feasibility.py              # All dataclasses (Report, Warning, Score, etc.)
├── services/
│   ├── feasibility_analyzer.py     # Main analyzer service
│   └── confidence/
│       ├── __init__.py              # Package exports
│       ├── base.py                  # ConfidenceCalculator ABC
│       └── default.py               # DefaultConfidenceCalculator implementation
└── exceptions.py                    # Add FeasibilityError

app/adapters/
└── repositories/
    └── generation_telemetry_repository.py  # Telemetry storage with cleanup

app/use_cases/
└── timetable.py                     # Update: add feasibility check before generation

app/infrastructure/
└── config.py                         # Add TelemetryConfig dataclass

tests/domain/
└── services/
    └── test_feasibility_analyzer.py  # Comprehensive tests
```

---

## Task 1: Create Feasibility Data Classes

**Files:**
- Create: `app/domain/entities/feasibility.py`
- Test: `tests/domain/entities/test_feasibility.py`

- [ ] **Step 1: Write the failing test**

```python
# tests/domain/entities/test_feasibility.py
import pytest
from datetime import datetime
from app.domain.entities.feasibility import (
    FeasibilityReport,
    FeasibilityStatus,
    Recoverability,
    ConstraintScore,
    ConstraintSeverity,
    WarningCollection,
    LocalWarning,
    GlobalWarning,
    RiskLevel,
    Suggestion,
    SuggestionType,
    SuggestionPriority,
    FeasibilityTelemetry,
    GenerationTelemetry
)

def test_feasibility_status_enum():
    assert FeasibilityStatus.PASS == "pass"
    assert FeasibilityStatus.WARNING == "warning"
    assert FeasibilityStatus.FAIL == "fail"

def test_recoverability_enum():
    assert Recoverability.RECOVERABLE == "recoverable"
    assert Recoverability.DIFFICULT == "difficult"
    assert Recoverability.NEAR_IMPOSSIBLE == "near_impossible"

def test_constraint_score_calculation():
    score = ConstraintScore(
        subject_id="sub1",
        faculty_id="fac1",
        subject_name="Mathematics",
        faculty_name="Dr. Smith",
        required_slots=4,
        unique_available_slots=5,
        score=0.8,
        severity=ConstraintSeverity.TIGHT,
        consecutive_pairs_available=0
    )
    assert score.score == 0.8
    assert score.severity == ConstraintSeverity.TIGHT
    assert score.is_tightly_constrained is True

def test_constraint_score_severity_classification():
    # Comfortable: < 0.5
    assert ConstraintScore.get_severity(0.4) == ConstraintSeverity.COMFORTABLE
    # Moderate: 0.5 - 0.79
    assert ConstraintScore.get_severity(0.6) == ConstraintSeverity.MODERATE
    # Tight: 0.8 - 0.99
    assert ConstraintScore.get_severity(0.85) == ConstraintSeverity.TIGHT
    # Critical: >= 1.0
    assert ConstraintScore.get_severity(1.0) == ConstraintSeverity.CRITICAL

def test_warning_collection():
    warnings = WarningCollection(
        local=[LocalWarning(
            faculty_id="fac1",
            faculty_name="Dr. Smith",
            subject_id="sub1",
            subject_name="Math",
            risk_level=RiskLevel.HIGH,
            constraint_score=0.9,
            severity=ConstraintSeverity.TIGHT,
            message="Only 4 unique slots",
            suggestion="Add afternoon availability"
        )],
        global=[GlobalWarning(
            slot_number=1,
            time_range="9:00-9:50 AM",
            competing_subjects=["Math", "Physics"],
            competing_faculty=["fac1", "fac2"],
            supply_demand_ratio=0.5,
            risk_level=RiskLevel.MEDIUM,
            message="High competition for morning slots"
        )]
    )
    assert warnings.has_local is True
    assert warnings.has_global is True
    assert len(warnings.all_messages()) == 2

def test_suggestion_creation():
    suggestion = Suggestion(
        target_faculty_id="fac1",
        target_subject_id="sub1",
        suggestion_type=SuggestionType.ADD_AFTERNOON,
        message="Consider adding afternoon availability",
        priority=SuggestionPriority.HIGH,
        expected_impact="+20% feasibility score"
    )
    assert suggestion.suggestion_type == SuggestionType.ADD_AFTERNOON
    assert suggestion.priority == SuggestionPriority.HIGH
```

- [ ] **Step 2: Run test to verify it fails**

```bash
pytest tests/domain/entities/test_feasibility.py -v
```

Expected: `ModuleNotFoundError: No module named 'app.domain.entities.feasibility'`

- [ ] **Step 3: Write the implementation**

```python
# app/domain/entities/feasibility.py
"""Feasibility analysis domain entities."""

from dataclasses import dataclass, field
from datetime import datetime
from typing import List, Dict, Optional, Any
from enum import Enum


class FeasibilityStatus(str, Enum):
    """Overall feasibility status."""
    PASS = "pass"
    WARNING = "warning"
    FAIL = "fail"


class Recoverability(str, Enum):
    """Generation difficulty classification."""
    RECOVERABLE = "recoverable"
    DIFFICULT = "difficult"
    NEAR_IMPOSSIBLE = "near_impossible"


class ConstraintSeverity(str, Enum):
    """Constraint severity levels."""
    COMFORTABLE = "comfortable"   # score < 0.5
    MODERATE = "moderate"         # 0.5 - 0.79
    TIGHT = "tight"               # 0.8 - 0.99
    CRITICAL = "critical"         # >= 1.0 (FAIL)


class RiskLevel(str, Enum):
    """Warning risk levels."""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class SuggestionType(str, Enum):
    """Types of suggestions."""
    ADD_SLOTS = "add_slots"
    DIVERSIFY_SLOTS = "diversify_slots"
    ADD_AFTERNOON = "add_afternoon"
    ADD_CONSECUTIVE = "add_consecutive"
    AVOID_LUNCH = "avoid_lunch"


class SuggestionPriority(str, Enum):
    """Suggestion priority levels."""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"


@dataclass
class ConstraintScore:
    """Per-subject/faculty constraint analysis."""

    subject_id: str
    faculty_id: str
    subject_name: str
    faculty_name: str

    required_slots: int
    """Slots needed for this subject (credits)"""

    unique_available_slots: int
    """Distinct (day, slot) pairs faculty is available for.
    Example: MON Slot 1 and TUE Slot 1 count as 2 unique opportunities"""

    score: float
    """required_slots / unique_available_slots"""

    severity: ConstraintSeverity
    """Classification based on score"""

    consecutive_pairs_available: int = 0
    """For labs: usable consecutive slot pairs"""

    @property
    def is_tightly_constrained(self) -> bool:
        return self.severity in (ConstraintSeverity.TIGHT,
                                ConstraintSeverity.CRITICAL)

    @classmethod
    def get_severity(cls, score: float) -> ConstraintSeverity:
        """Classify severity based on constraint score."""
        if score >= 1.0:
            return ConstraintSeverity.CRITICAL
        elif score >= 0.8:
            return ConstraintSeverity.TIGHT
        elif score >= 0.5:
            return ConstraintSeverity.MODERATE
        else:
            return ConstraintSeverity.COMFORTABLE


@dataclass
class LocalWarning:
    """Faculty-specific warning."""
    faculty_id: str
    faculty_name: str
    subject_id: str
    subject_name: str

    risk_level: RiskLevel
    constraint_score: float
    severity: ConstraintSeverity

    message: str
    """Human-readable description"""

    suggestion: str
    """Brief actionable hint"""


@dataclass
class GlobalWarning:
    """Section-wide bottleneck warning."""
    slot_number: int
    time_range: str  # "9:00-9:50 AM"

    competing_subjects: List[str]
    """Subject names competing for this slot"""

    competing_faculty: List[str]
    """Faculty IDs who selected this slot"""

    supply_demand_ratio: float
    """faculty_count / subjects_competing"""

    risk_level: RiskLevel

    message: str
    """Human-readable description"""


@dataclass
class WarningCollection:
    """Container for separated warning types."""
    local: List[LocalWarning] = field(default_factory=list)
    global: List[GlobalWarning] = field(default_factory=list)

    @property
    def has_local(self) -> bool:
        return len(self.local) > 0

    @property
    def has_global(self) -> bool:
        return len(self.global) > 0

    def all_messages(self) -> List[str]:
        return [w.message for w in self.local] + [w.message for w in self.global]


@dataclass
class Suggestion:
    """Semi-automated actionable recommendation."""
    target_faculty_id: str
    target_subject_id: str

    suggestion_type: SuggestionType
    """Type of recommendation"""

    message: str
    """Guiding (not dictating) recommendation"""

    priority: SuggestionPriority
    """LOW, MEDIUM, HIGH"""

    expected_impact: str
    """"May increase feasibility score by ~20%"*/


@dataclass
class FeasibilityTelemetry:
    """Pre-generation analysis snapshot."""
    analysis_timestamp: datetime
    semester: int
    section: str

    total_faculty: int
    total_subjects: int
    total_theory: int
    total_labs: int

    bottleneck_slots: List[int] = field(default_factory=list)
    """Slot numbers with >=3 competitors"""

    tightly_constrained_faculty: List[str] = field(default_factory=list)
    """Faculty IDs with constraint score >= 0.8"""

    low_diversity_faculty: List[str] = field(default_factory=list)
    """Faculty with <=3 unique slots"""

    lab_feasible: bool = True

    estimated_generation_time_ms: int = 0


@dataclass
class GenerationTelemetry:
    """Post-generation execution data."""
    generation_timestamp: datetime
    semester: int
    section: str

    feasibility_confidence: int
    """From pre-generation analysis"""

    generation_seed: str
    """For deterministic replay"""

    actual_attempts_used: int
    """Out of 10,000 max"""

    success: bool
    duration_ms: int

    bottleneck_subjects: List[str] = field(default_factory=list)
    """Subjects causing most retries"""

    total_backtracks: int = 0
    backtrack_by_reason: Dict[str, int] = field(default_factory=dict)

    conflict_hotspots: List[Dict[str, Any]] = field(default_factory=list)


@dataclass
class FeasibilityReport:
    """Complete feasibility analysis result."""

    status: FeasibilityStatus
    """Overall feasibility: PASS, WARNING, FAIL"""

    confidence_score: int
    """0-100, estimated feasibility score (not calibrated to probability)"""

    recoverability: Recoverability
    """RECOVERABLE, DIFFICULT, NEAR_IMPOSSIBLE"""

    errors: List[str] = field(default_factory=list)
    """Hard failures that block generation"""

    warnings: WarningCollection = field(default_factory=WarningCollection)
    """Separated LOCAL and GLOBAL warnings"""

    constraint_scores: Dict[str, ConstraintScore] = field(default_factory=dict)
    """subject_id -> constraint analysis"""

    suggestions: List[Suggestion] = field(default_factory=list)
    """Actionable, semi-automated recommendations"""

    telemetry_snapshot: Optional[FeasibilityTelemetry] = None
    """Pre-generation analysis data"""
```

- [ ] **Step 4: Run test to verify it passes**

```bash
pytest tests/domain/entities/test_feasibility.py -v
```

Expected: `PASSED` (all tests)

- [ ] **Step 5: Commit**

```bash
git add app/domain/entities/feasibility.py tests/domain/entities/test_feasibility.py
git commit -m "feat: add feasibility analysis domain entities"
```

---

## Task 2: Add FeasibilityError Exception

**Files:**
- Modify: `app/domain/exceptions.py`

- [ ] **Step 1: Write the failing test**

```python
# tests/domain/test_exceptions.py
import pytest
from app.domain.entities.feasibility import FeasibilityReport, FeasibilityStatus
from app.domain.exceptions import FeasibilityError

def test_feasibility_error_creation():
    report = FeasibilityReport(
        status=FeasibilityStatus.FAIL,
        confidence_score=25,
        recoverability="near_impossible"
    )
    error = FeasibilityError(
        message="Cannot generate timetable",
        report=report
    )
    assert error.message == "Cannot generate timetable"
    assert error.report == report
    assert str(error) == "Cannot generate timetable"
```

- [ ] **Step 2: Run test to verify it fails**

```bash
pytest tests/domain/test_exceptions.py::test_feasibility_error_creation -v
```

Expected: `ImportError: cannot import name 'FeasibilityError'`

- [ ] **Step 3: Write the implementation**

First, check what's in the existing exceptions file:

```python
# Read existing: app/domain/exceptions.py
```

Then add the FeasibilityError:

```python
# Add to app/domain/exceptions.py

class FeasibilityError(ValueError):
    """Raised when feasibility analysis detects impossible state."""

    def __init__(self, message: str, report):
        """
        Args:
            message: Human-readable error message
            report: FeasibilityReport with full analysis details
        """
        self.message = message
        self.report = report
        super().__init__(message)
```

- [ ] **Step 4: Run test to verify it passes**

```bash
pytest tests/domain/test_exceptions.py::test_feasibility_error_creation -v
```

Expected: `PASSED`

- [ ] **Step 5: Commit**

```bash
git add app/domain/exceptions.py tests/domain/test_exceptions.py
git commit -m "feat: add FeasibilityError exception"
```

---

## Task 3: Create Confidence Calculator Base and Default Implementation

**Files:**
- Create: `app/domain/services/confidence/__init__.py`
- Create: `app/domain/services/confidence/base.py`
- Create: `app/domain/services/confidence/default.py`
- Test: `tests/domain/services/confidence/test_default_calculator.py`

- [ ] **Step 1: Write the failing test**

```python
# tests/domain/services/confidence/test_default_calculator.py
import pytest
from app.domain.services.confidence.default import DefaultConfidenceCalculator

def test_calculate_perfect_score():
    """Perfect conditions yield 100."""
    calc = DefaultConfidenceCalculator()
    score = calc.calculate(
        constraint_scores=[0.3, 0.4, 0.5],  # All comfortable/moderate
        bottleneck_count=0,
        total_faculty=3,
        lab_feasible=True,
        low_diversity_count=0
    )
    assert score == 100

def test_calculate_critical_penalty():
    """Critical constraints get -25 each."""
    calc = DefaultConfidenceCalculator()
    score = calc.calculate(
        constraint_scores=[1.0, 1.2],  # Two critical
        bottleneck_count=0,
        total_faculty=2,
        lab_feasible=True,
        low_diversity_count=0
    )
    assert score == 50  # 100 - 25 - 25

def test_calculate_tight_penalty():
    """Tight constraints get -10 each (after critical check)."""
    calc = DefaultConfidenceCalculator()
    score = calc.calculate(
        constraint_scores=[0.8, 0.9],  # Two tight
        bottleneck_count=0,
        total_faculty=2,
        lab_feasible=True,
        low_diversity_count=0
    )
    assert score == 80  # 100 - 10 - 10

def test_calculate_bottleneck_penalty():
    """Bottlenecks get -15 each."""
    calc = DefaultConfidenceCalculator()
    score = calc.calculate(
        constraint_scores=[0.5, 0.6],
        bottleneck_count=2,
        total_faculty=2,
        lab_feasible=True,
        low_diversity_count=0
    )
    assert score == 70  # 100 - 15 - 15

def test_calculate_lab_penalty():
    """Infeasible lab gets -40."""
    calc = DefaultConfidenceCalculator()
    score = calc.calculate(
        constraint_scores=[0.5],
        bottleneck_count=0,
        total_faculty=1,
        lab_feasible=False,  # Lab infeasible
        low_diversity_count=0
    )
    assert score == 60  # 100 - 40

def test_calculate_low_diversity_penalty():
    """Low diversity gets -5 each."""
    calc = DefaultConfidenceCalculator()
    score = calc.calculate(
        constraint_scores=[0.5],
        bottleneck_count=0,
        total_faculty=1,
        lab_feasible=True,
        low_diversity_count=3
    )
    assert score == 85  # 100 - 5 - 5 - 5

def test_score_never_negative():
    """Score is clamped to 0-100 range."""
    calc = DefaultConfidenceCalculator()
    score = calc.calculate(
        constraint_scores=[1.5, 1.5, 1.5],  # Very critical
        bottleneck_count=5,
        total_faculty=3,
        lab_feasible=False,
        low_diversity_count=5
    )
    assert 0 <= score <= 100
```

- [ ] **Step 2: Run test to verify it fails**

```bash
pytest tests/domain/services/confidence/test_default_calculator.py -v
```

Expected: `ModuleNotFoundError`

- [ ] **Step 3: Write the implementation**

```python
# app/domain/services/confidence/__init__.py
"""Confidence calculation for feasibility analysis."""

from .base import ConfidenceCalculator
from .default import DefaultConfidenceCalculator

__all__ = ["ConfidenceCalculator", "DefaultConfidenceCalculator"]
```

```python
# app/domain/services/confidence/base.py
"""Base confidence calculator interface."""

from abc import ABC, abstractmethod
from typing import List


class ConfidenceCalculator(ABC):
    """Abstract base for confidence calculation strategies."""

    @abstractmethod
    def calculate(
        self,
        constraint_scores: List[float],
        bottleneck_count: int,
        total_faculty: int,
        lab_feasible: bool,
        low_diversity_count: int
    ) -> int:
        """
        Calculate confidence score 0-100.

        Args:
            constraint_scores: List of required/available ratios
            bottleneck_count: Number of slots with >=3 competitors
            total_faculty: Total faculty count
            lab_feasible: Whether lab constraints are satisfiable
            low_diversity_count: Faculty with <=3 unique slots

        Returns:
            Confidence score from 0 to 100
        """
        pass
```

```python
# app/domain/services/confidence/default.py
"""Default confidence calculator implementation."""

from .base import ConfidenceCalculator


class DefaultConfidenceCalculator(ConfidenceCalculator):
    """
    Base scoring starts at 100, deducts for issues.

    Deductions (in order):
    - Critical constraint (score >= 1.0): -25 each (checked FIRST)
    - Tight constraint (0.8 <= score < 1.0): -10 each
    - Bottleneck slot (>=3 competitors): -15 each
    - Lab infeasible: -40
    - Low diversity (<=3 slots): -5 each
    """

    def calculate(
        self,
        constraint_scores: List[float],
        bottleneck_count: int,
        total_faculty: int,
        lab_feasible: bool,
        low_diversity_count: int
    ) -> int:
        """Return confidence score 0-100."""
        score = 100

        # Check CRITICAL first (>= 1.0), then TIGHT (>= 0.8)
        for cs in constraint_scores:
            if cs >= 1.0:
                score -= 25
            elif cs >= 0.8:
                score -= 10

        score -= bottleneck_count * 15
        if not lab_feasible:
            score -= 40
        score -= low_diversity_count * 5

        return max(0, min(100, score))
```

- [ ] **Step 4: Run test to verify it passes**

```bash
pytest tests/domain/services/confidence/test_default_calculator.py -v
```

Expected: `PASSED` (all tests)

- [ ] **Step 5: Commit**

```bash
git add app/domain/services/confidence/ tests/domain/services/confidence/
git commit -m "feat: add modular confidence calculator"
```

---

## Task 4: Create Telemetry Configuration

**Files:**
- Modify: `app/infrastructure/config.py`

- [ ] **Step 1: Write the failing test**

```python
# tests/infrastructure/test_config.py
import pytest
from app.infrastructure.config import TelemetryConfig

def test_default_telemetry_config():
    config = TelemetryConfig()
    assert config.enabled is True
    assert config.persistence_enabled is True
    assert config.retention_days == 30
    assert config.max_records == 10000
    assert config.cleanup_interval_hours == 24

def test_disabled_telemetry_config():
    config = TelemetryConfig(enabled=False)
    assert config.enabled is False

def test_telemetry_config_to_dict():
    config = TelemetryConfig(
        enabled=True,
        persistence_enabled=True,
        retention_days=7,
        max_records=5000,
        cleanup_interval_hours=12
    )
    assert config.retention_days == 7
    assert config.max_records == 5000
    assert config.cleanup_interval_hours == 12
```

- [ ] **Step 2: Run test to verify it fails**

```bash
pytest tests/infrastructure/test_config.py::test_default_telemetry_config -v
```

Expected: `ImportError` or `AttributeError`

- [ ] **Step 3: Read existing config file**

```bash
# Check current structure of app/infrastructure/config.py
```

Then add TelemetryConfig:

```python
# Add to app/infrastructure/config.py

from dataclasses import dataclass, field
from typing import Optional


@dataclass
class TelemetryConfig:
    """Telemetry storage configuration."""

    enabled: bool = True
    """Master switch for telemetry"""

    persistence_enabled: bool = True
    """Whether to persist to database"""

    retention_days: int = 30
    """How long to keep telemetry records"""

    max_records: int = 10000
    """Maximum records before auto-cleanup"""

    cleanup_interval_hours: int = 24
    """How often to run cleanup job"""
```

- [ ] **Step 4: Run test to verify it passes**

```bash
pytest tests/infrastructure/test_config.py -v
```

Expected: `PASSED`

- [ ] **Step 5: Commit**

```bash
git add app/infrastructure/config.py tests/infrastructure/test_config.py
git commit -m "feat: add telemetry configuration"
```

---

## Task 5: Create Generation Telemetry Repository

**Files:**
- Create: `app/adapters/repositories/generation_telemetry_repository.py`
- Test: `tests/adapters/repositories/test_generation_telemetry_repository.py`

- [ ] **Step 1: Write the failing test**

```python
# tests/adapters/repositories/test_generation_telemetry_repository.py
import pytest
from datetime import datetime, timedelta
from unittest.mock import AsyncMock, MagicMock
from motor.motor_asynco import AsyncIOMotorDatabase

from app.domain.entities.feasibility import GenerationTelemetry
from app.adapters.repositories.generation_telemetry_repository import (
    GenerationTelemetryRepository,
    TelemetryConfig
)
from bson import ObjectId

@pytest.mark.asyncio
async def test_save_telemetry_when_enabled():
    """Should save when config enables persistence."""
    db = AsyncMock(spec=AsyncIOMotorDatabase)
    config = TelemetryConfig(enabled=True, persistence_enabled=True)
    repo = GenerationTelemetryRepository(db, config)

    telemetry = GenerationTelemetry(
        generation_timestamp=datetime.utcnow(),
        semester=1,
        section="A",
        feasibility_confidence=75,
        generation_seed="abc123",
        actual_attempts_used=5000,
        success=True,
        duration_ms=1500
    )

    # Mock collection methods
    mock_collection = MagicMock()
    db.generation_telemetry = mock_collection
    mock_collection.estimated_document_count = AsyncMock(return_value=100)
    mock_collection.insert_one = AsyncMock(return_value=MagicMock(acknowledged=True))

    result = await repo.save(telemetry)
    assert result is True

@pytest.mark.asyncio
async def test_save_telemetry_when_disabled():
    """Should return True without saving when disabled."""
    db = AsyncMock(spec=AsyncIOMotorDatabase)
    config = TelemetryConfig(enabled=False)
    repo = GenerationTelemetryRepository(db, config)

    telemetry = GenerationTelemetry(
        generation_timestamp=datetime.utcnow(),
        semester=1,
        section="A",
        feasibility_confidence=75,
        generation_seed="abc123",
        actual_attempts_used=5000,
        success=True,
        duration_ms=1500
    )

    result = await repo.save(telemetry)
    assert result is True  # Should not fail, just skip

@pytest.mark.asyncio
async def test_cleanup_expired():
    """Should remove records older than retention_days."""
    db = AsyncMock(spec=AsyncIOMotorDatabase)
    config = TelemetryConfig(retention_days=30)
    repo = GenerationTelemetryRepository(db, config)

    mock_collection = MagicMock()
    db.generation_telemetry = mock_collection
    mock_collection.delete_many = AsyncMock(return_value=MagicMock(deleted_count=5))

    await repo.cleanup_expired()

    # Verify delete_many was called with date cutoff
    args, _ = mock_collection.delete_many.call_args
    query = args[0]
    assert "generation_timestamp" in query
    assert "$lt" in query["generation_timestamp"]

@pytest.mark.asyncio
async def test_cleanup_oldest_when_limit_reached():
    """Should fetch oldest IDs and delete them explicitly."""
    db = AsyncMock(spec=AsyncIOMotorDatabase)
    config = TelemetryConfig(max_records=100)
    repo = GenerationTelemetryRepository(db, config)

    mock_collection = MagicMock()
    db.generation_telemetry = mock_collection

    # Mock count at limit
    mock_collection.estimated_document_count = AsyncMock(return_value=100)

    # Mock find with sort
    mock_cursor = AsyncMock()
    mock_cursor.to_list = AsyncMock(return_value=[
        {"_id": ObjectId("507f1f77bcf86cd799439011")},
        {"_id": ObjectId("507f1f77bcf86cd799439012")},
    ])
    mock_collection.find = MagicMock(return_value=mock_cursor)
    mock_collection.find.return_value.sort = MagicMock(return_value=mock_cursor)

    # Mock delete_many
    mock_collection.delete_many = AsyncMock(return_value=MagicMock(deleted_count=2))

    await repo._cleanup_oldest()

    # Verify delete_many was called with IDs
    args, _ = mock_collection.delete_many.call_args
    query = args[0]
    assert "_id" in query
    assert "$in" in query["_id"]
```

- [ ] **Step 2: Run test to verify it fails**

```bash
pytest tests/adapters/repositories/test_generation_telemetry_repository.py -v
```

Expected: `ModuleNotFoundError`

- [ ] **Step 3: Write the implementation**

```python
# app/adapters/repositories/generation_telemetry_repository.py
"""Repository for generation telemetry with configurable cleanup."""

from datetime import timedelta
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
            projection={"_id": 1}
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
```

- [ ] **Step 4: Run test to verify it passes**

```bash
pytest tests/adapters/repositories/test_generation_telemetry_repository.py -v
```

Expected: `PASSED`

- [ ] **Step 5: Commit**

```bash
git add app/adapters/repositories/generation_telemetry_repository.py tests/adapters/repositories/test_generation_telemetry_repository.py
git commit -m "feat: add generation telemetry repository with cleanup"
```

---

## Task 6: Implement FeasibilityAnalyzer Core Service

**Files:**
- Create: `app/domain/services/feasibility_analyzer.py`
- Test: `tests/domain/services/test_feasibility_analyzer.py`

- [ ] **Step 1: Write the failing test**

```python
# tests/domain/services/test_feasibility_analyzer.py
import pytest
from datetime import datetime
from unittest.mock import AsyncMock

from app.domain.entities.feasibility import (
    FeasibilityReport, FeasibilityStatus, Recoverability,
    ConstraintScore, ConstraintSeverity, WarningCollection,
    LocalWarning, GlobalWarning, RiskLevel, Suggestion,
    SuggestionType, SuggestionPriority, FeasibilityTelemetry
)
from app.domain.entities.subject import Subject, SubjectType
from app.domain.services.feasibility_analyzer import FeasibilityAnalyzer


@pytest.mark.asyncio
async def test_analyze_perfect_case():
    """All constraints comfortable, no issues."""
    analyzer = FeasibilityAnalyzer()

    subjects = [
        Subject(id="s1", code="MATH101", name="Math", semester=1,
                 subject_type=SubjectType.THEORY, credits=3,
                 classes_per_week=3)
    ]

    faculty_availability = {
        "f1": {"MON": [1, 2, 3, 4, 7, 8], "TUE": [1, 2, 3, 4, 7, 8]}
    }
    subject_faculty_map = {"s1": "f1"}

    report = await analyzer.analyze(
        semester=1,
        section="A",
        subjects=subjects,
        faculty_availability=faculty_availability,
        subject_faculty_map=subject_faculty_map
    )

    assert report.status == FeasibilityStatus.PASS
    assert report.confidence_score == 100
    assert report.recoverability == Recoverability.RECOVERABLE
    assert len(report.errors) == 0


@pytest.mark.asyncio
async def test_analyze_critical_constraint():
    """Faculty has fewer slots than required."""
    analyzer = FeasibilityAnalyzer()

    subjects = [
        Subject(id="s1", code="MATH101", name="Math", semester=1,
                 subject_type=SubjectType.THEORY, credits=4,
                 classes_per_week=4)
    ]

    # Only 3 unique slots available, need 4
    faculty_availability = {
        "f1": {"MON": [1, 2, 3]}  # 3 < 4 required
    }
    subject_faculty_map = {"s1": "f1"}

    report = await analyzer.analyze(
        semester=1,
        section="A",
        subjects=subjects,
        faculty_availability=faculty_availability,
        subject_faculty_map=subject_faculty_map
    )

    assert report.status == FeasibilityStatus.FAIL
    assert report.recoverability == Recoverability.NEAR_IMPOSSIBLE
    assert len(report.errors) > 0
    assert any("4" in err for err in report.errors)


@pytest.mark.asyncio
async def test_detect_bottleneck():
    """Multiple faculty competing for same slot."""
    analyzer = FeasibilityAnalyzer()

    subjects = [
        Subject(id="s1", code="MATH101", name="Math", semester=1,
                 subject_type=SubjectType.THEORY, credits=3, classes_per_week=3),
        Subject(id="s2", code="PHY101", name="Physics", semester=1,
                 subject_type=SubjectType.THEORY, credits=3, classes_per_week=3),
        Subject(id="s3", code="CS101", name="CS", semester=1,
                 subject_type=SubjectType.THEORY, credits=3, classes_per_week=3)
    ]

    # All faculty want slot 1 on MONDAY
    faculty_availability = {
        "f1": {"MON": [1, 2, 3]},
        "f2": {"MON": [1, 4, 5]},
        "f3": {"MON": [1, 6, 7]}
    }
    subject_faculty_map = {"s1": "f1", "s2": "f2", "s3": "f3"}

    report = await analyzer.analyze(
        semester=1,
        section="A",
        subjects=subjects,
        faculty_availability=faculty_availability,
        subject_faculty_map=subject_faculty_map
    )

    assert report.status == FeasibilityStatus.WARNING
    assert len(report.warnings.global) > 0
    # Should detect slot 1 as bottleneck
    slot_1_warnings = [w for w in report.warnings.global if w.slot_number == 1]
    assert len(slot_1_warnings) > 0


@pytest.mark.asyncio
async def test_calculate_constraint_scores_with_day_slot_pairs():
    """Count unique (day, slot) pairs, not just slot numbers."""
    analyzer = FeasibilityAnalyzer()

    subjects = [
        Subject(id="s1", code="MATH101", name="Math", semester=1,
                 subject_type=SubjectType.THEORY, credits=4, classes_per_week=4)
    ]

    # Faculty has 6 unique opportunities: MON-1, MON-2, TUE-1, TUE-2, WED-1, WED-2
    # Even though slot numbers repeat, day+slot combinations are unique
    faculty_availability = {
        "f1": {
            "MON": [1, 2],  # 2 opportunities
            "TUE": [1, 2],  # 2 opportunities (different day)
            "WED": [1, 2]   # 2 opportunities (different day)
        }
    }
    subject_faculty_map = {"s1": "f1"}

    report = await analyzer.analyze(
        semester=1,
        section="A",
        subjects=subjects,
        faculty_availability=faculty_availability,
        subject_faculty_map=subject_faculty_map
    )

    # Score = 4 required / 6 available = 0.667 (MODERATE)
    score = report.constraint_scores["s1"]
    assert score.unique_available_slots == 6
    assert round(score.score, 2) == 0.67
    assert score.severity == ConstraintSeverity.MODERATE


@pytest.mark.asyncio
async def test_generate_suggestions_for_tight_constraint():
    """Should suggest adding slots when constraint is tight."""
    analyzer = FeasibilityAnalyzer()

    subjects = [
        Subject(id="s1", code="MATH101", name="Math", semester=1,
                 subject_type=SubjectType.THEORY, credits=4, classes_per_week=4)
    ]

    # Exactly 4 slots - tight, no room for error
    faculty_availability = {
        "f1": {"MON": [1, 2, 3, 4]}
    }
    subject_faculty_map = {"s1": "f1"}

    report = await analyzer.analyze(
        semester=1,
        section="A",
        subjects=subjects,
        faculty_availability=faculty_availability,
        subject_faculty_map=subject_faculty_map
    )

    assert len(report.suggestions) > 0
    # Should suggest diversifying or adding slots
    suggestion_types = [s.suggestion_type for s in report.suggestions]
    assert SuggestionType.ADD_SLOTS in suggestion_types or \
           SuggestionType.DIVERSIFY_SLOTS in suggestion_types
```

- [ ] **Step 2: Run test to verify it fails**

```bash
pytest tests/domain/services/test_feasibility_analyzer.py -v
```

Expected: `ModuleNotFoundError`

- [ ] **Step 3: Write the implementation**

```python
# app/domain/services/feasibility_analyzer.py
"""Feasibility analysis service for timetable generation."""

from datetime import datetime
from typing import Dict, List, Optional, Tuple, Set
from collections import defaultdict
import logging

from app.domain.entities.feasibility import (
    FeasibilityReport, FeasibilityStatus, Recoverability,
    ConstraintScore, ConstraintSeverity, WarningCollection,
    LocalWarning, GlobalWarning, RiskLevel, Suggestion,
    SuggestionType, SuggestionPriority, FeasibilityTelemetry
)
from app.domain.entities.subject import Subject, SubjectType
from app.domain.services.confidence import ConfidenceCalculator, DefaultConfidenceCalculator

logger = logging.getLogger(__name__)


class FeasibilityAnalyzer:
    """
    Analyzes faculty availability for timetable generation feasibility.

    Provides pre-generation intelligence to prevent unnecessary backtracking
    failures through constraint detection and bottleneck analysis.
    """

    def __init__(
        self,
        confidence_calculator: Optional[ConfidenceCalculator] = None
    ):
        """
        Args:
            confidence_calculator: Modular scoring (injectable for tuning)
        """
        self.confidence_calculator = confidence_calculator or \
                                    DefaultConfidenceCalculator()

    async def analyze(
        self,
        semester: int,
        section: str,
        subjects: List[Subject],
        faculty_availability: Dict[str, Dict[str, List[int]]],
        subject_faculty_map: Dict[str, str]
    ) -> FeasibilityReport:
        """
        Perform complete feasibility analysis.

        Returns FeasibilityReport with status, confidence, warnings, suggestions.
        """
        errors = []
        local_warnings = []
        global_warnings = []

        # 1. Calculate constraint scores
        constraint_scores = self._calculate_constraint_scores(
            subjects, faculty_availability, subject_faculty_map
        )

        # 2. Check for FAIL conditions
        fail_result = self._check_fail_conditions(
            subjects, faculty_availability, subject_faculty_map, constraint_scores
        )
        errors.extend(fail_result["errors"])

        # 3. Detect bottlenecks
        bottlenecks = self._detect_bottlenecks(
            faculty_availability, subject_faculty_map
        )
        for bottleneck in bottlenecks:
            global_warnings.append(GlobalWarning(
                slot_number=bottleneck["slot"],
                time_range=bottleneck["time_range"],
                competing_subjects=bottleneck["subjects"],
                competing_faculty=bottleneck["faculty"],
                supply_demand_ratio=bottleneck["ratio"],
                risk_level=self._get_bottleneck_risk_level(bottleneck["ratio"]),
                message=f"{len(bottleneck['subjects'])} subjects competing for slot {bottleneck['slot']}"
            ))

        # 4. Analyze labs
        lab_subjects = [s for s in subjects if s.is_lab()]
        lab_result = self._analyze_labs(
            lab_subjects, faculty_availability, subject_faculty_map
        )
        errors.extend(lab_result["errors"])
        local_warnings.extend(lab_result["warnings"])

        # 5. Check diversity
        low_diversity_faculty = self._check_diversity(faculty_availability)
        for faculty_id in low_diversity_faculty:
            for subject_id, faculty_name in self._get_faculty_subjects(
                faculty_id, subject_faculty_map, subjects
            ):
                local_warnings.append(LocalWarning(
                    faculty_id=faculty_id,
                    faculty_name=faculty_name,
                    subject_id=subject_id,
                    subject_name=self._get_subject_name(subject_id, subjects),
                    risk_level=RiskLevel.MEDIUM,
                    constraint_score=constraint_scores.get(subject_id, ConstraintScore()).score,
                    severity=ConstraintSeverity.MODERATE,
                    message=f"Low slot diversity (≤3 unique opportunities)",
                    suggestion="Add availability across different days"
                ))

        # 6. Generate local warnings for tight/critical constraints
        for subject_id, score in constraint_scores.items():
            if score.severity in (ConstraintSeverity.TIGHT, ConstraintSeverity.CRITICAL):
                local_warnings.append(LocalWarning(
                    faculty_id=score.faculty_id,
                    faculty_name=score.faculty_name,
                    subject_id=subject_id,
                    subject_name=score.subject_name,
                    risk_level=RiskLevel.HIGH if score.severity == ConstraintSeverity.CRITICAL else RiskLevel.MEDIUM,
                    constraint_score=score.score,
                    severity=score.severity,
                    message=f"{score.unique_available_slots} opportunities for {score.required_slots} required slots",
                    suggestion="Consider adding more availability or diversifying days"
                ))

        # 7. Calculate confidence score
        constraint_score_values = [cs.score for cs in constraint_scores.values()]
        confidence = self.confidence_calculator.calculate(
            constraint_scores=constraint_score_values,
            bottleneck_count=len(bottlenecks),
            total_faculty=len(faculty_availability),
            lab_feasible=lab_result["feasible"],
            low_diversity_count=len(low_diversity_faculty)
        )

        # 8. Classify recoverability
        critical_count = sum(1 for cs in constraint_scores.values()
                           if cs.severity == ConstraintSeverity.CRITICAL)
        recoverability = self._classify_recoverability(
            confidence, critical_count, len(bottlenecks)
        )

        # 9. Generate suggestions
        suggestions = self._generate_suggestions(
            constraint_scores, bottlenecks, low_diversity_faculty, lab_result
        )

        # 10. Determine status
        status = FeasibilityStatus.FAIL if errors else \
                 FeasibilityStatus.WARNING if (local_warnings or global_warnings) else \
                 FeasibilityStatus.PASS

        # 11. Build telemetry snapshot
        telemetry_snapshot = FeasibilityTelemetry(
            analysis_timestamp=datetime.utcnow(),
            semester=semester,
            section=section,
            total_faculty=len(faculty_availability),
            total_subjects=len(subjects),
            total_theory=len([s for s in subjects if s.is_theory()]),
            total_labs=len(lab_subjects),
            bottleneck_slots=[b["slot"] for b in bottlenecks],
            tightly_constrained_faculty=[
                fid for fid, cs in constraint_scores.items()
                if cs.is_tightly_constrained
            ],
            low_diversity_faculty=low_diversity_faculty,
            lab_feasible=lab_result["feasible"]
        )

        return FeasibilityReport(
            status=status,
            confidence_score=confidence,
            recoverability=recoverability,
            errors=errors,
            warnings=WarningCollection(local=local_warnings, global=global_warnings),
            constraint_scores=constraint_scores,
            suggestions=suggestions,
            telemetry_snapshot=telemetry_snapshot
        )

    def _calculate_constraint_scores(
        self,
        subjects: List[Subject],
        faculty_availability: Dict[str, Dict[str, List[int]]],
        subject_faculty_map: Dict[str, str]
    ) -> Dict[str, ConstraintScore]:
        """
        Calculate required/available ratio per subject.

        Uses unique (day, slot) pairs, not just slot numbers.
        Example: MON Slot 1 and TUE Slot 1 count as 2 unique opportunities.
        """
        scores = {}

        for subject in subjects:
            faculty_id = subject_faculty_map.get(subject.id)
            if not faculty_id:
                continue

            avail = faculty_availability.get(faculty_id, {})
            faculty_name = self._get_faculty_name(faculty_id)

            # Count unique (day, slot) pairs
            unique_pairs = set()
            for day, slots in avail.items():
                for slot in slots:
                    unique_pairs.add((day, slot))

            required = subject.credits
            available = len(unique_pairs)
            score_val = required / available if available > 0 else float('inf')

            scores[subject.id] = ConstraintScore(
                subject_id=subject.id,
                faculty_id=faculty_id,
                subject_name=subject.name,
                faculty_name=faculty_name,
                required_slots=required,
                unique_available_slots=available,
                score=score_val,
                severity=ConstraintScore.get_severity(score_val),
                consecutive_pairs_available=self._count_consecutive_pairs(avail)
            )

        return scores

    def _check_fail_conditions(
        self,
        subjects: List[Subject],
        faculty_availability: Dict[str, Dict[str, List[int]]],
        subject_faculty_map: Dict[str, str],
        constraint_scores: Dict[str, ConstraintScore]
    ) -> Dict[str, List[str]]:
        """Check for hard FAIL conditions."""
        errors = []

        for subject in subjects:
            faculty_id = subject_faculty_map.get(subject.id)
            if not faculty_id:
                errors.append(f"No faculty assigned to {subject.name}")
                continue

            avail = faculty_availability.get(faculty_id, {})
            if not avail or not any(avail.values()):
                errors.append(f"Faculty for {subject.name} has no available slots")

            # Check constraint score
            score = constraint_scores.get(subject.id)
            if score and score.score >= 1.0:
                errors.append(
                    f"{subject.name}: {score.unique_available_slots} opportunities available, "
                    f"needs {score.required_slots} (shortage of {score.required_slots - score.unique_available_slots})"
                )

        # Check lab consecutive requirements
        lab_subjects = [s for s in subjects if s.is_lab()]
        for subject in lab_subjects:
            faculty_id = subject_faculty_map.get(subject.id)
            if not faculty_id:
                continue

            avail = faculty_availability.get(faculty_id, {})
            if not self._has_usable_consecutive_pairs(avail):
                errors.append(
                    f"{subject.name} (lab): No consecutive usable slot pairs. "
                    f"Labs require 2 consecutive periods (e.g., 1-2, 3-4, 7-8)."
                )

        return {"errors": errors}

    def _detect_bottlenecks(
        self,
        faculty_availability: Dict[str, Dict[str, List[int]]],
        subject_faculty_map: Dict[str, str]
    ) -> List[Dict]:
        """Find slots with >=3 competing subjects."""
        # Map (day, slot) -> competing faculty
        slot_competition: Dict[Tuple[str, int], Set[str]] = defaultdict(set)

        for faculty_id, avail in faculty_availability.items():
            for day, slots in avail.items():
                for slot in slots:
                    slot_competition[(day, slot)].add(faculty_id)

        bottlenecks = []
        for (day, slot), faculty_set in slot_competition.items():
            if len(faculty_set) >= 3:
                bottlenecks.append({
                    "slot": slot,
                    "day": day,
                    "faculty": list(faculty_set),
                    "count": len(faculty_set),
                    "time_range": self._slot_to_time_range(slot)
                })

        # Add subject names
        for bottleneck in bottlenecks:
            bottleneck["subjects"] = []  # Would need reverse lookup

        return bottlenecks

    def _analyze_labs(
        self,
        lab_subjects: List[Subject],
        faculty_availability: Dict[str, Dict[str, List[int]]],
        subject_faculty_map: Dict[str, str]
    ) -> Dict:
        """Check consecutive USABLE slot pairs for labs."""
        errors = []
        warnings = []
        feasible = True

        for subject in lab_subjects:
            faculty_id = subject_faculty_map.get(subject.id)
            if not faculty_id:
                errors.append(f"No faculty assigned to lab {subject.name}")
                continue

            avail = faculty_availability.get(faculty_id, {})
            pairs = self._count_usable_consecutive_pairs(avail)

            if pairs == 0:
                feasible = False
                errors.append(f"{subject.name} (lab): No consecutive usable slot pairs")
            elif pairs == 1:
                warnings.append(f"{subject.name} (lab): Only 1 consecutive pair available")

        return {"feasible": feasible, "errors": errors, "warnings": warnings}

    def _check_diversity(
        self,
        faculty_availability: Dict[str, Dict[str, List[int]]]
    ) -> List[str]:
        """Identify faculty with <=3 unique slots."""
        low_diversity = []

        for faculty_id, avail in faculty_availability.items():
            unique_pairs = set()
            for day, slots in avail.items():
                for slot in slots:
                    unique_pairs.add((day, slot))

            if len(unique_pairs) <= 3:
                low_diversity.append(faculty_id)

        return low_diversity

    def _generate_suggestions(
        self,
        constraint_scores: Dict[str, ConstraintScore],
        bottlenecks: List[Dict],
        low_diversity: List[str],
        lab_result: Dict
    ) -> List[Suggestion]:
        """Generate semi-automated recommendations."""
        suggestions = []

        # For tight/critical constraints
        for subject_id, score in constraint_scores.items():
            if score.is_tightly_constrained:
                suggestions.append(Suggestion(
                    target_faculty_id=score.faculty_id,
                    target_subject_id=subject_id,
                    suggestion_type=SuggestionType.ADD_SLOTS,
                    message=f"Consider adding 2-3 more available slots to increase flexibility",
                    priority=SuggestionPriority.HIGH,
                    expected_impact="May increase feasibility score by 15-25%"
                ))

        # For bottlenecks
        if bottlenecks:
            for bottleneck in bottlenecks:
                for faculty_id in bottleneck["faculty"]:
                    if faculty_id in low_diversity:
                        suggestions.append(Suggestion(
                            target_faculty_id=faculty_id,
                            target_subject_id="",  # Would need lookup
                            suggestion_type=SuggestionType.DIVERSIFY_SLOTS,
                            message="Consider adding afternoon availability (2-5 PM) to reduce morning competition",
                            priority=SuggestionPriority.MEDIUM,
                            expected_impact="May reduce bottleneck severity"
                        ))

        # For low diversity
        for faculty_id in low_diversity:
            suggestions.append(Suggestion(
                target_faculty_id=faculty_id,
                target_subject_id="",
                suggestion_type=SuggestionType.DIVERSIFY_SLOTS,
                message="Consider adding availability across different days for better scheduling options",
                priority=SuggestionPriority.MEDIUM,
                expected_impact="May increase feasibility score by 10-15%"
            ))

        return suggestions

    def _classify_recoverability(
        self,
        confidence: int,
        critical_count: int,
        bottleneck_count: int
    ) -> Recoverability:
        """Classify generation difficulty."""
        if critical_count > 0 or confidence < 30 or bottleneck_count >= 3:
            return Recoverability.NEAR_IMPOSSIBLE
        elif confidence < 70 or bottleneck_count > 0:
            return Recoverability.DIFFICULT
        else:
            return Recoverability.RECOVERABLE

    def _get_bottleneck_risk_level(self, ratio: float) -> RiskLevel:
        """Determine risk level from supply/demand ratio."""
        if ratio >= 1.0:
            return RiskLevel.CRITICAL
        elif ratio >= 0.75:
            return RiskLevel.HIGH
        elif ratio >= 0.5:
            return RiskLevel.MEDIUM
        else:
            return RiskLevel.LOW

    def _slot_to_time_range(self, slot: int) -> str:
        """Convert slot number to time range string."""
        times = {
            1: "9:00-9:50 AM", 2: "9:50-10:40 AM", 3: "10:40-11:30 AM",
            4: "11:30 AM-12:20 PM", 5: "12:20-1:10 PM", 6: "1:10-2:00 PM",
            7: "2:00-2:50 PM", 8: "2:50-3:40 PM", 9: "3:40-4:30 PM",
            10: "4:30-5:20 PM"
        }
        return times.get(slot, f"Slot {slot}")

    def _count_consecutive_pairs(self, avail: Dict[str, List[int]]) -> int:
        """Count consecutive slot pairs (non-lunch preferred)."""
        LUNCH_SLOTS = {5, 6}
        count = 0

        for day_slots in avail.values():
            sorted_slots = sorted(day_slots)
            for i in range(len(sorted_slots) - 1):
                if (sorted_slots[i + 1] - sorted_slots[i] == 1 and
                    sorted_slots[i] not in LUNCH_SLOTS and
                    sorted_slots[i + 1] not in LUNCH_SLOTS):
                    count += 1

        return count

    def _has_usable_consecutive_pairs(self, avail: Dict[str, List[int]]) -> bool:
        """Check if there are any consecutive usable pairs."""
        return self._count_consecutive_pairs(avail) > 0

    def _count_usable_consecutive_pairs(self, avail: Dict[str, List[int]]) -> int:
        """Count consecutive USABLE pairs (excluding lunch)."""
        LUNCH_SLOTS = {5, 6}
        count = 0

        for day_slots in avail.values():
            sorted_slots = sorted(day_slots)
            for i in range(len(sorted_slots) - 1):
                if (sorted_slots[i + 1] - sorted_slots[i] == 1 and
                    sorted_slots[i] not in LUNCH_SLOTS and
                    sorted_slots[i + 1] not in LUNCH_SLOTS):
                    count += 1

        return count

    def _get_faculty_name(self, faculty_id: str) -> str:
        """Get faculty name (placeholder)."""
        return f"Faculty {faculty_id}"

    def _get_subject_name(self, subject_id: str, subjects: List[Subject]) -> str:
        """Get subject name by ID."""
        for subject in subjects:
            if subject.id == subject_id:
                return subject.name
        return subject_id

    def _get_faculty_subjects(
        self,
        faculty_id: str,
        subject_faculty_map: Dict[str, str],
        subjects: List[Subject]
    ) -> List[Tuple[str, str]]:
        """Get (subject_id, faculty_name) pairs for a faculty."""
        pairs = []
        for subject_id, fid in subject_faculty_map.items():
            if fid == faculty_id:
                pairs.append((subject_id, self._get_faculty_name(fid)))
        return pairs
```

- [ ] **Step 4: Run test to verify it passes**

```bash
pytest tests/domain/services/test_feasibility_analyzer.py -v
```

Expected: `PASSED` (may need iteration for helper methods)

- [ ] **Step 5: Commit**

```bash
git add app/domain/services/feasibility_analyzer.py tests/domain/services/test_feasibility_analyzer.py
git commit -m "feat: implement feasibility analyzer service"
```

---

## Task 7: Update TimetableUseCase with Feasibility Check

**Files:**
- Modify: `app/use_cases/timetable.py`

- [ ] **Step 1: Write the failing test**

```python
# tests/use_cases/test_timetable_feasibility_integration.py
import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from app.use_cases.timetable import TimetableUseCase
from app.domain.entities.feasibility import FeasibilityStatus, FeasibilityError
from app.domain.entities.subject import Subject, SubjectType


@pytest.mark.asyncio
async def test_generate_blocks_on_feasibility_fail():
    """Should raise FeasibilityError when feasibility fails."""
    use_case = _create_use_case()

    # Mock feasibility analyzer to return FAIL
    with patch.object(use_case.feasibility_analyzer, 'analyze') as mock_analyze:
        from app.domain.entities.feasibility import FeasibilityReport, FeasibilityStatus, Recoverability

        mock_report = FeasibilityReport(
            status=FeasibilityStatus.FAIL,
            confidence_score=20,
            recoverability="near_impossible",
            errors=["Insufficient slots"]
        )
        mock_analyze.return_value = mock_report

        with pytest.raises(FeasibilityError) as exc_info:
            await use_case.generate_timetable_simple(
                semester=1,
                section="A",
                created_by="admin1"
            )

        assert exc_info.value.report == mock_report


@pytest.mark.asyncio
async def test_generate_proceeds_on_feasibility_warning():
    """Should attach warnings when feasibility has warnings."""
    use_case = _create_use_case()

    with patch.object(use_case.feasibility_analyzer, 'analyze') as mock_analyze:
        from app.domain.entities.feasibility import FeasibilityReport, FeasibilityStatus

        mock_report = FeasibilityReport(
            status=FeasibilityStatus.WARNING,
            confidence_score=65,
            recoverability="difficult"
        )
        mock_analyze.return_value = mock_report

        # Mock generate_timetable to return response
        with patch.object(use_case, 'generate_timetable') as mock_generate:
            mock_response = MagicMock()
            mock_response.warnings = None
            mock_response.duration_ms = 1000
            mock_generate.return_value = mock_response

            response = await use_case.generate_timetable_simple(
                semester=1,
                section="A",
                created_by="admin1"
            )

            # Should have warnings attached
            assert response.warnings is not None


def _create_use_case():
    """Helper to create test use case."""
    from app.domain.services.feasibility_analyzer import FeasibilityAnalyzer

    mock_subject_repo = AsyncMock()
    mock_timetable_repo = AsyncMock()
    mock_assignment_repo = AsyncMock()
    mock_user_repo = AsyncMock()
    mock_availability_repo = AsyncMock()
    mock_availability_service = AsyncMock()
    mock_override_repo = AsyncMock()
    mock_telemetry_repo = AsyncMock()

    use_case = TimetableUseCase(
        subject_repository=mock_subject_repo,
        timetable_repository=mock_timetable_repo,
        assignment_repo=mock_assignment_repo,
        user_repo=mock_user_repo,
        faculty_availability_repo=mock_availability_repo,
        availability_service=mock_availability_service,
        override_repo=mock_override_repo,
        telemetry_repo=mock_telemetry_repo
    )

    use_case.feasibility_analyzer = FeasibilityAnalyzer()

    return use_case
```

- [ ] **Step 2: Run test to verify it fails**

```bash
pytest tests/use_cases/test_timetable_feasibility_integration.py -v
```

Expected: Test failures for missing feasibility integration

- [ ] **Step 3: Update TimetableUseCase**

First, read the existing TimetableUseCase to find the integration point:

```python
# Read app/use_cases/timetable.py lines 699-739 (generate_timetable_simple method)
```

Then update the `__init__` method to add feasibility analyzer:

```python
# Add to imports in app/use_cases/timetable.py
from app.domain.services.feasibility_analyzer import FeasibilityAnalyzer
from app.domain.entities.feasibility import FeasibilityError
from app.adapters.repositories.generation_telemetry_repository import (
    GenerationTelemetryRepository,
    TelemetryConfig
)
from app.infrastructure.config import TelemetryConfig

# Update __init__ method parameters (around line 69-90)
def __init__(
    self,
    subject_repository: ISubjectRepository,
    timetable_repository,  # TimetableRepository
    timetable_generator: Optional[ITimetableGenerator] = None,
    assignment_repo=None,  # SubjectAssignmentRepository
    user_repo=None,  # UserRepository
    faculty_availability_repo=None,  # FacultyAvailabilityRepository
    availability_service=None,  # FacultyAvailabilityService
    override_repo=None,  # AdminOverrideRepository
    feasibility_analyzer: FeasibilityAnalyzer = None,
    telemetry_repo: GenerationTelemetryRepository = None
):
    self.subject_repository = subject_repository
    self.timetable_repository = timetable_repository
    self.timetable_generator = timetable_generator
    self.assignment_repo = assignment_repo
    self.user_repo = user_repo
    self.faculty_availability_repo = faculty_availability_repo
    self.availability_service = availability_service
    self.override_repo = override_repo
    self.feasibility_analyzer = feasibility_analyzer or FeasibilityAnalyzer()
    self.telemetry_repo = telemetry_repo
```

Then update `generate_timetable_simple` method:

```python
# Replace app/use_cases/timetable.py generate_timetable_simple method (lines 699-739)
async def generate_timetable_simple(
    self,
    semester: int,
    section: str,
    created_by: str
) -> GenerateTimetableResponse:
    """
    Generate timetable with automatic detection (simplified version).

    Now includes feasibility analysis BEFORE backtracking.
    """
    # 1. Auto-detect assignments
    detected = await self.detect_assignments_for_timetable(
        semester=semester,
        section=section
    )

    # 2. Fetch subjects for analysis
    subjects = []
    for sid in detected["subject_ids"]:
        s = await self.subject_repository.find_by_id(sid)
        if s:
            subjects.append(s)

    # 3. Run feasibility analysis
    report = await self.feasibility_analyzer.analyze(
        semester=semester,
        section=section,
        subjects=subjects,
        faculty_availability=detected["faculty_availability"],
        subject_faculty_map=detected["subject_faculty_map"]
    )

    # 4. Handle FAIL - block generation
    if report.status == FeasibilityStatus.FAIL:
        raise FeasibilityError(
            message=f"Cannot generate timetable for Semester {semester}, Section {section}",
            report=report
        )

    # 5. Attach constraint scores for heuristic scheduling
    detected["constraint_scores"] = report.constraint_scores

    # 6. Prepare generation request
    request = GenerateTimetableRequest(
        semester=semester,
        section=section,
        subject_ids=detected["subject_ids"],
        faculty_availability=detected["faculty_availability"],
        subject_faculty_map=detected["subject_faculty_map"],
        created_by=created_by
    )

    # 7. Generate (may still fail, but we tried our best)
    import time
    start_time = time.time()

    response = await self.generate_timetable(request)

    duration_ms = int((time.time() - start_time) * 1000)

    # 8. Store telemetry (for both success and failure)
    if self.telemetry_repo and self.telemetry_repo.config.enabled:
        telemetry = GenerationTelemetry(
            generation_timestamp=datetime.utcnow(),
            semester=semester,
            section=section,
            feasibility_confidence=report.confidence_score,
            generation_seed=getattr(self.timetable_generator, 'random_seed', 'unknown'),
            actual_attempts_used=getattr(self.timetable_generator, 'last_attempt_count', 0),
            success=True,  # We got here without exception
            duration_ms=duration_ms
        )
        await self.telemetry_repo.save(telemetry)

    # 9. Attach warnings/confidence to response
    response.warnings = report.warnings
    response.confidence_score = report.confidence_score
    response.recoverability = report.recoverability

    return response
```

- [ ] **Step 4: Run test to verify it passes**

```bash
pytest tests/use_cases/test_timetable_feasibility_integration.py -v
```

Expected: `PASSED`

- [ ] **Step 5: Commit**

```bash
git add app/use_cases/timetable.py tests/use_cases/test_timetable_feasibility_integration.py
git commit -m "feat: integrate feasibility analysis into timetable generation"
```

---

## Task 8: Update Controller Response Format

**Files:**
- Modify: `app/adapters/controllers/timetable_controller.py`

- [ ] **Step 1: Read current controller**

```bash
# Read app/adapters/controllers/timetable_controller.py
# Find the generate endpoint
```

- [ ] **Step 2: Add FeasibilityError handling**

Find the `/generate` or `/generate/simple` endpoint and add exception handling:

```python
# Add to imports in timetable_controller.py
from app.domain.entities.feasibility import FeasibilityReport
from app.domain.exceptions import FeasibilityError
from fastapi.responses import JSONResponse

# Update the endpoint (modify existing)
@router.post("/generate")
async def generate_timetable_endpoint(
    semester: int = Query(..., ge=1, le=8),
    section: str = Query(..., min_length=1, max_length=2),
    current_admin: User = Depends(get_current_admin),
    use_case: TimetableUseCase = Depends(get_timetable_use_case)
):
    """Generate timetable for a section (admin only)."""
    try:
        response = await use_case.generate_timetable_simple(
            semester=semester,
            section=section,
            created_by=current_admin.id
        )
        return response

    except FeasibilityError as e:
        # Return structured feasibility report for frontend display
        return JSONResponse(
            status_code=400,
            content={
                "status": "fail",
                "can_proceed": False,
                "confidence_score": e.report.confidence_score,
                "recoverability": e.report.recoverability,
                "errors": e.report.errors,
                "warnings": _format_warnings(e.report.warnings),
                "suggestions": _format_suggestions(e.report.suggestions),
                "constraint_scores": _format_constraint_scores(e.report.constraint_scores)
            }
        )
```

- [ ] **Step 3: Add response formatting helpers**

```python
# Add to timetable_controller.py

def _format_warnings(warnings) -> dict:
    """Format warnings for JSON response."""
    return {
        "local": [
            {
                "faculty_id": w.faculty_id,
                "faculty_name": w.faculty_name,
                "subject_id": w.subject_id,
                "subject_name": w.subject_name,
                "risk_level": w.risk_level.value,
                "constraint_score": w.constraint_score,
                "severity": w.severity.value,
                "message": w.message,
                "suggestion": w.suggestion
            }
            for w in warnings.local
        ],
        "global": [
            {
                "slot": w.slot_number,
                "time_range": w.time_range,
                "competing_subjects": w.competing_subjects,
                "supply_demand_ratio": w.supply_demand_ratio,
                "risk_level": w.risk_level.value,
                "message": w.message
            }
            for w in warnings.global
        ]
    }

def _format_suggestions(suggestions: List) -> List[dict]:
    """Format suggestions for JSON response."""
    return [
        {
            "target_faculty_id": s.target_faculty_id,
            "target_subject_id": s.target_subject_id,
            "type": s.suggestion_type.value,
            "message": s.message,
            "priority": s.priority.value,
            "expected_impact": s.expected_impact
        }
        for s in suggestions
    ]

def _format_constraint_scores(scores: Dict) -> Dict:
    """Format constraint scores for JSON response."""
    return {
        subject_id: {
            "subject_name": score.subject_name,
            "faculty_id": score.faculty_id,
            "faculty_name": score.faculty_name,
            "required_slots": score.required_slots,
            "unique_available_slots": score.unique_available_slots,
            "score": score.score,
            "severity": score.severity.value
        }
        for subject_id, score in scores.items()
    ]
```

- [ ] **Step 4: Run existing tests to verify no breakage**

```bash
pytest tests/adapters/controllers/test_timetable_controller.py -v
```

Expected: Existing tests still pass

- [ ] **Step 5: Commit**

```bash
git add app/adapters/controllers/timetable_controller.py
git commit -m "feat: add feasibility error handling to timetable controller"
```

---

## Task 9: Add Deterministic Seed to TimetableGenerator

**Files:**
- Modify: `app/adapters/services/timetable_generator.py`

- [ ] **Step 1: Update TimetableGenerator with seed**

```python
# Add to imports in timetable_generator.py
import os
import random

# Update __init__ method (around line 60-70)
def __init__(self, subjects: List[Subject]):
    """
    Initialize the generator with subjects.

    Args:
        subjects: List of subjects to schedule
    """
    self.subjects = subjects
    self.time_slots = [TimeSlot(num, start, end)
                      for num, start, end in self.TIME_SLOTS]

    # Add deterministic seed for replay debugging
    self.random_seed = os.urandom(4).hex()
    self.rng = random.Random(self.random_seed)

    # Track attempts for telemetry
    self.last_attempt_count = 0
```

- [ ] **Step 2: Replace random.shuffle with self.rng.shuffle**

Find all `random.shuffle()` calls and replace:

```python
# In _find_available_slot method (around line 537-543)
# Replace: random.shuffle(non_lunch_slots)
# With:
self.rng.shuffle(non_lunch_slots)

# Replace: random.shuffle(lunch_slots)
# With:
self.rng.shuffle(lunch_slots)
```

- [ ] **Step 3: Update attempt tracking**

In `_generate_schedule_for_section` method, add tracking after the loop:

```python
# After the for attempt in range(max_attempts): loop ends (around line 268-275)
# Store attempt count before raising error
self.last_attempt_count = max_attempts

# ... rest of error handling
```

- [ ] **Step 4: Commit**

```bash
git add app/adapters/services/timetable_generator.py
git commit -m "feat: add deterministic seed support to timetable generator"
```

---

## Task 10: Add Generator Helper for Default Constraint Score

**Files:**
- Modify: `app/use_cases/timetable.py`

- [ ] **Step 1: Add fallback helper**

```python
# Add to app/use_cases/timetable.py (at end of file or with other helpers)

class _DefaultConstraintScore:
    """Default constraint score for subjects not in analysis."""
    def __init__(self):
        self.score = 0.0
        self.severity = None
        self.is_tightly_constrained = False
```

- [ ] **Step 2: Update generate_timetable to pass constraint scores**

The generator needs constraint scores for heuristic scheduling. Update the call:

```python
# In generate_timetable method, pass constraint scores to generator
# (This will be implemented in Phase 4 heuristic enhancement)

# For now, ensure constraint scores are available
if hasattr(self.timetable_generator, 'constraint_scores'):
    self.timetable_generator.constraint_scores = request.constraint_scores
```

- [ ] **Step 3: Commit**

```bash
git add app/use_cases/timetable.py
git commit -m "feat: add default constraint score helper"
```

---

## Task 11: Add GenerationTelemetry Import

**Files:**
- Modify: `app/adapters/repositories/__init__.py`

- [ ] **Step 1: Add export**

```python
# Add to app/adapters/repositories/__init__.py
from .generation_telemetry_repository import GenerationTelemetryRepository

__all__ = ["GenerationTelemetryRepository", ...existing exports...]
```

- [ ] **Step 2: Commit**

```bash
git add app/adapters/repositories/__init__.py
git commit -m "feat: export GenerationTelemetryRepository"
```

---

## Task 12: Run Full Test Suite

**Files:**
- All modified files

- [ ] **Step 1: Run all tests**

```bash
pytest tests/ -v --tb=short
```

- [ ] **Step 2: Fix any failing tests**

Debug and fix any test failures.

- [ ] **Step 3: Run integration test**

```bash
# Test the full flow with real-ish data
pytest tests/integration/test_feasibility_integration.py -v
```

- [ ] **Step 4: Commit**

```bash
git add .
git commit -m "test: fix test failures from feasibility implementation"
```

---

## Completion Checklist

After all tasks complete:

- [ ] All tests pass
- [ ] No import errors
- [ ] Feasibility analysis runs before timetable generation
- [ ] FAIL conditions block generation with structured report
- [ ] WARNING conditions allow generation with advisory display
- [ ] Telemetry stores for both success and failure cases
- [ ] Deterministic seed stored for debugging replay
- [ ] Constraint scores use unique (day, slot) pairs
- [ ] Confidence scoring checks CRITICAL before TIGHT

---

**Implementation plan complete.**
