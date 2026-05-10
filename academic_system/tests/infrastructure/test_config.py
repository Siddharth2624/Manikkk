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
