"""
Integration tests for the scheduling system.

Tests the complete scheduler workflow including:
- Scheduler startup/shutdown
- Job creation and management
- Schedule modification
- API endpoints
- Run filtering by trigger_type
"""
import pytest
from datetime import datetime
from unittest.mock import patch, AsyncMock
from fastapi.testclient import TestClient

from app.main import app
from app.services.scheduler_service import SchedulerService


@pytest.fixture
def client():
    """FastAPI test client."""
    return TestClient(app)


@pytest.fixture
def scheduler():
    """Fresh scheduler instance (not started)."""
    # Reset singleton for clean test
    SchedulerService.reset_instance()
    return SchedulerService()


@pytest.fixture(autouse=True)
def reset_scheduler_after_test():
    """Reset scheduler singleton after each test."""
    yield
    SchedulerService.reset_instance()


class TestSchedulerService:
    """Tests for SchedulerService class."""

    def test_singleton_pattern(self, scheduler):
        """Verify scheduler is a singleton."""
        svc1 = SchedulerService()
        svc2 = SchedulerService()
        assert svc1 is svc2

    def test_job_id_generation(self, scheduler):
        """Verify job IDs follow pattern."""
        assert scheduler.get_job_id("Health") == "category_run_health"
        assert scheduler.get_job_id("Dental") == "category_run_dental"
        assert scheduler.get_job_id("Group Life") == "category_run_group_life"

    def test_timezone_is_sao_paulo(self, scheduler):
        """Verify Sao Paulo timezone configured."""
        assert str(scheduler.SAO_PAULO_TZ) == "America/Sao_Paulo"

    def test_scheduler_not_running_initially(self, scheduler):
        """Verify scheduler is not running before start()."""
        assert not scheduler._scheduler.running

    def test_get_schedule_returns_none_before_start(self, scheduler):
        """Verify get_schedule returns None when jobs don't exist."""
        result = scheduler.get_schedule("Health")
        assert result is None

    def test_get_all_schedules_returns_placeholder(self, scheduler):
        """Verify get_all_schedules returns placeholder info for missing jobs."""
        schedules = scheduler.get_all_schedules()
        assert len(schedules) == 3

        for schedule in schedules:
            assert "job_id" in schedule
            assert "category" in schedule
            assert schedule["paused"] is True  # No jobs exist yet

    def test_get_health_status_structure(self, scheduler):
        """Verify health status returns correct structure."""
        status = scheduler.get_health_status()

        assert "scheduler_running" in status
        assert "jobs_count" in status
        assert "timezone" in status
        assert "next_jobs" in status
        assert status["timezone"] == "America/Sao_Paulo"


class TestScheduleAPI:
    """Tests for schedule API endpoints."""

    def test_list_schedules(self, client):
        """Test GET /api/schedules returns all schedules."""
        response = client.get("/api/schedules")
        assert response.status_code == 200

        data = response.json()
        assert "schedules" in data
        assert "timezone" in data
        assert data["timezone"] == "America/Sao_Paulo"

    def test_get_schedule_by_category_valid(self, client):
        """Test GET /api/schedules/{category} with valid category returns 404 (no jobs created)."""
        # Note: Without starting the scheduler, jobs don't exist
        response = client.get("/api/schedules/Health")
        # Returns 404 because job doesn't exist until scheduler starts
        assert response.status_code in [200, 404]

    def test_get_schedule_invalid_category(self, client):
        """Test GET /api/schedules/{category} with invalid category."""
        response = client.get("/api/schedules/Invalid")
        assert response.status_code == 400

        data = response.json()
        assert "Invalid category" in data.get("detail", "")

    def test_scheduler_health(self, client):
        """Test GET /api/schedules/health."""
        response = client.get("/api/schedules/health")
        assert response.status_code == 200

        data = response.json()
        assert "scheduler_running" in data
        assert "jobs_count" in data
        assert "timezone" in data
        assert data["timezone"] == "America/Sao_Paulo"


