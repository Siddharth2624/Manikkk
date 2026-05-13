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
    """Critical constraints get -25 each; exact-fit constraints are tight."""
    calc = DefaultConfidenceCalculator()
    score = calc.calculate(
        constraint_scores=[1.0, 1.2],  # One tight, one critical
        bottleneck_count=0,
        total_faculty=2,
        lab_feasible=True,
        low_diversity_count=0
    )
    assert score == 65  # 100 - 10 - 25

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
