"""Add workspace-scoped company management.

Revision ID: 20261003_0003
Revises: 20261003_0002
Create Date: 2026-10-03
"""

from collections.abc import Sequence

from alembic import op

revision: str = "20261003_0003"
down_revision: str | None = "20261003_0002"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # PostgreSQL requires newly added enum values to be committed before they are
    # referenced by function bodies later in this migration.
    with op.get_context().autocommit_block():
        op.execute("ALTER TYPE arizonix.audit_action ADD VALUE IF NOT EXISTS 'company.created'")
        op.execute("ALTER TYPE arizonix.audit_action ADD VALUE IF NOT EXISTS 'company.updated'")
        op.execute("ALTER TYPE arizonix.audit_action ADD VALUE IF NOT EXISTS 'company.archived'")
        op.execute("ALTER TYPE arizonix.audit_action ADD VALUE IF NOT EXISTS 'company.restored'")

    sql = r"""
        ALTER TABLE arizonix.audit_events DROP CONSTRAINT ck_audit_events_target_type;
        ALTER TABLE arizonix.audit_events ADD CONSTRAINT ck_audit_events_target_type
          CHECK (target_type IN ('workspace', 'membership', 'company'));

        CREATE TABLE arizonix.companies (
          id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
          workspace_id uuid NOT NULL REFERENCES arizonix.workspaces(id) ON DELETE RESTRICT,
          name varchar(200) NOT NULL,
          website_url varchar(2048),
          industry varchar(100),
          country_code varchar(2),
          description varchar(2000),
          notes text,
          created_by uuid NOT NULL REFERENCES arizonix.application_users(id) ON DELETE RESTRICT,
          updated_by uuid NOT NULL REFERENCES arizonix.application_users(id) ON DELETE RESTRICT,
          created_at timestamptz NOT NULL DEFAULT clock_timestamp(),
          updated_at timestamptz NOT NULL DEFAULT clock_timestamp(),
          archived_at timestamptz,
          archived_by uuid REFERENCES arizonix.application_users(id) ON DELETE RESTRICT,
          version integer NOT NULL DEFAULT 1,
          CONSTRAINT ck_companies_valid_name CHECK (char_length(btrim(name)) BETWEEN 1 AND 200),
          CONSTRAINT ck_companies_valid_website_url CHECK (
            website_url IS NULL OR (
              char_length(website_url) <= 2048
              AND website_url ~* '^https?://(\[[0-9a-f:.]+\]|[[:alnum:]][[:alnum:].-]*)(:[0-9]{1,5})?([/?#][^[:space:]]*)?$'
            )
          ),
          CONSTRAINT ck_companies_country_code
            CHECK (country_code IS NULL OR country_code ~ '^[A-Z]{2}$'),
          CONSTRAINT ck_companies_archive_metadata
            CHECK ((archived_at IS NULL) = (archived_by IS NULL)),
          CONSTRAINT ck_companies_positive_version CHECK (version >= 1),
          CONSTRAINT ck_companies_industry_length
            CHECK (industry IS NULL OR char_length(industry) <= 100),
          CONSTRAINT ck_companies_description_length
            CHECK (description IS NULL OR char_length(description) <= 2000),
          CONSTRAINT ck_companies_notes_length
            CHECK (notes IS NULL OR char_length(notes) <= 5000)
        );
        CREATE INDEX ix_companies_workspace_order
          ON arizonix.companies (workspace_id, archived_at, created_at DESC, id DESC);
        CREATE INDEX ix_companies_workspace_name
          ON arizonix.companies (workspace_id, lower(name));
        CREATE INDEX ix_companies_workspace_industry
          ON arizonix.companies (workspace_id, lower(industry));
        CREATE INDEX ix_companies_workspace_country
          ON arizonix.companies (workspace_id, country_code);
        ALTER TABLE arizonix.companies OWNER TO arizonix_owner;
        ALTER TABLE arizonix.companies ENABLE ROW LEVEL SECURITY;
        CREATE POLICY companies_select ON arizonix.companies
          FOR SELECT TO arizonix_runtime
          USING (arizonix.is_workspace_member(workspace_id));

        CREATE FUNCTION arizonix.company_actor_role(p_workspace_id uuid)
        RETURNS arizonix.workspace_role
        LANGUAGE plpgsql STABLE SECURITY DEFINER
        SET search_path = ''
        AS $function$
        DECLARE selected_role arizonix.workspace_role;
        BEGIN
          SELECT m.role INTO selected_role FROM arizonix.memberships m
            WHERE m.workspace_id = p_workspace_id
              AND m.user_id = arizonix.current_user_id();
          IF selected_role IS NULL THEN
            RAISE EXCEPTION 'workspace is unavailable' USING ERRCODE = 'AR004';
          END IF;
          RETURN selected_role;
        END
        $function$;
        ALTER FUNCTION arizonix.company_actor_role(uuid) OWNER TO arizonix_owner;

        CREATE FUNCTION arizonix.create_company(
          p_workspace_id uuid, p_name text, p_website_url text, p_industry text,
          p_country_code text, p_description text, p_notes text
        ) RETURNS uuid
        LANGUAGE plpgsql SECURITY DEFINER
        SET search_path = ''
        AS $function$
        DECLARE
          actor uuid := arizonix.current_user_id();
          actor_role arizonix.workspace_role;
          company_id uuid;
        BEGIN
          actor_role := arizonix.company_actor_role(p_workspace_id);
          IF actor_role = 'viewer' THEN
            RAISE EXCEPTION 'permission denied' USING ERRCODE = 'AR003';
          END IF;
          INSERT INTO arizonix.companies (
            workspace_id, name, website_url, industry, country_code, description, notes,
            created_by, updated_by
          ) VALUES (
            p_workspace_id, btrim(p_name), nullif(btrim(p_website_url), ''),
            nullif(btrim(p_industry), ''), upper(nullif(btrim(p_country_code), '')),
            nullif(btrim(p_description), ''), nullif(btrim(p_notes), ''), actor, actor
          ) RETURNING id INTO company_id;
          PERFORM arizonix.write_audit_event(
            p_workspace_id, 'company.created', 'company', company_id,
            jsonb_build_object('name', btrim(p_name), 'version', 1)
          );
          RETURN company_id;
        END
        $function$;
        ALTER FUNCTION arizonix.create_company(uuid, text, text, text, text, text, text)
          OWNER TO arizonix_owner;

        CREATE FUNCTION arizonix.update_company(
          p_workspace_id uuid, p_company_id uuid, p_expected_version integer,
          p_set_name boolean, p_name text,
          p_set_website_url boolean, p_website_url text,
          p_set_industry boolean, p_industry text,
          p_set_country_code boolean, p_country_code text,
          p_set_description boolean, p_description text,
          p_set_notes boolean, p_notes text
        ) RETURNS uuid
        LANGUAGE plpgsql SECURITY DEFINER
        SET search_path = ''
        AS $function$
        DECLARE
          actor uuid := arizonix.current_user_id();
          actor_role arizonix.workspace_role;
          existing arizonix.companies%ROWTYPE;
          next_name text;
          next_website text;
          next_industry text;
          next_country text;
          next_description text;
          next_notes text;
          changed_fields jsonb := '[]'::jsonb;
        BEGIN
          actor_role := arizonix.company_actor_role(p_workspace_id);
          IF actor_role = 'viewer' THEN
            RAISE EXCEPTION 'permission denied' USING ERRCODE = 'AR003';
          END IF;
          SELECT c.* INTO existing FROM arizonix.companies c
            WHERE c.id = p_company_id AND c.workspace_id = p_workspace_id FOR UPDATE;
          IF NOT FOUND THEN
            RAISE EXCEPTION 'company is unavailable' USING ERRCODE = 'AR010';
          END IF;
          IF existing.version <> p_expected_version THEN
            RAISE EXCEPTION 'company version is stale' USING ERRCODE = 'AR008';
          END IF;
          IF existing.archived_at IS NOT NULL THEN
            RAISE EXCEPTION 'archived company cannot be edited' USING ERRCODE = 'AR009';
          END IF;

          next_name := CASE WHEN p_set_name THEN btrim(p_name) ELSE existing.name END;
          next_website := CASE WHEN p_set_website_url
            THEN nullif(btrim(p_website_url), '') ELSE existing.website_url END;
          next_industry := CASE WHEN p_set_industry
            THEN nullif(btrim(p_industry), '') ELSE existing.industry END;
          next_country := CASE WHEN p_set_country_code
            THEN upper(nullif(btrim(p_country_code), '')) ELSE existing.country_code END;
          next_description := CASE WHEN p_set_description
            THEN nullif(btrim(p_description), '') ELSE existing.description END;
          next_notes := CASE WHEN p_set_notes
            THEN nullif(btrim(p_notes), '') ELSE existing.notes END;

          IF existing.name IS DISTINCT FROM next_name THEN
            changed_fields := changed_fields || '"name"'::jsonb;
          END IF;
          IF existing.website_url IS DISTINCT FROM next_website THEN
            changed_fields := changed_fields || '"website_url"'::jsonb;
          END IF;
          IF existing.industry IS DISTINCT FROM next_industry THEN
            changed_fields := changed_fields || '"industry"'::jsonb;
          END IF;
          IF existing.country_code IS DISTINCT FROM next_country THEN
            changed_fields := changed_fields || '"country_code"'::jsonb;
          END IF;
          IF existing.description IS DISTINCT FROM next_description THEN
            changed_fields := changed_fields || '"description"'::jsonb;
          END IF;
          IF existing.notes IS DISTINCT FROM next_notes THEN
            changed_fields := changed_fields || '"notes"'::jsonb;
          END IF;
          IF jsonb_array_length(changed_fields) = 0 THEN RETURN p_company_id; END IF;

          UPDATE arizonix.companies SET
            name = next_name, website_url = next_website, industry = next_industry,
            country_code = next_country, description = next_description, notes = next_notes,
            updated_by = actor, updated_at = clock_timestamp(), version = version + 1
          WHERE id = p_company_id;
          PERFORM arizonix.write_audit_event(
            p_workspace_id, 'company.updated', 'company', p_company_id,
            jsonb_strip_nulls(jsonb_build_object(
              'previous_version', existing.version, 'new_version', existing.version + 1,
              'changed_fields', changed_fields,
              'previous_name', CASE WHEN p_set_name THEN existing.name END,
              'new_name', CASE WHEN p_set_name THEN next_name END,
              'previous_industry', CASE WHEN p_set_industry THEN existing.industry END,
              'new_industry', CASE WHEN p_set_industry THEN next_industry END,
              'previous_country_code', CASE WHEN p_set_country_code THEN existing.country_code END,
              'new_country_code', CASE WHEN p_set_country_code THEN next_country END,
              'website_url_changed', existing.website_url IS DISTINCT FROM next_website,
              'description_changed', existing.description IS DISTINCT FROM next_description,
              'notes_changed', existing.notes IS DISTINCT FROM next_notes
            ))
          );
          RETURN p_company_id;
        END
        $function$;
        ALTER FUNCTION arizonix.update_company(
          uuid, uuid, integer, boolean, text, boolean, text, boolean, text,
          boolean, text, boolean, text, boolean, text
        ) OWNER TO arizonix_owner;

        CREATE FUNCTION arizonix.set_company_archived(
          p_workspace_id uuid, p_company_id uuid, p_expected_version integer, p_archived boolean
        ) RETURNS uuid
        LANGUAGE plpgsql SECURITY DEFINER
        SET search_path = ''
        AS $function$
        DECLARE
          actor uuid := arizonix.current_user_id();
          actor_role arizonix.workspace_role;
          existing arizonix.companies%ROWTYPE;
        BEGIN
          actor_role := arizonix.company_actor_role(p_workspace_id);
          IF actor_role = 'viewer' THEN
            RAISE EXCEPTION 'permission denied' USING ERRCODE = 'AR003';
          END IF;
          SELECT c.* INTO existing FROM arizonix.companies c
            WHERE c.id = p_company_id AND c.workspace_id = p_workspace_id FOR UPDATE;
          IF NOT FOUND THEN
            RAISE EXCEPTION 'company is unavailable' USING ERRCODE = 'AR010';
          END IF;
          IF existing.version <> p_expected_version THEN
            RAISE EXCEPTION 'company version is stale' USING ERRCODE = 'AR008';
          END IF;
          IF (p_archived AND existing.archived_at IS NOT NULL)
             OR (NOT p_archived AND existing.archived_at IS NULL) THEN
            RETURN p_company_id;
          END IF;
          UPDATE arizonix.companies SET
            archived_at = CASE WHEN p_archived THEN clock_timestamp() ELSE NULL END,
            archived_by = CASE WHEN p_archived THEN actor ELSE NULL END,
            updated_by = actor, updated_at = clock_timestamp(), version = version + 1
          WHERE id = p_company_id;
          PERFORM arizonix.write_audit_event(
            p_workspace_id,
            CASE WHEN p_archived THEN 'company.archived'::arizonix.audit_action
                 ELSE 'company.restored'::arizonix.audit_action END,
            'company', p_company_id,
            jsonb_build_object(
              'previous_version', existing.version, 'new_version', existing.version + 1
            )
          );
          RETURN p_company_id;
        END
        $function$;
        ALTER FUNCTION arizonix.set_company_archived(uuid, uuid, integer, boolean)
          OWNER TO arizonix_owner;

        REVOKE ALL ON arizonix.companies FROM PUBLIC, arizonix_runtime;
        REVOKE ALL ON FUNCTION arizonix.company_actor_role(uuid) FROM PUBLIC, arizonix_runtime;
        REVOKE ALL ON FUNCTION arizonix.create_company(uuid, text, text, text, text, text, text)
          FROM PUBLIC, arizonix_runtime;
        REVOKE ALL ON FUNCTION arizonix.update_company(
          uuid, uuid, integer, boolean, text, boolean, text, boolean, text,
          boolean, text, boolean, text, boolean, text
        ) FROM PUBLIC, arizonix_runtime;
        REVOKE ALL ON FUNCTION arizonix.set_company_archived(uuid, uuid, integer, boolean)
          FROM PUBLIC, arizonix_runtime;
        GRANT SELECT ON arizonix.companies TO arizonix_runtime;
        GRANT EXECUTE ON FUNCTION arizonix.create_company(uuid, text, text, text, text, text, text)
          TO arizonix_runtime;
        GRANT EXECUTE ON FUNCTION arizonix.update_company(
          uuid, uuid, integer, boolean, text, boolean, text, boolean, text,
          boolean, text, boolean, text, boolean, text
        ) TO arizonix_runtime;
        GRANT EXECUTE ON FUNCTION arizonix.set_company_archived(uuid, uuid, integer, boolean)
          TO arizonix_runtime;
    """

    async def execute_script(driver_connection) -> None:  # type: ignore[no-untyped-def]
        await driver_connection.execute(sql)

    op.get_bind().connection.run_async(execute_script)


def downgrade() -> None:
    raise RuntimeError("Downgrading across the company audit boundary is intentionally unsupported")
