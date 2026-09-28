from uuid import UUID, uuid4

import pytest

from arizonix_api.domain import (
    ClaimEvidenceRelationship,
    ClaimLifecycleStatus,
    Company,
    DomainIntegrityError,
    EvidenceRelationshipKind,
    validate_domain_bundle,
)
from arizonix_api.evaluation import DEFAULT_FIXTURE_DIRECTORY, load_evaluation_case


def _valid_bundle():
    case = load_evaluation_case(DEFAULT_FIXTURE_DIRECTORY / "eval-002-one-recent-complaint.json")
    return case.inputs


def test_dangling_evidence_reference_is_rejected() -> None:
    bundle = _valid_bundle()
    link = bundle.claim_evidence_relationships[0].model_copy(update={"evidence_id": uuid4()})
    changed = bundle.model_copy(update={"claim_evidence_relationships": [link]})

    with pytest.raises(DomainIntegrityError, match="references missing evidence"):
        validate_domain_bundle(changed)


def test_cross_workspace_record_is_rejected() -> None:
    bundle = _valid_bundle()
    source = bundle.sources[0].model_copy(update={"workspace_id": uuid4()})
    changed = bundle.model_copy(update={"sources": [source]})

    with pytest.raises(DomainIntegrityError, match="inconsistent workspace_id"):
        validate_domain_bundle(changed)


def test_cross_company_relationship_is_rejected() -> None:
    bundle = _valid_bundle()
    second_company_id = UUID("20000000-0000-4000-8000-000000000102")
    second_company = Company(
        id=second_company_id,
        workspace_id=bundle.companies[0].workspace_id,
        name="Another Company",
        created_at=bundle.companies[0].created_at,
    )
    link = bundle.claim_evidence_relationships[0].model_copy(
        update={"company_id": second_company_id}
    )
    changed = bundle.model_copy(
        update={
            "companies": [*bundle.companies, second_company],
            "claim_evidence_relationships": [link],
        }
    )

    with pytest.raises(DomainIntegrityError, match="inconsistent company_id"):
        validate_domain_bundle(changed)


def test_conflicting_support_and_contradiction_are_rejected() -> None:
    bundle = _valid_bundle()
    original = bundle.claim_evidence_relationships[0]
    contradiction = ClaimEvidenceRelationship(
        **original.model_dump(exclude={"id", "relationship"}),
        id=uuid4(),
        relationship=EvidenceRelationshipKind.CONTRADICTION,
    )
    changed = bundle.model_copy(update={"claim_evidence_relationships": [original, contradiction]})

    with pytest.raises(DomainIntegrityError, match="both support and contradiction"):
        validate_domain_bundle(changed)


def test_verified_claim_without_support_is_rejected() -> None:
    bundle = _valid_bundle()
    claim = bundle.claims[0].model_copy(update={"lifecycle_status": ClaimLifecycleStatus.VERIFIED})
    changed = bundle.model_copy(update={"claims": [claim], "claim_evidence_relationships": []})

    with pytest.raises(DomainIntegrityError, match="has no supporting evidence relationship"):
        validate_domain_bundle(changed)
