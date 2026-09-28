from datetime import UTC, date, datetime
from uuid import UUID

import pytest
from pydantic import ValidationError

from arizonix_api.domain import (
    CaptureStatus,
    Claim,
    ClaimLifecycleStatus,
    Company,
    DomainBundle,
    EvidentiaryClassification,
    HumanReviewDecision,
    PublicationPrecision,
    ResearchOutcome,
    ResearchProject,
    ResearchRun,
    ReviewArtifactType,
    ReviewDecision,
    ReviewScope,
    RunStatus,
    SourceSnapshot,
)

WORKSPACE_ID = UUID("00000000-0000-4000-8000-000000000001")
COMPANY_ID = UUID("00000000-0000-4000-8000-000000000101")
SOURCE_ID = UUID("00000000-0000-4000-8000-000000000201")
NOW = datetime(2026, 6, 1, tzinfo=UTC)


def test_contracts_construct_and_round_trip_as_json() -> None:
    company = Company(
        id=COMPANY_ID,
        workspace_id=WORKSPACE_ID,
        name="Example Bakery",
        website_url="https://bakery.example",
        created_at=NOW,
    )
    bundle = DomainBundle(contract_version="1.0", companies=[company])

    restored = DomainBundle.model_validate_json(bundle.model_dump_json())

    assert restored == bundle
    assert restored.contract_version == "1.0"


def test_unexpected_fields_are_rejected() -> None:
    with pytest.raises(ValidationError, match="Extra inputs are not permitted"):
        Company(
            id=COMPANY_ID,
            workspace_id=WORKSPACE_ID,
            name="Example Bakery",
            created_at=NOW,
            invented_field=True,
        )


@pytest.mark.parametrize("field", ["created_at", "updated_at"])
def test_naive_timestamps_are_rejected(field: str) -> None:
    values = {
        "id": UUID("00000000-0000-4000-8000-000000000301"),
        "workspace_id": WORKSPACE_ID,
        "company_id": COMPANY_ID,
        "objective": "Assess current service quality.",
        "version": 1,
        "progression": "draft",
        "created_at": NOW,
        "updated_at": NOW,
    }
    values[field] = datetime(2026, 6, 1)

    with pytest.raises(ValidationError, match="timezone offset"):
        ResearchProject(**values)


def test_invalid_date_ordering_is_rejected() -> None:
    with pytest.raises(ValidationError, match="updated_at must not be before created_at"):
        ResearchProject(
            id=UUID("00000000-0000-4000-8000-000000000301"),
            workspace_id=WORKSPACE_ID,
            company_id=COMPANY_ID,
            objective="Assess current service quality.",
            version=1,
            progression="draft",
            created_at=NOW,
            updated_at=datetime(2026, 5, 1, tzinfo=UTC),
        )


def test_research_run_and_versioned_review_construct() -> None:
    project_id = UUID("00000000-0000-4000-8000-000000000301")
    run = ResearchRun(
        id=UUID("00000000-0000-4000-8000-000000000302"),
        workspace_id=WORKSPACE_ID,
        company_id=COMPANY_ID,
        project_id=project_id,
        status=RunStatus.SUCCEEDED,
        queued_at=NOW,
        started_at=datetime(2026, 6, 1, 0, 1, tzinfo=UTC),
        completed_at=datetime(2026, 6, 1, 0, 2, tzinfo=UTC),
        outcome=ResearchOutcome.NO_MEANINGFUL_PROBLEM,
    )
    review = HumanReviewDecision(
        id=UUID("00000000-0000-4000-8000-000000000701"),
        workspace_id=WORKSPACE_ID,
        company_id=COMPANY_ID,
        review_scope=ReviewScope.RESEARCH,
        artifact_type=ReviewArtifactType.RESEARCH_PROJECT,
        artifact_id=project_id,
        artifact_version=2,
        actor_id=UUID("00000000-0000-4000-8000-000000000801"),
        decision=ReviewDecision.CHANGES_REQUESTED,
        decided_at=NOW,
    )

    assert run.outcome is ResearchOutcome.NO_MEANINGFUL_PROBLEM
    assert review.artifact_version == 2


