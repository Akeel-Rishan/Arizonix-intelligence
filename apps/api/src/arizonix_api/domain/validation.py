"""Cross-record validation for assembled in-memory contract bundles."""

from collections import defaultdict
from typing import Literal
from uuid import UUID

from pydantic import Field

from arizonix_api.domain.claims import (
    Claim,
    ClaimEvidenceRelationship,
    ClaimLifecycleStatus,
    EvidenceRelationshipKind,
)
from arizonix_api.domain.common import ContractModel
from arizonix_api.domain.companies import Company
from arizonix_api.domain.evidence import Evidence
from arizonix_api.domain.research import ResearchProject, ResearchRun
from arizonix_api.domain.reviews import HumanReviewDecision, ReviewArtifactType
from arizonix_api.domain.sources import Source, SourceSnapshot


class DomainBundle(ContractModel):
    contract_version: Literal["1.0"]
    companies: list[Company] = Field(default_factory=list)
    research_projects: list[ResearchProject] = Field(default_factory=list)
    research_runs: list[ResearchRun] = Field(default_factory=list)
    sources: list[Source] = Field(default_factory=list)
    snapshots: list[SourceSnapshot] = Field(default_factory=list)
    evidence: list[Evidence] = Field(default_factory=list)
    claims: list[Claim] = Field(default_factory=list)
    claim_evidence_relationships: list[ClaimEvidenceRelationship] = Field(default_factory=list)
    review_decisions: list[HumanReviewDecision] = Field(default_factory=list)


class DomainIntegrityError(ValueError):
    def __init__(self, errors: list[str]) -> None:
        self.errors = errors
        super().__init__("domain integrity failed:\n- " + "\n- ".join(errors))


def _index(
    records: list[ContractModel], label: str, errors: list[str]
) -> dict[UUID, ContractModel]:
    result: dict[UUID, ContractModel] = {}
    for record in records:
        record_id = record.id
        if record_id in result:
            errors.append(f"duplicate {label} id {record_id}")
        result[record_id] = record
    return result


def _same_owner(child: object, parent: object, relationship: str, errors: list[str]) -> None:
    for field in ("workspace_id", "company_id"):
        if getattr(child, field) != getattr(parent, field):
            errors.append(f"{relationship} has inconsistent {field}")


