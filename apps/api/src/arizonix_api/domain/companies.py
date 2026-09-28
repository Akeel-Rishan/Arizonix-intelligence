"""Company identity contracts."""

from pydantic import Field, HttpUrl

from arizonix_api.domain.common import AwareDatetime, WorkspaceRecord


class Company(WorkspaceRecord):
    """A workspace-scoped business identity, not an authorization decision."""

    name: str = Field(min_length=1, max_length=300)
    location_label: str | None = Field(default=None, min_length=1, max_length=300)
    website_url: HttpUrl | None = None
    identity_key: str | None = Field(default=None, min_length=1, max_length=500)
    created_at: AwareDatetime
