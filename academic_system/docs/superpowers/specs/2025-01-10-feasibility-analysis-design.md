# Pre-Generation Feasibility Analysis - Implementation Specification

**Date:** 2025-01-10
**Author:** Claude (via brainstorming)
**Status:** Approved for Implementation

---

## Overview

This specification defines the pre-generation feasibility analysis system for timetable generation. The system analyzes faculty availability patterns before attempting backtracking, providing structured feedback to prevent unnecessary 10,000-attempt failures.

### Core Principle

**Faculty availability ≠ Slot reservation**

Availability indicates when faculty is *free* to teach. It does not reserve or claim slots. The feasibility analyzer provides *advisory* information about scheduling difficulty and potential conflicts.

---

## Architecture

### Separation of Concerns

| Layer | Responsibility | Constraint Type |
|-------|---------------|-----------------|
| Faculty Availability | "I'm free to teach" | Soft constraint |
| **Feasibility Analyzer** | **Predictive intelligence** | **Advisory analysis** |
| Scheduler (existing) | Actual slot assignment | Hard constraint satisfaction |
| Telemetry | Optimization/debugging | Post-facto analysis |

### Flow Diagram

```
detect_assignments_for_timetable()
    → subjects, faculty_availability, subject_faculty_map
                    ↓
FeasibilityAnalyzer.analyze()
    → constraint_scores, bottleneck_detection, lab_analysis
    → confidence_score (0-100), local/global warnings
    → suggestions (semi-automated)
                    ↓
Decision Point
    FAIL → Block with structured error
    WARNING → Show popup, allow proceed
    PASS → Proceed to generation
                    ↓
generate_timetable()
    → heuristic ordering (most constrained first)
    → backtracking with seed storage
    → GenerationTelemetry on completion
```

---

## Data Structures

### 1. FeasibilityReport

```python
@dataclass
class FeasibilityReport:
    """Complete feasibility analysis result."""

    status: FeasibilityStatus
    """Overall feasibility: PASS, WARNING, FAIL"""

    confidence_score: int
    """0-100, estimated feasibility score (not calibrated to probability)"""

    recoverability: Recoverability
    """RECOVERABLE, DIFFICULT, NEAR_IMPOSSIBLE"""

    errors: List[ValidationError]
    """Hard failures that block generation"""

    warnings: WarningCollection
    """Separated LOCAL and GLOBAL warnings"""

    constraint_scores: Dict[str, ConstraintScore]
    """subject_id -> constraint analysis"""

    suggestions: List[Suggestion]
    """Actionable, semi-automated recommendations"""

    telemetry_snapshot: FeasibilityTelemetry
    """Pre-generation analysis data"""

class FeasibilityStatus(str, Enum):
    PASS = "pass"
    WARNING = "warning"
    FAIL = "fail"

class Recoverability(str, Enum):
    RECOVERABLE = "recoverable"
    DIFFICULT = "difficult"
    NEAR_IMPOSSIBLE = "near_impossible"
```

### 2. Constraint Severity Classification

```python
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
    """Distinct (day, slot) pairs faculty is available for
    Example: MON Slot 1 and TUE Slot 1 count as 2 unique opportunities"""

    score: float
    """required_slots / unique_available_slots"""

    severity: ConstraintSeverity
    """Classification based on score"""

    consecutive_pairs_available: int
    """For labs: usable consecutive slot pairs"""

    @property
    def is_tightly_constrained(self) -> bool:
        return self.severity in (ConstraintSeverity.TIGHT,
                                ConstraintSeverity.CRITICAL)

class ConstraintSeverity(str, Enum):
    COMFORTABLE = "comfortable"   # score < 0.5
    MODERATE = "moderate"         # 0.5 - 0.79
    TIGHT = "tight"               # 0.8 - 0.99
    CRITICAL = "critical"         # ≥ 1.0 (FAIL)
```

### 3. Warning Collection

```python
@dataclass
class WarningCollection:
    """Container for separated warning types."""
    local: List[LocalWarning]
    global: List[GlobalWarning]

    @property
    def has_local(self) -> bool:
        return len(self.local) > 0

    @property
    def has_global(self) -> bool:
        return len(self.global) > 0

    def all_messages(self) -> List[str]:
        return [w.message for w in self.local] + \
               [w.message for w in self.global]

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

class RiskLevel(str, Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"
```

### 4. Suggestion

