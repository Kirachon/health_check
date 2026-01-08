"""Tests for Alerting Engine."""
import pytest
from unittest.mock import AsyncMock, patch, MagicMock
from decimal import Decimal
from fastapi.testclient import TestClient

from db.models import Trigger, AlertEvent, Template


class TestAlertingService:
    """Test TriggerEvaluator service."""

    @pytest.mark.asyncio
    async def test_parse_threshold_greater_than(self):
        """Test > threshold parsing."""
        from services.alerting import TriggerEvaluator
        
        evaluator = TriggerEvaluator()
        
        # Value above threshold -> PROBLEM
        assert evaluator.parse_threshold("cpu_percent > 90", 95.0) == "PROBLEM"
        # Value below threshold -> OK
        assert evaluator.parse_threshold("cpu_percent > 90", 85.0) == "OK"
        # Value at threshold -> OK (not greater)
        assert evaluator.parse_threshold("cpu_percent > 90", 90.0) == "OK"

    @pytest.mark.asyncio
    async def test_parse_threshold_greater_equal(self):
        """Test >= threshold parsing."""
        from services.alerting import TriggerEvaluator
        
        evaluator = TriggerEvaluator()
        
        assert evaluator.parse_threshold("memory >= 80", 80.0) == "PROBLEM"
        assert evaluator.parse_threshold("memory >= 80", 79.9) == "OK"

    @pytest.mark.asyncio
    async def test_parse_threshold_less_than(self):
        """Test < threshold parsing."""
        from services.alerting import TriggerEvaluator
        
        evaluator = TriggerEvaluator()
        
        assert evaluator.parse_threshold("disk_free < 10", 5.0) == "PROBLEM"
        assert evaluator.parse_threshold("disk_free < 10", 15.0) == "OK"

    @pytest.mark.asyncio
    async def test_query_vm_returns_value(self):
        """Test VictoriaMetrics query parsing."""
        from services.alerting import TriggerEvaluator
        
        evaluator = TriggerEvaluator("http://localhost:9090")
        
        with patch('httpx.AsyncClient') as mock_client:
            mock_response = MagicMock()
            mock_response.status_code = 200
            mock_response.json.return_value = {
                "status": "success",
                "data": {"result": [{"value": [1234567890, "42.5"]}]}
            }
            mock_response.raise_for_status = MagicMock()
            
            mock_client_instance = AsyncMock()
            mock_client_instance.get = AsyncMock(return_value=mock_response)
            mock_client.return_value.__aenter__ = AsyncMock(return_value=mock_client_instance)
            mock_client.return_value.__aexit__ = AsyncMock()
            
            value = await evaluator.query_vm("test_metric > 10")
            assert value == 42.5


class TestAlertsAPI:
    """Test Alerts API endpoints."""

    def test_list_alerts_requires_auth(self, client: TestClient):
        """Test that listing alerts requires authentication."""
        response = client.get("/api/v1/alerts")
        assert response.status_code in (401, 403)

    def test_list_alerts_empty(self, authenticated_client: TestClient):
        """Test listing alerts when none exist."""
        response = authenticated_client.get("/api/v1/alerts")
        assert response.status_code == 200
        data = response.json()
        assert "events" in data
        assert "total" in data

    def test_get_alert_not_found(self, authenticated_client: TestClient):
        """Test getting non-existent alert."""
        response = authenticated_client.get("/api/v1/alerts/00000000-0000-0000-0000-000000000000")
        assert response.status_code == 404

    def test_alert_counts(self, authenticated_client: TestClient):
        """Test alert summary counts endpoint."""
        response = authenticated_client.get("/api/v1/alerts/summary/counts")
        assert response.status_code == 200
        data = response.json()
        assert "total" in data
        assert "problem" in data
        assert "ok" in data
        assert "unacknowledged" in data
