"""Tests for classification service."""
import pytest
from unittest.mock import Mock, patch, MagicMock
from app.services.classifier import ClassificationService, SYSTEM_PROMPT_SINGLE
from app.schemas.classification import NewsClassification, InsurerClassification


class TestNewsClassificationSchema:
    """Tests for NewsClassification Pydantic model."""

    def test_valid_classification(self):
        """Should accept valid classification data."""
        nc = NewsClassification(
            status="Critical",
            summary_bullets=["Crise financeira detectada"],
            sentiment="negative",
            reasoning="Notícia indica problemas financeiros graves",
            category_indicators=["financial_crisis", "regulatory_action"]
        )
        assert nc.status == "Critical"
        assert nc.sentiment == "negative"
        assert "financial_crisis" in nc.category_indicators

    def test_invalid_status_rejected(self):
        """Should reject invalid status values."""
        with pytest.raises(ValueError):
            NewsClassification(
                status="InvalidStatus",
                summary_bullets=["test"],
                sentiment="neutral",
                reasoning="test"
            )

    def test_invalid_sentiment_rejected(self):
        """Should reject invalid sentiment values."""
        with pytest.raises(ValueError):
            NewsClassification(
                status="Watch",
                summary_bullets=["test"],
                sentiment="invalid_sentiment",
                reasoning="test"
            )

    def test_empty_category_indicators_allowed(self):
        """Should allow empty category_indicators list."""
        nc = NewsClassification(
            status="Stable",
            summary_bullets=["Operações normais"],
            sentiment="neutral",
            reasoning="Sem eventos significativos",
            category_indicators=[]
        )
        assert nc.category_indicators == []

    def test_default_category_indicators(self):
        """Should default to empty list if not provided."""
        nc = NewsClassification(
            status="Stable",
            summary_bullets=["test"],
            sentiment="neutral",
            reasoning="test"
        )
        assert nc.category_indicators == []

    def test_multiple_category_indicators(self):
        """Should accept multiple category indicators."""
        nc = NewsClassification(
            status="Watch",
            summary_bullets=["M&A e mudanças de liderança"],
            sentiment="neutral",
            reasoning="Atividade corporativa significativa",
            category_indicators=["m_and_a", "leadership_change", "partnership"]
        )
        assert len(nc.category_indicators) == 3
        assert "m_and_a" in nc.category_indicators
        assert "leadership_change" in nc.category_indicators
        assert "partnership" in nc.category_indicators


class TestInsurerClassificationSchema:
    """Tests for InsurerClassification Pydantic model."""

    def test_valid_insurer_classification(self):
        """Should accept valid insurer classification data."""
        ic = InsurerClassification(
            overall_status="Critical",
            key_findings=["Crise detectada", "Intervenção regulatória"],
            risk_factors=["Problemas de solvência", "Multas regulatórias"],
            sentiment_breakdown={"positive": 0, "negative": 5, "neutral": 2},
            reasoning="Múltiplos indicadores críticos detectados"
        )
        assert ic.overall_status == "Critical"
        assert len(ic.key_findings) == 2
        assert len(ic.risk_factors) == 2
        assert ic.sentiment_breakdown["negative"] == 5

    def test_empty_risk_factors_allowed(self):
        """Should allow empty risk_factors for Stable status."""
        ic = InsurerClassification(
            overall_status="Stable",
            key_findings=["Operações normais"],
            risk_factors=[],
            sentiment_breakdown={"positive": 1, "negative": 0, "neutral": 3},
            reasoning="Sem problemas identificados"
        )
        assert ic.risk_factors == []


