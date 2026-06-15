import pytest

from src.settings import get_settings, require_env


def test_require_env_raises_when_missing(monkeypatch):
    monkeypatch.delenv("MISSING_TEST_VAR", raising=False)

    with pytest.raises(RuntimeError) as exc_info:
        require_env("MISSING_TEST_VAR")

    assert "MISSING_TEST_VAR" in str(exc_info.value)


def test_get_settings_loads_required_values(monkeypatch):
    monkeypatch.setenv("AZURE_OPENAI_ENDPOINT", "https://example.openai.azure.com")
    monkeypatch.setenv("AZURE_OPENAI_API_VERSION", "2024-10-21")
    monkeypatch.setenv("AZURE_OPENAI_CHAT_DEFAULT_DEPLOYMENT", "chat-default")
    monkeypatch.setenv("AZURE_OPENAI_CHAT_FAST_DEPLOYMENT", "chat-fast")
    monkeypatch.setenv("AZURE_OPENAI_CHAT_QUALITY_DEPLOYMENT", "chat-quality")
    monkeypatch.setenv("DEFAULT_CHAT_MODEL", "chat_default")

    monkeypatch.setenv("AGENT_PROMPT_VERSION", "v1")
    monkeypatch.setenv("AGENT_PROMPT_PROFILE", "default")
    monkeypatch.setenv("AGENT_ENVIRONMENT", "test")
    monkeypatch.setenv("AGENT_ALLOWED_SERVICES", "vpn, correo, sharepoint, erp")

    settings = get_settings()

    assert settings.azure_openai_endpoint == "https://example.openai.azure.com"
    assert settings.chat_default_deployment == "chat-default"
    assert settings.default_chat_model == "chat_default"
    assert settings.agent_prompt_version == "v1"
    assert settings.agent_prompt_profile == "default"