```python
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
    """"May increase success by ~20%"*/

class SuggestionType(str, Enum):
    ADD_SLOTS = "add_slots"
    DIVERSIFY_SLOTS = "diversify_slots"
    ADD_AFTERNOON = "add_afternoon"
    ADD_CONSECUTIVE = "add_consecutive"
    AVOID_LUNCH = "avoid_lunch"

class SuggestionPriority(str, Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
```

### 5. Telemetry

```python
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

    bottleneck_slots: List[int]
    """Slot numbers with ≥3 competitors"""

    tightly_constrained_faculty: List[str]
    """Faculty IDs with constraint score ≥ 0.8"""

    low_diversity_faculty: List[str]
    """Faculty with ≤3 unique slots"""

    lab_feasible: bool

    estimated_generation_time_ms: int

@dataclass
class GenerationTelemetry:
    """Post-generation execution data."""

    generation_timestamp: datetime
    semester: int
    section: str

    feasibility_confidence: int
    """From pre-generation analysis"""

    generation_seed: int
    """For deterministic replay"""

    actual_attempts_used: int
    """Out of 10,000 max"""

    success: bool
    duration_ms: int

    bottleneck_subjects: List[str]
    """Subjects causing most retries"""

    total_backtracks: int
    backtrack_by_reason: Dict[str, int]

    conflict_hotspots: List[SlotHotspot]

    @dataclass
    class SlotHotspot:
        slot_number: int
        time_range: str
        conflict_count: int
        competing_faculty: List[str]
```

---

## FeasibilityAnalyzer Service

### Location
`app/domain/services/feasibility_analyzer.py`

### Interface

```python
class FeasibilityAnalyzer:
    """Analyzes faculty availability for timetable generation feasibility."""

    def __init__(
        self,
        confidence_calculator: Optional[ConfidenceCalculator] = None,
        telemetry_config: Optional[TelemetryConfig] = None
    ):
        """
        Args:
            confidence_calculator: Modular scoring (injectable for tuning)
            telemetry_config: Storage configuration
        """
        self.confidence_calculator = confidence_calculator or \
                                    DefaultConfidenceCalculator()
        self.telemetry_config = telemetry_config or TelemetryConfig()

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

        Returns FeasibilityReport with:
        - Status (PASS/WARNING/FAIL)
        - Confidence score (0-100)
        - Recoverability classification
        - Separated warnings (LOCAL/GLOBAL)
        - Constraint scores per subject
        - Actionable suggestions
        - Telemetry snapshot
        """

    def _calculate_constraint_scores(
        self,
        subjects: List[Subject],
        faculty_availability: Dict[str, Dict[str, List[int]]],
        subject_faculty_map: Dict[str, str]
    ) -> Dict[str, ConstraintScore]:
        """Calculate required/available ratio per subject."""

    def _detect_bottlenecks(
        self,
        faculty_availability: Dict[str, Dict[str, List[int]]],
        subject_faculty_map: Dict[str, str]
    ) -> List[BottleneckSlot]:
        """Find slots with ≥3 competing subjects."""

    def _analyze_labs(
        self,
        lab_subjects: List[Subject],
        faculty_availability: Dict[str, Dict[str, List[int]]],
        subject_faculty_map: Dict[str, str]
    ) -> LabFeasibilityResult:
        """Check consecutive USABLE slot pairs for labs."""

    def _check_diversity(
        self,
        faculty_availability: Dict[str, Dict[str, List[int]]]
    ) -> List[str]:
        """Identify faculty with ≤3 unique slots."""

    def _generate_suggestions(
        self,
        constraint_scores: Dict[str, ConstraintScore],
        bottlenecks: List[BottleneckSlot],
        low_diversity: List[str],
        lab_result: LabFeasibilityResult
    ) -> List[Suggestion]:
        """Generate semi-automated recommendations."""
```

### Confidence Scoring (Modular)

```python
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
        """Return confidence score 0-100."""
        pass

class DefaultConfidenceCalculator(ConfidenceCalculator):
    """
    Base scoring starts at 100, deducts for issues.

    Deductions:
    - Critical constraint (score ≥ 1.0): -25 each (checked FIRST)
    - Tight constraint (0.8 ≤ score < 1.0): -10 each
    - Bottleneck slot (≥3 competitors): -15 each
    - Lab infeasible: -40
    - Low diversity (≤3 slots): -5 each
    """

    def calculate(self, ...) -> int:
        score = 100

        for cs in constraint_scores:
            # Check CRITICAL first (≥ 1.0), then TIGHT (≥ 0.8)
            if cs >= 1.0:
                score -= 25
            elif cs >= 0.8:
                score -= 10

        score -= bottleneck_count * 15
        if not lab_feasible:
            score -= 40
        score -= low_diversity_count * 5

        return max(0, min(100, score))

# Future: WeightedConfidenceCalculator with configurable weights
```