class TestClassificationServiceInit:
    """Tests for ClassificationService initialization."""

    def test_init_without_config(self):
        """Should handle missing Azure OpenAI config gracefully."""
        with patch('app.services.classifier.get_settings') as mock_settings:
            mock_settings.return_value = Mock(
                is_azure_openai_configured=Mock(return_value=False),
                use_llm_summary=True
            )
            service = ClassificationService()
            assert service.client is None
            assert service.model is None

    def test_init_with_llm_disabled(self):
        """Should respect use_llm_summary=False setting."""
        with patch('app.services.classifier.get_settings') as mock_settings:
            mock_settings.return_value = Mock(
                is_azure_openai_configured=Mock(return_value=True),
                use_llm_summary=False,
                azure_openai_endpoint="https://test.openai.azure.com/",
                azure_openai_api_key="test-key",
                azure_openai_api_version="2024-08-01-preview",
                azure_openai_deployment="gpt-4o"
            )
            with patch('app.services.classifier.AzureOpenAI'):
                service = ClassificationService()
                assert service.use_llm is False

    def test_init_with_valid_config(self):
        """Should initialize client with valid config."""
        with patch('app.services.classifier.get_settings') as mock_settings:
            mock_settings.return_value = Mock(
                is_azure_openai_configured=Mock(return_value=True),
                use_llm_summary=True,
                azure_openai_endpoint="https://test.openai.azure.com/",
                azure_openai_api_key="test-key",
                azure_openai_api_version="2024-08-01-preview",
                azure_openai_deployment="gpt-4o"
            )
            with patch('app.services.classifier.AzureOpenAI') as mock_client:
                service = ClassificationService()
                assert service.client is not None
                assert service.model == "gpt-4o"
                assert service.use_llm is True


class TestClassificationServiceFallback:
    """Tests for fallback classification behavior."""

    def test_fallback_when_client_none(self):
        """Should return fallback when client is None."""
        with patch('app.services.classifier.get_settings') as mock_settings:
            mock_settings.return_value = Mock(
                is_azure_openai_configured=Mock(return_value=False),
                use_llm_summary=True
            )
            service = ClassificationService()
            result = service.classify_single_news("Test Insurer", "Test Title")

            assert result is not None
            assert result.status == "Monitor"
            assert result.sentiment == "neutral"
            assert "routine_operations" in result.category_indicators

    def test_fallback_when_llm_disabled(self):
        """Should return fallback when use_llm_summary=False."""
        with patch('app.services.classifier.get_settings') as mock_settings:
            mock_settings.return_value = Mock(
                is_azure_openai_configured=Mock(return_value=True),
                use_llm_summary=False,
                azure_openai_endpoint="https://test.openai.azure.com/",
                azure_openai_api_key="test-key",
                azure_openai_api_version="2024-08-01-preview",
                azure_openai_deployment="gpt-4o"
            )
            with patch('app.services.classifier.AzureOpenAI'):
                service = ClassificationService()
                result = service.classify_single_news("Test Insurer", "Test Title")

                assert result is not None
                assert result.status == "Monitor"
                assert result.sentiment == "neutral"
                assert "routine_operations" in result.category_indicators

    def test_fallback_insurer_classification(self):
        """Should return fallback insurer classification when LLM unavailable."""
        with patch('app.services.classifier.get_settings') as mock_settings:
            mock_settings.return_value = Mock(
                is_azure_openai_configured=Mock(return_value=False),
                use_llm_summary=True
            )
            service = ClassificationService()
            result = service.classify_insurer_news("Test", [{"title": "News"}])

            assert result is not None
            assert result.overall_status == "Monitor"
            assert result.sentiment_breakdown == {"positive": 0, "negative": 0, "neutral": 0}

    def test_fallback_structure_matches_schema(self):
        """Should verify fallback returns complete NewsClassification."""
        with patch('app.services.classifier.get_settings') as mock_settings:
            mock_settings.return_value = Mock(
                is_azure_openai_configured=Mock(return_value=False),
                use_llm_summary=True
            )
            service = ClassificationService()
            result = service.classify_single_news("Test", "Title")

            # Verify all required fields present
            assert hasattr(result, 'status')
            assert hasattr(result, 'summary_bullets')
            assert hasattr(result, 'sentiment')
            assert hasattr(result, 'reasoning')
            assert hasattr(result, 'category_indicators')
            assert isinstance(result.category_indicators, list)


