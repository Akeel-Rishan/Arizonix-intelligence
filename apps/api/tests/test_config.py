import pytest
from pydantic import ValidationError

from arizonix_api.config import AppEnvironment, LogLevel, Settings

SETTING_NAMES = (
    "ARIZONIX_APP_ENVIRONMENT",
    "ARIZONIX_APP_VERSION",
    "ARIZONIX_LOG_LEVEL",
    "ARIZONIX_ALLOWED_ORIGINS",
)


@pytest.fixture(autouse=True)
def clear_settings_environment(monkeypatch: pytest.MonkeyPatch) -> None:
    for name in SETTING_NAMES:
        monkeypatch.delenv(name, raising=False)


def test_local_defaults_are_valid() -> None:
    settings = Settings(_env_file=None)

    assert settings.app_environment is AppEnvironment.DEVELOPMENT
    assert settings.app_version == "0.1.0"
    assert settings.log_level is LogLevel.INFO
    assert settings.allowed_origins == ["http://127.0.0.1:3000", "http://localhost:3000"]


def test_explicit_environment_overrides(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("ARIZONIX_APP_ENVIRONMENT", "production")
    monkeypatch.setenv("ARIZONIX_APP_VERSION", "1.2.3")
    monkeypatch.setenv("ARIZONIX_LOG_LEVEL", "warning")
    monkeypatch.setenv(
        "ARIZONIX_ALLOWED_ORIGINS",
        "https://research.example,http://127.0.0.1:4000/",
    )

    settings = Settings(_env_file=None)

    assert settings.app_environment is AppEnvironment.PRODUCTION
    assert settings.app_version == "1.2.3"
    assert settings.log_level is LogLevel.WARNING
    assert settings.allowed_origins == [
        "https://research.example",
        "http://127.0.0.1:4000",
    ]


@pytest.mark.parametrize(
    ("name", "value", "message"),
    [
        ("ARIZONIX_APP_ENVIRONMENT", "staging", "development, test or production"),
        ("ARIZONIX_APP_VERSION", "   ", "application version must not be empty"),
        ("ARIZONIX_LOG_LEVEL", "verbose", "debug, info, warning, error or critical"),
        ("ARIZONIX_ALLOWED_ORIGINS", "*", "wildcard CORS origins are not allowed"),
        (
            "ARIZONIX_ALLOWED_ORIGINS",
            "http://localhost:3000/path",
            "must not contain a path, query, or fragment",
        ),
    ],
)
def test_invalid_configuration_fails_clearly(
    monkeypatch: pytest.MonkeyPatch,
    name: str,
    value: str,
    message: str,
) -> None:
    monkeypatch.setenv(name, value)

    with pytest.raises(ValidationError) as error:
        Settings(_env_file=None)

    rendered = str(error.value)
    if name in {"ARIZONIX_APP_ENVIRONMENT", "ARIZONIX_LOG_LEVEL"}:
        assert "Input should be" in rendered
    else:
        assert message in rendered


def test_json_array_origins_are_supported(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv(
        "ARIZONIX_ALLOWED_ORIGINS",
        '["http://127.0.0.1:3000", "https://research.example"]',
    )

    settings = Settings(_env_file=None)

    assert settings.allowed_origins == [
        "http://127.0.0.1:3000",
        "https://research.example",
    ]
