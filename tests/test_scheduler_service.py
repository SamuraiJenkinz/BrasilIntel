"""
Tests for SchedulerService.

Validates singleton pattern, job ID generation, timezone configuration,
and basic scheduler functionality.
"""
import pytest
from unittest.mock import patch, MagicMock
from zoneinfo import ZoneInfo

from app.services.scheduler_service import SchedulerService


@pytest.fixture(autouse=True)
def reset_singleton():
    """Reset singleton before and after each test."""
    SchedulerService.reset_instance()
    yield
    SchedulerService.reset_instance()


class TestSingletonPattern:
    """Tests for singleton pattern implementation."""

    def test_singleton_returns_same_instance(self):
        """Verify singleton returns same instance."""
        svc1 = SchedulerService()
        svc2 = SchedulerService()
        assert svc1 is svc2

    def test_singleton_initializes_once(self):
        """Verify initialization only happens once."""
        svc1 = SchedulerService()
        initial_scheduler = svc1._scheduler

        svc2 = SchedulerService()
        assert svc2._scheduler is initial_scheduler


class TestJobIdGeneration:
    """Tests for job ID generation."""

    def test_job_id_health(self):
        """Verify job ID for Health category."""
        svc = SchedulerService()
        assert svc.get_job_id("Health") == "category_run_health"

    def test_job_id_dental(self):
        """Verify job ID for Dental category."""
        svc = SchedulerService()
        assert svc.get_job_id("Dental") == "category_run_dental"

    def test_job_id_group_life(self):
        """Verify job ID for Group Life category."""
        svc = SchedulerService()
        assert svc.get_job_id("Group Life") == "category_run_group_life"

    def test_job_id_lowercase_conversion(self):
        """Verify job ID converts to lowercase."""
        svc = SchedulerService()
        assert svc.get_job_id("HEALTH") == "category_run_health"
        assert svc.get_job_id("DENTAL") == "category_run_dental"


class TestTimezoneConfiguration:
    """Tests for timezone configuration."""

    def test_timezone_is_sao_paulo(self):
        """Verify Sao Paulo timezone is set."""
        svc = SchedulerService()
        assert str(svc.SAO_PAULO_TZ) == "America/Sao_Paulo"

    def test_timezone_is_zoneinfo_type(self):
        """Verify timezone is proper ZoneInfo type."""
        svc = SchedulerService()
        assert isinstance(svc.SAO_PAULO_TZ, ZoneInfo)


class TestSchedulerInitialization:
    """Tests for scheduler initialization state."""

    def test_scheduler_not_running_initially(self):
        """Verify scheduler doesn't auto-start."""
        svc = SchedulerService()
        assert not svc._scheduler.running

    def test_scheduler_created(self):
        """Verify scheduler object is created."""
        svc = SchedulerService()
        assert svc._scheduler is not None

    def test_categories_defined(self):
        """Verify all three categories are defined."""
        svc = SchedulerService()
        assert svc.CATEGORIES == ["Health", "Dental", "Group Life"]

    def test_is_running_property_false_initially(self):
        """Verify is_running property returns False initially."""
        svc = SchedulerService()
        assert svc.is_running is False


class TestGetSchedule:
    """Tests for schedule retrieval methods."""

    def test_get_schedule_returns_none_for_missing_job(self):
        """Verify get_schedule returns None when job doesn't exist."""
        svc = SchedulerService()
        result = svc.get_schedule("Health")
        # Job doesn't exist until start() is called
        assert result is None

    def test_get_all_schedules_returns_list(self):
        """Verify get_all_schedules returns a list."""
        svc = SchedulerService()
        result = svc.get_all_schedules()
        assert isinstance(result, list)
        assert len(result) == 3  # One per category


class TestResetInstance:
    """Tests for singleton reset functionality."""

    def test_reset_clears_instance(self):
        """Verify reset clears the singleton instance."""
        svc1 = SchedulerService()
        SchedulerService.reset_instance()

        # After reset, _instance should be None
        assert SchedulerService._instance is None
        assert SchedulerService._scheduler is None
        assert SchedulerService._initialized is False

    def test_new_instance_after_reset(self):
        """Verify new instance is created after reset."""
        svc1 = SchedulerService()
        id1 = id(svc1)

        SchedulerService.reset_instance()
        svc2 = SchedulerService()
        id2 = id(svc2)

        # After reset, we get a new instance
        assert id1 != id2