class TestClassificationServiceHealthCheck:
    """Tests for health check functionality."""

    def test_health_check_not_configured(self):
        """Should return error status when not configured."""
        with patch('app.services.classifier.get_settings') as mock_settings:
            mock_settings.return_value = Mock(
                is_azure_openai_configured=Mock(return_value=False),
                use_llm_summary=True
            )
            service = ClassificationService()
            health = service.health_check()

            assert health["status"] == "error"
            assert "not configured" in health["message"]

    def test_health_check_disabled(self):
        """Should return disabled status when LLM disabled."""
        with patch('app.services.classifier.get_settings') as mock_settings:
            mock_settings.return_value = Mock(
                is_azure_openai_configured=Mock(return_value=True),
                use_llm_summary=False,
                azure_openai_endpoint="https://test.openai.azure.com/",
                azure_openai_api_key="test-key",
                azure_openai_api_version="2024-08-01-preview",
                azure_openai_deployment="gpt-4o"
            )
            with patch('app.services.classifier.AzureOpenAI'):
                service = ClassificationService()
                health = service.health_check()

                assert health["status"] == "disabled"


class TestSystemPrompt:
    """Tests for system prompt content."""

    def test_prompt_includes_classification_criteria(self):
        """System prompt should include all classification criteria."""
        assert "CRITICAL" in SYSTEM_PROMPT_SINGLE.upper()
        assert "WATCH" in SYSTEM_PROMPT_SINGLE.upper()
        assert "MONITOR" in SYSTEM_PROMPT_SINGLE.upper()
        assert "STABLE" in SYSTEM_PROMPT_SINGLE.upper()

    def test_prompt_includes_category_indicators(self):
        """System prompt should include category indicator descriptions."""
        prompt_lower = SYSTEM_PROMPT_SINGLE.lower()
        # Check for key category indicators in Portuguese descriptions
        assert "financial_crisis" in prompt_lower
        assert "regulatory_action" in prompt_lower
        assert "m_and_a" in prompt_lower
        assert "leadership_change" in prompt_lower
        assert "fraud_criminal" in prompt_lower
        assert "routine_operations" in prompt_lower

    def test_prompt_requests_portuguese_output(self):
        """System prompt should request Portuguese output."""
        assert "português" in SYSTEM_PROMPT_SINGLE.lower()

    def test_prompt_has_all_ten_categories(self):
        """System prompt should document all 10 category indicators."""
        categories = [
            "financial_crisis",
            "regulatory_action",
            "m_and_a",
            "leadership_change",
            "fraud_criminal",
            "rate_change",
            "network_change",
            "market_expansion",
            "partnership",
            "routine_operations"
        ]
        for category in categories:
            assert category in SYSTEM_PROMPT_SINGLE, f"Missing {category} in prompt"


class TestClassificationWithDescription:
    """Tests for classification with optional description field."""

    def test_classification_with_description(self):
        """Should handle news with description field."""
        with patch('app.services.classifier.get_settings') as mock_settings:
            mock_settings.return_value = Mock(
                is_azure_openai_configured=Mock(return_value=False),
                use_llm_summary=True
            )
            service = ClassificationService()
            result = service.classify_single_news(
                "Test Insurer",
                "Test Title",
                "Test Description"
            )
            assert result is not None
            assert result.status == "Monitor"

    def test_classification_without_description(self):
        """Should handle news without description field."""
        with patch('app.services.classifier.get_settings') as mock_settings:
            mock_settings.return_value = Mock(
                is_azure_openai_configured=Mock(return_value=False),
                use_llm_summary=True
            )
            service = ClassificationService()
            result = service.classify_single_news(
                "Test Insurer",
                "Test Title",
                None
            )
            assert result is not None
            assert result.status == "Monitor"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
