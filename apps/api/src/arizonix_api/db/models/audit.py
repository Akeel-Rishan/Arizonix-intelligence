from datetime import datetime
from enum import StrEnum
from typing import Any
from uuid import UUID

from sqlalchemy import (
    CheckConstraint,
    DateTime,
    Enum,
    ForeignKey,
    Index,
    SmallInteger,
    String,
    func,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.dialects.postgresql import UUID as PostgreSQLUUID
from sqlalchemy.orm import Mapped, mapped_column

from arizonix_api.db.base import Base


class AuditAction(StrEnum):
    WORKSPACE_CREATED = "workspace.created"
    WORKSPACE_RENAMED = "workspace.renamed"
    MEMBERSHIP_ADDED = "membership.added"
    MEMBERSHIP_ROLE_CHANGED = "membership.role_changed"
    MEMBERSHIP_REMOVED = "membership.removed"
    MEMBERSHIP_LEFT = "membership.left"
    COMPANY_CREATED = "company.created"
    COMPANY_UPDATED = "company.updated"
    COMPANY_ARCHIVED = "company.archived"
    COMPANY_RESTORED = "company.restored"


class AuditEvent(Base):
    __tablename__ = "audit_events"
    __table_args__ = (
        CheckConstraint(
            "target_type IN ('workspace', 'membership', 'company')", name="target_type"
        ),
        CheckConstraint("event_schema_version = 1", name="schema_version"),
        CheckConstraint("jsonb_typeof(details) = 'object'", name="details_object"),
        CheckConstraint("octet_length(details::text) <= 4096", name="details_size"),
        Index("ix_audit_events_workspace_order", "workspace_id", "occurred_at", "id"),
        Index(
            "ix_audit_events_workspace_action_order", "workspace_id", "action", "occurred_at", "id"
        ),
        Index(
            "ix_audit_events_workspace_actor_order",
            "workspace_id",
            "actor_user_id",
            "occurred_at",
            "id",
        ),
    )

    id: Mapped[UUID] = mapped_column(PostgreSQLUUID(as_uuid=True), primary_key=True)
    workspace_id: Mapped[UUID] = mapped_column(
        PostgreSQLUUID(as_uuid=True),
        ForeignKey("arizonix.workspaces.id", ondelete="RESTRICT"),
    )
    actor_user_id: Mapped[UUID] = mapped_column(
        PostgreSQLUUID(as_uuid=True),
        ForeignKey("arizonix.application_users.id", ondelete="RESTRICT"),
    )
    action: Mapped[AuditAction] = mapped_column(
        Enum(
            AuditAction,
            name="audit_action",
            schema="arizonix",
            native_enum=True,
            values_callable=lambda actions: [action.value for action in actions],
        )
    )
    target_type: Mapped[str] = mapped_column(String(32))
    target_id: Mapped[UUID] = mapped_column(PostgreSQLUUID(as_uuid=True))
    occurred_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.clock_timestamp()
    )
    request_id: Mapped[UUID] = mapped_column(PostgreSQLUUID(as_uuid=True))
    event_schema_version: Mapped[int] = mapped_column(SmallInteger, server_default="1")
    details: Mapped[dict[str, Any]] = mapped_column(JSONB, server_default="{}")