### Recoverability Classification

```python
def classify_recoverability(
    confidence_score: int,
    critical_count: int,
    bottleneck_count: int
) -> Recoverability:
    """
    Classify generation difficulty.

    NEAR_IMPOSSIBLE:
    - Any CRITICAL constraints
    - Confidence < 30
    - ≥ 3 bottleneck slots

    DIFFICULT:
    - Confidence 30-69
    - 1-2 bottleneck slots
    - Any TIGHT constraints

    RECOVERABLE:
    - Confidence ≥ 70
    - No bottlenecks
    - All COMFORTABLE/MODERATE
    """
    if critical_count > 0 or confidence_score < 30 or bottleneck_count >= 3:
        return Recoverability.NEAR_IMPOSSIBLE
    elif confidence_score < 70 or bottleneck_count > 0 or \
            any(cs >= 0.8 for cs in constraint_scores):
        return Recoverability.DIFFICULT
    else:
        return Recoverability.RECOVERABLE
```

---

## Detection Rules

### Hard FAIL Conditions

| Condition | Detection | Error Message |
|-----------|-----------|---------------|
| No faculty assigned | `subject_faculty_map[id] is None` | "No faculty assigned to {subject}" |
| Zero availability | `len(faculty_slots) == 0` | "Faculty for {subject} has no available slots" |
| Insufficient slots | `constraint_score ≥ 1.0` | "Faculty has {n} slots, needs {m}" |
| Lab no consecutive | `usable_consecutive_pairs == 0` | "Lab requires 2 consecutive periods" |

### WARNING Conditions (Local)

| Condition | Threshold | Risk Level |
|-----------|-----------|------------|
| Tight constraint | `0.8 ≤ score < 1.0` | HIGH |
| Low diversity | `unique_slots ≤ 3` | MEDIUM |
| Single-day dependency | `available_days ≤ 2` | MEDIUM |
| Limited lab pairs | `consecutive_pairs == 1` | HIGH |

### WARNING Conditions (Global)

| Condition | Threshold | Risk Level |
|-----------|-----------|------------|
| Slot bottleneck | `competitors ≥ 3` | MEDIUM |
| Severe bottleneck | `competitors ≥ 4` | HIGH |
| Morning overload | `>70% select slot 1-4` | MEDIUM |

---

## Telemetry Configuration

### Storage Config

```python
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

class GenerationTelemetryRepository:
    """Repository for generation telemetry."""

    def __init__(self, db: AsyncIOMotorDatabase,
                 config: TelemetryConfig):
        self.db = db
        self.config = config
        self.collection = db.generation_telemetry

    async def save(self, telemetry: GenerationTelemetry) -> bool:
        """Save telemetry if enabled and under limits."""
        if not self.config.enabled:
            return True

        if not self.config.persistence_enabled:
            return True

        # Enforce max records
        count = await self.collection.estimated_document_count()
        if count >= self.config.max_records:
            await self._cleanup_oldest()

        result = await self.collection.insert_one(
            self._to_dict(telemetry)
        )
        return result.acknowledged

    async def _cleanup_oldest(self):
        """Remove oldest records when limit reached.

        Note: MongoDB delete_many() does not support sort/limit.
        We must fetch oldest IDs first, then delete explicitly.
        """
        # Find oldest 100 records
        oldest = await self.collection.find(
            {},
            projection={"_id": 1}
        ).sort("generation_timestamp", 1).to_list(length=100)

        if oldest:
            oldest_ids = [doc["_id"] for doc in oldest]
            await self.collection.delete_many({
                "_id": {"$in": oldest_ids}
            })

    async def cleanup_expired(self):
        """Remove records older than retention_days."""
        cutoff = datetime.utcnow() - timedelta(
            days=self.config.retention_days
        )
        await self.collection.delete_many({
            "generation_timestamp": {"$lt": cutoff}
        })
```

### Deterministic Replay Support