def test_research_run_rejects_reversed_execution_dates() -> None:
    with pytest.raises(ValidationError, match="completed_at must not be before run start"):
        ResearchRun(
            id=UUID("00000000-0000-4000-8000-000000000302"),
            workspace_id=WORKSPACE_ID,
            company_id=COMPANY_ID,
            project_id=UUID("00000000-0000-4000-8000-000000000301"),
            status=RunStatus.FAILED,
            queued_at=NOW,
            started_at=datetime(2026, 6, 1, 0, 2, tzinfo=UTC),
            completed_at=datetime(2026, 6, 1, 0, 1, tzinfo=UTC),
        )


def test_out_of_range_confidence_is_rejected() -> None:
    with pytest.raises(ValidationError, match="less than or equal to 1"):
        Claim(
            id=UUID("00000000-0000-4000-8000-000000000501"),
            workspace_id=WORKSPACE_ID,
            company_id=COMPANY_ID,
            statement="An unsupported claim.",
            version=1,
            lifecycle_status=ClaimLifecycleStatus.DRAFT,
            evidentiary_classification=EvidentiaryClassification.HYPOTHESIS,
            confidence=1.1,
        )


def test_successful_snapshot_requires_provenance_material() -> None:
    with pytest.raises(ValidationError, match="requires content_sha256 and storage_reference"):
        SourceSnapshot(
            id=UUID("00000000-0000-4000-8000-000000000301"),
            workspace_id=WORKSPACE_ID,
            company_id=COMPANY_ID,
            source_id=SOURCE_ID,
            requested_url="https://source.example/page",
            capture_status=CaptureStatus.SUCCESS,
            captured_at=NOW,
        )


def test_failed_snapshot_cannot_claim_captured_material() -> None:
    with pytest.raises(ValidationError, match="must not contain captured material"):
        SourceSnapshot(
            id=UUID("00000000-0000-4000-8000-000000000301"),
            workspace_id=WORKSPACE_ID,
            company_id=COMPANY_ID,
            source_id=SOURCE_ID,
            requested_url="https://source.example/page",
            capture_status=CaptureStatus.FAILED,
            captured_at=NOW,
            content_sha256="a" * 64,
            storage_reference="snapshot://test/failed-page",
        )


def test_unknown_publication_date_remains_unknown_after_recent_capture() -> None:
    snapshot = SourceSnapshot(
        id=UUID("00000000-0000-4000-8000-000000000301"),
        workspace_id=WORKSPACE_ID,
        company_id=COMPANY_ID,
        source_id=SOURCE_ID,
        requested_url="https://source.example/page",
        capture_status=CaptureStatus.SUCCESS,
        captured_at=NOW,
        content_sha256="a" * 64,
        storage_reference="snapshot://test/page",
        publication_precision=PublicationPrecision.UNKNOWN,
    )

    assert snapshot.published_at is None
    assert snapshot.publication_date is None
    assert snapshot.publication_period is None


def test_exact_date_does_not_invent_a_publication_timestamp() -> None:
    snapshot = SourceSnapshot(
        id=UUID("00000000-0000-4000-8000-000000000301"),
        workspace_id=WORKSPACE_ID,
        company_id=COMPANY_ID,
        source_id=SOURCE_ID,
        requested_url="https://source.example/page",
        capture_status=CaptureStatus.SUCCESS,
        captured_at=NOW,
        content_sha256="b" * 64,
        storage_reference="snapshot://test/page",
        publication_precision=PublicationPrecision.EXACT_DATE,
        publication_date=date(2026, 5, 31),
    )

    assert snapshot.published_at is None
    assert snapshot.publication_date == date(2026, 5, 31)
