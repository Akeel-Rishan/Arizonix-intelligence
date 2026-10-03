import pytest
from pydantic import ValidationError

from arizonix_api.schemas.companies import CompanyCreate, CompanyUpdate


def test_company_create_normalizes_values_and_accepts_unicode() -> None:
    payload = CompanyCreate(
        name="  株式会社 Arizonix  ",
        website_url=" https://example.test/path ",
        industry="  Research  ",
        country_code="lk",
        description="   ",
        notes=None,
    )
    assert payload.name == "株式会社 Arizonix"
    assert payload.website_url == "https://example.test/path"
    assert payload.industry == "Research"
    assert payload.country_code == "LK"
    assert payload.description is None


@pytest.mark.parametrize(
    "website",
    ["example.test", "ftp://example.test", "https://user:secret@example.test", "https://bad host"],
)
def test_company_create_rejects_unsafe_or_ambiguous_urls(website: str) -> None:
    with pytest.raises(ValidationError):
        CompanyCreate(name="Example", website_url=website)


def test_company_update_distinguishes_omitted_fields_from_explicit_null() -> None:
    payload = CompanyUpdate(expected_version=3, industry=None)
    assert payload.model_fields_set == {"expected_version", "industry"}
    assert payload.industry is None


def test_company_update_rejects_empty_patch_null_name_and_extra_fields() -> None:
    with pytest.raises(ValidationError):
        CompanyUpdate(expected_version=1)
    with pytest.raises(ValidationError):
        CompanyUpdate(expected_version=1, name=None)
    with pytest.raises(ValidationError):
        CompanyCreate(name="Example", created_by="not-accepted")