def validate_domain_bundle(bundle: DomainBundle) -> None:
    """Validate references and ownership; this is not an authorization check."""

    errors: list[str] = []
    companies = _index(bundle.companies, "company", errors)
    projects = _index(bundle.research_projects, "research project", errors)
    runs = _index(bundle.research_runs, "research run", errors)
    sources = _index(bundle.sources, "source", errors)
    snapshots = _index(bundle.snapshots, "snapshot", errors)
    evidence = _index(bundle.evidence, "evidence", errors)
    claims = _index(bundle.claims, "claim", errors)
    _index(bundle.claim_evidence_relationships, "claim-evidence relationship", errors)
    _index(bundle.review_decisions, "review decision", errors)

    company_owned = [
        *bundle.research_projects,
        *bundle.research_runs,
        *bundle.sources,
        *bundle.snapshots,
        *bundle.evidence,
        *bundle.claims,
        *bundle.claim_evidence_relationships,
        *bundle.review_decisions,
    ]
    for record in company_owned:
        company = companies.get(record.company_id)
        if company is None:
            errors.append(
                f"{type(record).__name__} {record.id} references missing company "
                f"{record.company_id}"
            )
        elif record.workspace_id != company.workspace_id:
            errors.append(f"{type(record).__name__} {record.id} has inconsistent workspace_id")

    for project in bundle.research_projects:
        company = companies.get(project.company_id)
        if company is not None and project.workspace_id != company.workspace_id:
            errors.append(f"research project {project.id} crosses workspaces")

    for run in bundle.research_runs:
        project = projects.get(run.project_id)
        if project is None:
            errors.append(f"research run {run.id} references missing project {run.project_id}")
        else:
            _same_owner(run, project, f"research run {run.id} -> project {project.id}", errors)

    for snapshot in bundle.snapshots:
        source = sources.get(snapshot.source_id)
        if source is None:
            errors.append(f"snapshot {snapshot.id} references missing source {snapshot.source_id}")
        else:
            _same_owner(snapshot, source, f"snapshot {snapshot.id} -> source {source.id}", errors)

    for item in bundle.evidence:
        snapshot = snapshots.get(item.source_snapshot_id)
        if snapshot is None:
            errors.append(
                f"evidence {item.id} references missing snapshot {item.source_snapshot_id}"
            )
        else:
            _same_owner(item, snapshot, f"evidence {item.id} -> snapshot {snapshot.id}", errors)

    for claim in bundle.claims:
        if claim.research_run_id is not None:
            run = runs.get(claim.research_run_id)
            if run is None:
                errors.append(f"claim {claim.id} references missing run {claim.research_run_id}")
            else:
                _same_owner(claim, run, f"claim {claim.id} -> run {run.id}", errors)

    relationships_by_claim: dict[UUID, list[ClaimEvidenceRelationship]] = defaultdict(list)
    seen_links: dict[tuple[UUID, int, UUID], EvidenceRelationshipKind] = {}
    for link in bundle.claim_evidence_relationships:
        claim = claims.get(link.claim_id)
        item = evidence.get(link.evidence_id)
        if claim is None:
            errors.append(f"relationship {link.id} references missing claim {link.claim_id}")
        else:
            _same_owner(link, claim, f"relationship {link.id} -> claim {claim.id}", errors)
            if link.claim_version != claim.version:
                errors.append(f"relationship {link.id} references a different claim version")
        if item is None:
            errors.append(f"relationship {link.id} references missing evidence {link.evidence_id}")
        else:
            _same_owner(link, item, f"relationship {link.id} -> evidence {item.id}", errors)

        key = (link.claim_id, link.claim_version, link.evidence_id)
        prior = seen_links.get(key)
        if prior is not None:
            if {prior, link.relationship} == {
                EvidenceRelationshipKind.SUPPORT,
                EvidenceRelationshipKind.CONTRADICTION,
            }:
                errors.append(
                    f"claim {link.claim_id} version {link.claim_version} and evidence "
                    f"{link.evidence_id} conflict as both support and contradiction"
                )
            else:
                errors.append(f"duplicate claim-evidence link for claim {link.claim_id}")
        seen_links[key] = link.relationship
        relationships_by_claim[link.claim_id].append(link)

    for claim in bundle.claims:
        if claim.lifecycle_status is ClaimLifecycleStatus.VERIFIED and not any(
            link.relationship is EvidenceRelationshipKind.SUPPORT
            for link in relationships_by_claim[claim.id]
        ):
            errors.append(f"verified claim {claim.id} has no supporting evidence relationship")

    artifacts: dict[ReviewArtifactType, dict[UUID, ContractModel]] = {
        ReviewArtifactType.RESEARCH_PROJECT: projects,
        ReviewArtifactType.RESEARCH_RUN: runs,
        ReviewArtifactType.CLAIM: claims,
    }
    for decision in bundle.review_decisions:
        if decision.artifact_type is ReviewArtifactType.OUTBOUND_MESSAGE:
            errors.append(
                f"review decision {decision.id} references an outbound message, whose contract "
                "is deferred from domain version 1.0"
            )
            continue
        artifact = artifacts[decision.artifact_type].get(decision.artifact_id)
        if artifact is None:
            errors.append(
                f"review decision {decision.id} references missing {decision.artifact_type.value} "
                f"{decision.artifact_id}"
            )
            continue
        _same_owner(
            decision,
            artifact,
            f"review decision {decision.id} -> artifact {decision.artifact_id}",
            errors,
        )
        artifact_version = getattr(artifact, "version", 1)
        if decision.artifact_version != artifact_version:
            errors.append(f"review decision {decision.id} references a different artifact version")

    if errors:
        raise DomainIntegrityError(errors)