```python
# In TimetableGenerator.__init__
self.random_seed = os.urandom(4).hex()
self.rng = random.Random(self.random_seed)

# Store seed in telemetry
telemetry.generation_seed = self.random_seed

# For debugging: replay with same seed
generator = TimetableGenerator(...)
generator.rng = random.Random(saved_seed)
```

---

## Integration Points

### TimetableUseCase.update

```python
class TimetableUseCase:
    def __init__(
        self,
        # ... existing dependencies ...
        feasibility_analyzer: FeasibilityAnalyzer = None,
        telemetry_repo: GenerationTelemetryRepository = None
    ):
        # ... existing ...
        self.feasibility_analyzer = feasibility_analyzer or \
                                    FeasibilityAnalyzer()
        self.telemetry_repo = telemetry_repo

    async def generate_timetable_simple(
        self,
        semester: int,
        section: str,
        created_by: str
    ) -> GenerateTimetableResponse:
        """Generate with feasibility check."""

        # 1. Auto-detect assignments
        detected = await self.detect_assignments_for_timetable(
            semester=semester, section=section
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

        # 4. Handle FAIL
        if report.status == FeasibilityStatus.FAIL:
            raise FeasibilityError(
                message="Cannot generate timetable",
                report=report
            )

        # 5. Prepare request with warnings
        request = GenerateTimetableRequest(
            semester=semester,
            section=section,
            subject_ids=detected["subject_ids"],
            faculty_availability=detected["faculty_availability"],
            subject_faculty_map=detected["subject_faculty_map"],
            created_by=created_by,
            feasibility_report=report  # Attach for later use
        )

        # 6. Generate (with heuristic ordering)
        response = await self.generate_timetable(request)

        # 7. Store telemetry (for BOTH successful AND failed generations)
        if self.telemetry_repo and self.telemetry_repo.config.enabled:
            telemetry = GenerationTelemetry(
                generation_timestamp=datetime.utcnow(),
                semester=semester,
                section=section,
                feasibility_confidence=report.confidence_score,
                generation_seed=self.timetable_generator.random_seed,
                actual_attempts_used=self.timetable_generator.last_attempt_count,
                success=True,  # Set to False if generation fails
                duration_ms=response.duration_ms
            )
            await self.telemetry_repo.save(telemetry)

        # 8. Attach warnings to response
        response.warnings = report.warnings
        response.confidence_score = report.confidence_score

        return response
```

### Controller Response

```python
@router.post("/generate")
async def generate_timetable(
    semester: int,
    section: str,
    current_admin: User = Depends(get_current_admin),
    use_case: TimetableUseCase = Depends(get_timetable_use_case)
):
    """Generate timetable with feasibility analysis."""

    try:
        response = await use_case.generate_timetable_simple(
            semester=semester,
            section=section,
            created_by=current_admin.id
        )
        return response

    except FeasibilityError as e:
        # Return structured feasibility report
        return JSONResponse(
            status_code=400,
            content={
                "status": "fail",
                "can_proceed": False,
                "report": feasibility_report_to_dict(e.report)
            }
        )
```

### Response Format

```json
{
  "status": "warning",
  "can_proceed": true,
  "confidence_score": 65,
  "recoverability": "difficult",

  "local_warnings": [
    {
      "faculty_id": "fac_123",
      "faculty_name": "Dr. Smith",
      "subject_id": "sub_456",
      "subject_name": "Mathematics",
      "risk_level": "high",
      "constraint_score": 0.9,
      "severity": "tight",
      "message": "Only 4 unique slots for 4 required credits",
      "suggestion": "Add 2+ afternoon slots for flexibility"
    }
  ],

  "global_warnings": [
    {
      "slot": 1,
      "time_range": "9:00-9:50 AM",
      "competing_subjects": ["Math", "Physics", "CS"],
      "supply_demand_ratio": 1.0,
      "risk_level": "medium",
      "message": "3 subjects competing for this slot"
    }
  ],

  "suggestions": [
    {
      "target_faculty_id": "fac_123",
      "type": "add_afternoon",
      "message": "Consider adding afternoon availability (2-5 PM)",
      "priority": "high",
      "expected_impact": "+20% feasibility score"
    }
  ]
}
```

---

## Heuristic Scheduling Enhancement

### Most-Constrained-First Ordering

