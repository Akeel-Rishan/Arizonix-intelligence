from arizonix_api.config import Settings


def test_allowed_origins_accepts_comma_separated_environment_value(monkeypatch) -> None:
    monkeypatch.setenv(
        "ARIZONIX_ALLOWED_ORIGINS",
        "http://127.0.0.1:3000,http://localhost:3000",
    )

    settings = Settings()

    assert settings.allowed_origins == ["http://127.0.0.1:3000", "http://localhost:3000"]
