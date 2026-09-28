"""Offline validation for versioned synthetic evaluation cases."""

import argparse
import json
import sys
from collections.abc import Sequence
from pathlib import Path
from typing import Literal
from uuid import UUID

from pydantic import Field, ValidationError, model_validator

from arizonix_api.domain.claims import ClaimLifecycleStatus, EvidentiaryClassification
from arizonix_api.domain.common import CONTRACT_VERSION, AwareDatetime, Confidence, ContractModel
from arizonix_api.domain.research import ResearchOutcome
from arizonix_api.domain.validation import (
    DomainBundle,
    DomainIntegrityError,
    validate_domain_bundle,
)

EVALUATION_SCHEMA_VERSION = "1.0"
REPOSITORY_ROOT = Path(__file__).resolve().parents[4]
DEFAULT_FIXTURE_DIRECTORY = REPOSITORY_ROOT / "evals" / "fixtures"
DEFAULT_SCHEMA_PATH = REPOSITORY_ROOT / "evals" / "schema" / "case.schema.json"


class ExpectedClaimConstraint(ContractModel):
    claim_id: UUID | None = None
    allowed_classifications: list[EvidentiaryClassification] = Field(default_factory=list)
    forbidden_lifecycle_statuses: list[ClaimLifecycleStatus] = Field(default_factory=list)
    maximum_confidence: Confidence | None = None
    requirement: str = Field(min_length=1, max_length=2000)


class EvaluationCase(ContractModel):
    schema_version: Literal["1.0"]
    contract_version: Literal["1.0"]
    case_id: str = Field(pattern=r"^EVAL-[0-9]{3}$")
    description: str = Field(min_length=1, max_length=2000)
    as_of: AwareDatetime
    synthetic: Literal[True]
    inputs: DomainBundle
    expected_research_outcome: ResearchOutcome
    expected_claim_constraints: list[ExpectedClaimConstraint] = Field(min_length=1)
    required_behaviors: list[str] = Field(min_length=1)
    forbidden_conclusions: list[str] = Field(min_length=1)
    rationale: str = Field(min_length=1, max_length=5000)

    @model_validator(mode="after")
    def validate_nonblank_expectations(self) -> "EvaluationCase":
        for field_name in ("required_behaviors", "forbidden_conclusions"):
            values = getattr(self, field_name)
            if any(not value.strip() for value in values):
                raise ValueError(f"{field_name} must not contain blank values")
        return self


class FixtureValidationError(ValueError):
    pass


def generated_evaluation_schema() -> dict[str, object]:
    schema = EvaluationCase.model_json_schema(mode="validation")
    schema["$id"] = (
        f"https://arizonix.example/schemas/evaluation-case-{EVALUATION_SCHEMA_VERSION}.json"
    )
    return schema


def write_evaluation_schema(path: Path = DEFAULT_SCHEMA_PATH) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(generated_evaluation_schema(), indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )


def validate_schema_file(path: Path = DEFAULT_SCHEMA_PATH) -> None:
    try:
        committed = json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError as error:
        raise FixtureValidationError(f"schema file is missing: {path}") from error
    except json.JSONDecodeError as error:
        raise FixtureValidationError(f"schema file is invalid JSON: {path}: {error}") from error
    if committed != generated_evaluation_schema():
        raise FixtureValidationError(
            f"generated schema differs from {path}; run the schema generation command"
        )


def load_evaluation_case(path: Path) -> EvaluationCase:
    try:
        case = EvaluationCase.model_validate_json(path.read_text(encoding="utf-8"))
        validate_domain_bundle(case.inputs)
        return case
    except FileNotFoundError as error:
        raise FixtureValidationError(f"fixture is missing: {path}") from error
    except (ValidationError, DomainIntegrityError, ValueError) as error:
        raise FixtureValidationError(f"invalid fixture {path}: {error}") from error


def validate_fixture_directory(
    fixture_directory: Path = DEFAULT_FIXTURE_DIRECTORY,
    schema_path: Path = DEFAULT_SCHEMA_PATH,
) -> list[EvaluationCase]:
    validate_schema_file(schema_path)
    paths = sorted(fixture_directory.glob("*.json"))
    if not paths:
        raise FixtureValidationError(f"no JSON fixtures found in {fixture_directory}")

    cases: list[EvaluationCase] = []
    seen_case_ids: set[str] = set()
    for path in paths:
        case = load_evaluation_case(path)
        if case.case_id in seen_case_ids:
            raise FixtureValidationError(f"duplicate case_id {case.case_id} in {path}")
        expected_filename = f"{case.case_id.lower()}-{path.stem.split('-', 2)[-1]}.json"
        if path.name != expected_filename:
            raise FixtureValidationError(
                f"fixture {path} must start with its lowercase case ID {case.case_id.lower()}"
            )
        seen_case_ids.add(case.case_id)
        cases.append(case)
    return cases


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--fixtures", type=Path, default=DEFAULT_FIXTURE_DIRECTORY)
    parser.add_argument("--schema", type=Path, default=DEFAULT_SCHEMA_PATH)
    parser.add_argument(
        "--write-schema",
        action="store_true",
        help="regenerate the committed JSON Schema before validating fixtures",
    )
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    args = _parser().parse_args(argv)
    try:
        if args.write_schema:
            write_evaluation_schema(args.schema)
        cases = validate_fixture_directory(args.fixtures, args.schema)
    except FixtureValidationError as error:
        print(error, file=sys.stderr)
        return 1
    print(f"Validated {len(cases)} synthetic evaluation cases against contract {CONTRACT_VERSION}.")
    print("Model behavior evaluation is NOT IMPLEMENTED; no network or model calls were made.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