```python
# In TimetableGenerator._generate_schedule_for_section

# Sort subjects by constraint score (most constrained first)
# Use explicit fallback for subjects not in constraint_scores
sorted_theory = sorted(
    theory_subjects,
    key=lambda s: constraint_scores.get(s.id, ConstraintScore()),
    reverse=True  # Higher score = more constrained = schedule first
)

sorted_labs = sorted(
    lab_subjects,
    key=lambda s: constraint_scores.get(s.id, ConstraintScore()),
    reverse=True
)

# Helper: Default constraint score for unmapped subjects
class ConstraintScore:
    score = 0.0  # Faculty with no constraints scheduled last
```

---

## Error Types

```python
class FeasibilityError(ValueError):
    """Raised when feasibility analysis detects impossible state."""

    def __init__(self, message: str, report: FeasibilityReport):
        self.message = message
        self.report = report
        super().__init__(message)
```

---

## File Structure

```
app/domain/
├── entities/
│   └── feasibility.py              # All dataclasses
├── services/
│   └── feasibility_analyzer.py     # Main analyzer service
│   └── confidence/
│       ├── base.py                 # ConfidenceCalculator ABC
│       └── default.py              # DefaultConfidenceCalculator

app/adapters/
└── repositories/
    └── generation_telemetry_repository.py

app/use_cases/
└── timetable.py                    # Updated with feasibility integration

app/infrastructure/
└── config.py                       # Add telemetry config

app/domain/
└── exceptions.py                   # Add FeasibilityError
```

---

## Implementation Checklist

### Phase 1: Core Analysis
- [ ] Create feasibility dataclasses (`feasibility.py`)
- [ ] Implement `FeasibilityAnalyzer` service
- [ ] Implement constraint score calculation
- [ ] Implement bottleneck detection
- [ ] Implement lab feasibility analysis
- [ ] Implement diversity checking
- [ ] Implement suggestion generation
- [ ] Implement confidence calculator (modular)

### Phase 2: Integration
- [ ] Update `TimetableUseCase.generate_timetable_simple()`
- [ ] Add `FeasibilityError` exception
- [ ] Update controller response format
- [ ] Implement recoverability classification

### Phase 3: Telemetry
- [ ] Create `GenerationTelemetryRepository`
- [ ] Implement `TelemetryConfig`
- [ ] Add deterministic seed storage
- [ ] Implement cleanup jobs
- [ ] Add telemetry to generation response

### Phase 4: Heuristic Enhancement
- [ ] Implement most-constrained-first ordering in generator
- [ ] Pass constraint scores to generator
- [ ] Track bottleneck subjects

### Phase 5: Admin Display (Future)
- [ ] Feasibility popup UI
- [ ] Warning display (separated local/global)
- [ ] Suggestions display
- [ ] Confidence score visualization

---

## Testing Strategy

### Unit Tests
- Constraint score calculation edge cases
- Bottleneck detection accuracy
- Lab consecutive pair detection
- Confidence score calculation
- Suggestion generation logic
- Recoverability classification

### Integration Tests
- Full feasibility analysis flow
- FAIL block behavior
- WARNING proceed behavior
- Telemetry storage and cleanup
- Deterministic replay with seed

### Edge Cases
- Empty faculty availability
- Single faculty, multiple subjects
- All labs, no theory
- All subjects competing for same slot
- Section with 1 subject vs 10 subjects

---

## Future Extensions

### Weighted Confidence Scoring
```python
class WeightedConfidenceCalculator(ConfidenceCalculator):
    def __init__(self, weights: Dict[str, float]):
        # weights = {"tight_constraint": 15, "bottleneck": 20, ...}
        self.weights = weights

    def calculate(self, ...) -> int:
        score = 100
        for factor, value in analysis.items():
            score -= value * self.weights.get(factor, 1.0)
```

### Machine Learning Enhancement
- Train on historical generation telemetry
- Predict success probability based on patterns
- Suggest optimal availability adjustments

### Faculty Advisory UI (Phase 3)
- Real-time overlap indicators
- Health score display
- Slot competition visualization

---

## Success Criteria

1. **Prevents unnecessary 10,000-attempt failures**
   - FAIL conditions detected before backtracking
   - Clear error messages with actionable suggestions

2. **Provides actionable intelligence**
   - Admin can understand WHY generation might fail
   - Semi-automated suggestions guide resolution

3. **Maintains architectural separation**
   - Availability remains soft constraint
   - Feasibility is advisory only
   - Scheduler handles actual assignment

4. **Enables data-driven improvement**
   - Telemetry tracks bottlenecks
   - Deterministic replay for debugging
   - Configurable retention prevents unbounded growth

---

**End of Specification**
