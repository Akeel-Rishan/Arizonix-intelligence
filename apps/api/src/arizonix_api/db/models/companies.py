from datetime import datetime
from uuid import UUID, uuid4

from sqlalchemy import CheckConstraint, DateTime, ForeignKey, Index, Integer, String, Text, func
from sqlalchemy.dialects.postgresql import UUID as PostgreSQLUUID
from sqlalchemy.orm import Mapped, mapped_column

from arizonix_api.db.base import Base


class Company(Base):
    __tablename__ = "companies"
    __table_args__ = (
        CheckConstraint("char_length(btrim(name)) BETWEEN 1 AND 200", name="valid_name"),
        CheckConstraint(
            "website_url IS NULL OR (char_length(website_url) <= 2048 AND "
            "website_url ~* '^https?://(\\[[0-9a-f:.]+\\]|[[:alnum:]][[:alnum:].-]*)"
            "(:[0-9]{1,5})?([/?#][^[:space:]]*)?$')",
            name="valid_website_url",
        ),
        CheckConstraint("country_code IS NULL OR country_code ~ '^[A-Z]{2}$'", name="country_code"),
        CheckConstraint("(archived_at IS NULL) = (archived_by IS NULL)", name="archive_metadata"),
        CheckConstraint("version >= 1", name="positive_version"),
        Index("ix_companies_workspace_order", "workspace_id", "archived_at", "created_at", "id"),
        Index("ix_companies_workspace_name", "workspace_id", func.lower("name")),
        Index("ix_companies_workspace_industry", "workspace_id", func.lower("industry")),
        Index("ix_companies_workspace_country", "workspace_id", "country_code"),
    )

    id: Mapped[UUID] = mapped_column(PostgreSQLUUID(as_uuid=True), primary_key=True, default=uuid4)
    workspace_id: Mapped[UUID] = mapped_column(
        PostgreSQLUUID(as_uuid=True),
        ForeignKey("arizonix.workspaces.id", ondelete="RESTRICT"),
    )
    name: Mapped[str] = mapped_column(String(200))
    website_url: Mapped[str | None] = mapped_column(String(2048))
    industry: Mapped[str | None] = mapped_column(String(100))
    country_code: Mapped[str | None] = mapped_column(String(2))
    description: Mapped[str | None] = mapped_column(String(2000))
    notes: Mapped[str | None] = mapped_column(Text)
    created_by: Mapped[UUID] = mapped_column(
        PostgreSQLUUID(as_uuid=True),
        ForeignKey("arizonix.application_users.id", ondelete="RESTRICT"),
    )
    updated_by: Mapped[UUID] = mapped_column(
        PostgreSQLUUID(as_uuid=True),
        ForeignKey("arizonix.application_users.id", ondelete="RESTRICT"),
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.clock_timestamp()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.clock_timestamp()
    )
    archived_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    archived_by: Mapped[UUID | None] = mapped_column(
        PostgreSQLUUID(as_uuid=True),
        ForeignKey("arizonix.application_users.id", ondelete="RESTRICT"),
    )
    version: Mapped[int] = mapped_column(Integer, server_default="1")