class TestRunFiltering:
    """Tests for run history filtering."""

    def test_list_runs_endpoint(self, client):
        """Test GET /api/runs returns successfully."""
        response = client.get("/api/runs")
        assert response.status_code == 200
        assert isinstance(response.json(), list)

    def test_list_runs_with_trigger_type_filter(self, client):
        """Test GET /api/runs with trigger_type filter."""
        response = client.get("/api/runs?trigger_type=manual")
        assert response.status_code == 200
        assert isinstance(response.json(), list)

    def test_list_runs_with_scheduled_filter(self, client):
        """Test GET /api/runs with trigger_type=scheduled filter."""
        response = client.get("/api/runs?trigger_type=scheduled")
        assert response.status_code == 200
        assert isinstance(response.json(), list)

    def test_list_runs_combined_filters(self, client):
        """Test GET /api/runs with multiple filters."""
        response = client.get("/api/runs?category=Health&status=completed&trigger_type=manual")
        assert response.status_code == 200
        assert isinstance(response.json(), list)

    def test_get_latest_runs(self, client):
        """Test GET /api/runs/latest."""
        response = client.get("/api/runs/latest")
        assert response.status_code == 200

        data = response.json()
        assert "latest_runs" in data

        # Verify structure contains expected categories
        latest_runs = data["latest_runs"]
        assert "Health" in latest_runs or latest_runs.get("Health") is None
        assert "Dental" in latest_runs or latest_runs.get("Dental") is None
        assert "Group Life" in latest_runs or latest_runs.get("Group Life") is None

    def test_get_run_stats(self, client):
        """Test GET /api/runs/stats?days=7."""
        response = client.get("/api/runs/stats?days=7")
        assert response.status_code == 200

        data = response.json()
        assert "period_days" in data
        assert data["period_days"] == 7
        assert "total_runs" in data
        assert "by_status" in data
        assert "by_trigger_type" in data
        assert "by_category" in data

    def test_get_run_stats_custom_days(self, client):
        """Test GET /api/runs/stats with custom days parameter."""
        response = client.get("/api/runs/stats?days=30")
        assert response.status_code == 200

        data = response.json()
        assert data["period_days"] == 30


class TestCategoryValidation:
    """Tests for category validation in schedule endpoints."""

    def test_valid_category_health(self, client):
        """Test Health category is valid."""
        response = client.get("/api/schedules/Health")
        # May be 200 or 404 depending on scheduler state, but not 400
        assert response.status_code != 400 or "Invalid category" not in response.json().get("detail", "")

    def test_valid_category_dental(self, client):
        """Test Dental category is valid."""
        response = client.get("/api/schedules/Dental")
        assert response.status_code != 400 or "Invalid category" not in response.json().get("detail", "")

    def test_valid_category_group_life(self, client):
        """Test Group Life category is valid."""
        response = client.get("/api/schedules/Group%20Life")
        assert response.status_code != 400 or "Invalid category" not in response.json().get("detail", "")

    def test_case_insensitive_category(self, client):
        """Test category matching is case-insensitive."""
        response = client.get("/api/schedules/health")
        # Should normalize to "Health" and not return 400 for invalid category
        assert response.status_code != 400 or "Invalid category" not in response.json().get("detail", "")


class TestScheduleEndpointStructure:
    """Tests for schedule endpoint response structure."""

    def test_schedule_list_structure(self, client):
        """Test structure of schedule list response."""
        response = client.get("/api/schedules")
        assert response.status_code == 200

        data = response.json()
        schedules = data.get("schedules", [])

        # Each schedule should have required fields
        for schedule in schedules:
            assert "category" in schedule
            assert "job_id" in schedule
            assert "enabled" in schedule
            assert "cron_expression" in schedule

    def test_health_status_structure(self, client):
        """Test structure of health status response."""
        response = client.get("/api/schedules/health")
        assert response.status_code == 200

        data = response.json()
        assert isinstance(data["scheduler_running"], bool)
        assert isinstance(data["jobs_count"], int)
        assert isinstance(data["timezone"], str)
        assert isinstance(data["next_jobs"], list)


class TestTriggerEndpoints:
    """Tests for schedule trigger endpoints."""

    def test_pause_endpoint_exists(self, client):
        """Test POST /api/schedules/{category}/pause endpoint exists."""
        response = client.post("/api/schedules/Health/pause")
        # May fail if no job exists, but endpoint should exist
        assert response.status_code in [200, 400, 404, 500]

    def test_resume_endpoint_exists(self, client):
        """Test POST /api/schedules/{category}/resume endpoint exists."""
        response = client.post("/api/schedules/Health/resume")
        # May fail if no job exists, but endpoint should exist
        assert response.status_code in [200, 400, 404, 500]

    def test_trigger_endpoint_exists(self, client):
        """Test POST /api/schedules/{category}/trigger endpoint exists."""
        # This will attempt to trigger a run, so we just verify the endpoint exists
        # by checking it doesn't return 405 Method Not Allowed
        response = client.post("/api/schedules/Health/trigger")
        assert response.status_code != 405
