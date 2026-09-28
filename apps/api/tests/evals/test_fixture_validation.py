import json
from pathlib import Path
from tempfile import TemporaryDirectory

import pytest

from arizonix_api.evaluation import (
    DEFAULT_FIXTURE_DIRECTORY,
    DEFAULT_SCHEMA_PATH,
    FixtureValidationError,
    generated_evaluation_schema,
    validate_fixture_directory,
)


def test_all_synthetic_fixtures_validate() -> None:
    cases = validate_fixture_directory()

    assert len(cases) == 12
    assert len({case.case_id for case in cases}) == 12
    assert all(case.synthetic is True for case in cases)


def test_fixture_validation_reports_the_file_and_fields() -> None:
    with TemporaryDirectory(prefix="arizonix-eval-") as directory:
        fixture_directory = Path(directory)
        fixture = fixture_directory / "eval-999-invalid.json"
        fixture.write_text('{"case_id": "EVAL-999"}', encoding="utf-8")

        with pytest.raises(FixtureValidationError) as caught:
            validate_fixture_directory(fixture_directory, DEFAULT_SCHEMA_PATH)

        message = str(caught.value)
        assert str(fixture) in message
        assert "schema_version" in message
        assert "expected_research_outcome" in message


def test_generated_schema_matches_committed_schema() -> None:
    committed = json.loads(DEFAULT_SCHEMA_PATH.read_text(encoding="utf-8"))

    assert committed == generated_evaluation_schema()


def test_fixture_directory_does_not_contain_real_domains() -> None:
    for path in DEFAULT_FIXTURE_DIRECTORY.glob("*.json"):
        contents = path.read_text(encoding="utf-8")
        assert ".com" not in contents
        assert ".net" not in contents
        assert ".org" not in contents
