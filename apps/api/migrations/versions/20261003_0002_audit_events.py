"""Add append-only workspace audit events.

Revision ID: 20261003_0002
Revises: 20260928_0001
Create Date: 2026-10-03
"""

from collections.abc import Sequence

from alembic import op

revision: str = "20261003_0002"
down_revision: str | None = "20260928_0001"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    sql = r"""
        CREATE TYPE arizonix.audit_action AS ENUM (
          'workspace.created',
          'workspace.renamed',
          'membership.added',
          'membership.role_changed',
          'membership.removed',
          'membership.left'
        );
        ALTER TYPE arizonix.audit_action OWNER TO arizonix_owner;

        CREATE TABLE arizonix.audit_events (
          id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
          workspace_id uuid NOT NULL REFERENCES arizonix.workspaces(id) ON DELETE RESTRICT,
          actor_user_id uuid NOT NULL REFERENCES arizonix.application_users(id) ON DELETE RESTRICT,
          action arizonix.audit_action NOT NULL,
          target_type varchar(32) NOT NULL,
          target_id uuid NOT NULL,
          occurred_at timestamptz NOT NULL DEFAULT clock_timestamp(),
          request_id uuid NOT NULL,
          event_schema_version smallint NOT NULL DEFAULT 1,
          details jsonb NOT NULL DEFAULT '{}'::jsonb,
          CONSTRAINT ck_audit_events_target_type
            CHECK (target_type IN ('workspace', 'membership')),
          CONSTRAINT ck_audit_events_schema_version
            CHECK (event_schema_version = 1),
          CONSTRAINT ck_audit_events_details_object
            CHECK (jsonb_typeof(details) = 'object'),
          CONSTRAINT ck_audit_events_details_size
            CHECK (octet_length(details::text) <= 4096)
        );
        CREATE INDEX ix_audit_events_workspace_order
          ON arizonix.audit_events (workspace_id, occurred_at DESC, id DESC);
        CREATE INDEX ix_audit_events_workspace_action_order
          ON arizonix.audit_events (workspace_id, action, occurred_at DESC, id DESC);
        CREATE INDEX ix_audit_events_workspace_actor_order
          ON arizonix.audit_events (workspace_id, actor_user_id, occurred_at DESC, id DESC);
        ALTER TABLE arizonix.audit_events OWNER TO arizonix_owner;
        ALTER TABLE arizonix.audit_events ENABLE ROW LEVEL SECURITY;

        CREATE FUNCTION arizonix.current_request_id() RETURNS uuid
        LANGUAGE sql STABLE
        SET search_path = ''
        AS $function$
          SELECT nullif(current_setting('arizonix.request_id', true), '')::uuid
        $function$;
        ALTER FUNCTION arizonix.current_request_id() OWNER TO arizonix_owner;

        CREATE FUNCTION arizonix.can_read_audit(p_workspace_id uuid) RETURNS boolean
        LANGUAGE sql STABLE SECURITY DEFINER
        SET search_path = ''
        AS $function$
          SELECT arizonix.current_user_id() IS NOT NULL AND EXISTS (
            SELECT 1 FROM arizonix.memberships m
            WHERE m.workspace_id = p_workspace_id
              AND m.user_id = arizonix.current_user_id()
              AND m.role IN ('owner', 'admin')
          )
        $function$;
        ALTER FUNCTION arizonix.can_read_audit(uuid) OWNER TO arizonix_owner;

        CREATE POLICY audit_events_select ON arizonix.audit_events
          FOR SELECT TO arizonix_runtime
          USING (arizonix.can_read_audit(workspace_id));

        CREATE FUNCTION arizonix.write_audit_event(
          p_workspace_id uuid,
          p_action arizonix.audit_action,
          p_target_type text,
          p_target_id uuid,
          p_details jsonb
        ) RETURNS void
        LANGUAGE plpgsql SECURITY DEFINER
        SET search_path = ''
        AS $function$
        DECLARE
          actor uuid := arizonix.current_user_id();
          correlation uuid := arizonix.current_request_id();
        BEGIN
          IF actor IS NULL OR correlation IS NULL THEN
            RAISE EXCEPTION 'audit context is unavailable' USING ERRCODE = 'AR007';
          END IF;
          INSERT INTO arizonix.audit_events (
            workspace_id, actor_user_id, action, target_type, target_id, request_id, details
          ) VALUES (
            p_workspace_id, actor, p_action, p_target_type, p_target_id, correlation, p_details
          );
        EXCEPTION WHEN SQLSTATE 'AR007' THEN
          RAISE;
        WHEN OTHERS THEN
          RAISE EXCEPTION 'audit persistence failed' USING ERRCODE = 'AR007';
        END
        $function$;
        ALTER FUNCTION arizonix.write_audit_event(
          uuid, arizonix.audit_action, text, uuid, jsonb
        ) OWNER TO arizonix_owner;

        CREATE OR REPLACE FUNCTION arizonix.create_workspace(p_name text) RETURNS uuid
        LANGUAGE plpgsql SECURITY DEFINER
        SET search_path = ''
        AS $function$
        DECLARE
          actor uuid := arizonix.current_user_id();
          new_workspace_id uuid;
          normalized_name text := btrim(p_name);
        BEGIN
          IF actor IS NULL THEN
            RAISE EXCEPTION 'identity is required' USING ERRCODE = 'AR003';
          END IF;
          IF NOT EXISTS (SELECT 1 FROM arizonix.application_users u WHERE u.id = actor) THEN
            RAISE EXCEPTION 'application user is unavailable' USING ERRCODE = 'AR005';
          END IF;
          INSERT INTO arizonix.workspaces (name, created_by)
          VALUES (normalized_name, actor)
          RETURNING id INTO new_workspace_id;
          INSERT INTO arizonix.memberships (workspace_id, user_id, role)
          VALUES (new_workspace_id, actor, 'owner');
          PERFORM arizonix.write_audit_event(
            new_workspace_id, 'workspace.created', 'workspace', new_workspace_id,
            jsonb_build_object('name', normalized_name)
          );
          RETURN new_workspace_id;
        END
        $function$;

        CREATE OR REPLACE FUNCTION arizonix.rename_workspace(
          p_workspace_id uuid, p_name text
        ) RETURNS void
        LANGUAGE plpgsql SECURITY DEFINER
        SET search_path = ''
        AS $function$
        DECLARE
          actor_role arizonix.workspace_role;
          previous_name text;
          normalized_name text := btrim(p_name);
        BEGIN
          SELECT w.name INTO previous_name FROM arizonix.workspaces w
            WHERE w.id = p_workspace_id FOR UPDATE;
          IF NOT FOUND THEN
            RAISE EXCEPTION 'workspace is unavailable' USING ERRCODE = 'AR004';
          END IF;
          SELECT m.role INTO actor_role FROM arizonix.memberships m
            WHERE m.workspace_id = p_workspace_id AND m.user_id = arizonix.current_user_id();
          IF actor_role IS NULL THEN
            RAISE EXCEPTION 'workspace is unavailable' USING ERRCODE = 'AR004';
          END IF;
          IF actor_role NOT IN ('owner', 'admin') THEN
            RAISE EXCEPTION 'permission denied' USING ERRCODE = 'AR003';
          END IF;
          IF previous_name = normalized_name THEN
            RETURN;
          END IF;
          UPDATE arizonix.workspaces SET name = normalized_name WHERE id = p_workspace_id;
          PERFORM arizonix.write_audit_event(
            p_workspace_id, 'workspace.renamed', 'workspace', p_workspace_id,
            jsonb_build_object('previous_name', previous_name, 'new_name', normalized_name)
          );
        END
        $function$;

        CREATE OR REPLACE FUNCTION arizonix.add_workspace_member(
          p_workspace_id uuid, p_user_id uuid, p_role text
        ) RETURNS void
        LANGUAGE plpgsql SECURITY DEFINER
        SET search_path = ''
        AS $function$
        DECLARE
          actor_role arizonix.workspace_role;
          requested_role arizonix.workspace_role := p_role::arizonix.workspace_role;
        BEGIN
          PERFORM 1 FROM arizonix.workspaces w WHERE w.id = p_workspace_id FOR UPDATE;
          IF NOT FOUND THEN
            RAISE EXCEPTION 'workspace is unavailable' USING ERRCODE = 'AR004';
          END IF;
          SELECT m.role INTO actor_role FROM arizonix.memberships m
            WHERE m.workspace_id = p_workspace_id AND m.user_id = arizonix.current_user_id();
          IF actor_role IS NULL THEN
            RAISE EXCEPTION 'workspace is unavailable' USING ERRCODE = 'AR004';
          END IF;
          IF actor_role <> 'owner' AND NOT (
            actor_role = 'admin' AND requested_role IN ('analyst', 'viewer')
          ) THEN RAISE EXCEPTION 'permission denied' USING ERRCODE = 'AR003'; END IF;
          IF NOT EXISTS (SELECT 1 FROM arizonix.application_users u WHERE u.id = p_user_id) THEN
            RAISE EXCEPTION 'application user is unavailable' USING ERRCODE = 'AR005';
          END IF;
          BEGIN
            INSERT INTO arizonix.memberships (workspace_id, user_id, role)
            VALUES (p_workspace_id, p_user_id, requested_role);
          EXCEPTION WHEN unique_violation THEN
            RAISE EXCEPTION 'duplicate membership' USING ERRCODE = 'AR001';
          END;
          PERFORM arizonix.write_audit_event(
            p_workspace_id, 'membership.added', 'membership', p_user_id,
            jsonb_build_object('target_user_id', p_user_id, 'assigned_role', requested_role)
          );
        END
        $function$;

        CREATE OR REPLACE FUNCTION arizonix.change_workspace_member_role(
          p_workspace_id uuid, p_user_id uuid, p_role text
        ) RETURNS void
        LANGUAGE plpgsql SECURITY DEFINER
        SET search_path = ''
        AS $function$
        DECLARE
          actor_role arizonix.workspace_role;
          existing_role arizonix.workspace_role;
          requested_role arizonix.workspace_role := p_role::arizonix.workspace_role;
          owner_count integer;
        BEGIN
          PERFORM 1 FROM arizonix.workspaces w WHERE w.id = p_workspace_id FOR UPDATE;
          IF NOT FOUND THEN
            RAISE EXCEPTION 'workspace is unavailable' USING ERRCODE = 'AR004';
          END IF;
          SELECT m.role INTO actor_role FROM arizonix.memberships m
            WHERE m.workspace_id = p_workspace_id AND m.user_id = arizonix.current_user_id();
          IF actor_role IS NULL THEN
            RAISE EXCEPTION 'workspace is unavailable' USING ERRCODE = 'AR004';
          END IF;
          SELECT m.role INTO existing_role FROM arizonix.memberships m
            WHERE m.workspace_id = p_workspace_id AND m.user_id = p_user_id;
          IF existing_role IS NULL THEN
            RAISE EXCEPTION 'membership is unavailable' USING ERRCODE = 'AR006';
          END IF;
          IF actor_role <> 'owner' AND NOT (
            actor_role = 'admin' AND existing_role IN ('analyst', 'viewer')
            AND requested_role IN ('analyst', 'viewer')
          ) THEN RAISE EXCEPTION 'permission denied' USING ERRCODE = 'AR003'; END IF;
          IF existing_role = requested_role THEN RETURN; END IF;
          IF existing_role = 'owner' AND requested_role <> 'owner' THEN
            SELECT count(*) INTO owner_count FROM arizonix.memberships m
              WHERE m.workspace_id = p_workspace_id AND m.role = 'owner';
            IF owner_count <= 1 THEN
              RAISE EXCEPTION 'last owner cannot be demoted' USING ERRCODE = 'AR002';
            END IF;
          END IF;
          UPDATE arizonix.memberships SET role = requested_role
            WHERE workspace_id = p_workspace_id AND user_id = p_user_id;
          PERFORM arizonix.write_audit_event(
            p_workspace_id, 'membership.role_changed', 'membership', p_user_id,
            jsonb_build_object(
              'target_user_id', p_user_id,
              'previous_role', existing_role,
              'new_role', requested_role
            )
          );
        END
        $function$;

        CREATE OR REPLACE FUNCTION arizonix.remove_workspace_member(
          p_workspace_id uuid, p_user_id uuid
        ) RETURNS void
        LANGUAGE plpgsql SECURITY DEFINER
        SET search_path = ''
        AS $function$
        DECLARE
          actor_role arizonix.workspace_role;
          existing_role arizonix.workspace_role;
          owner_count integer;
        BEGIN
          PERFORM 1 FROM arizonix.workspaces w WHERE w.id = p_workspace_id FOR UPDATE;
          IF NOT FOUND THEN
            RAISE EXCEPTION 'workspace is unavailable' USING ERRCODE = 'AR004';
          END IF;
          SELECT m.role INTO actor_role FROM arizonix.memberships m
            WHERE m.workspace_id = p_workspace_id AND m.user_id = arizonix.current_user_id();
          IF actor_role IS NULL THEN
            RAISE EXCEPTION 'workspace is unavailable' USING ERRCODE = 'AR004';
          END IF;
          SELECT m.role INTO existing_role FROM arizonix.memberships m
            WHERE m.workspace_id = p_workspace_id AND m.user_id = p_user_id;
          IF existing_role IS NULL THEN
            RAISE EXCEPTION 'membership is unavailable' USING ERRCODE = 'AR006';
          END IF;
          IF actor_role <> 'owner' AND NOT (
            actor_role = 'admin' AND existing_role IN ('analyst', 'viewer')
          ) THEN RAISE EXCEPTION 'permission denied' USING ERRCODE = 'AR003'; END IF;
          IF existing_role = 'owner' THEN
            SELECT count(*) INTO owner_count FROM arizonix.memberships m
              WHERE m.workspace_id = p_workspace_id AND m.role = 'owner';
            IF owner_count <= 1 THEN
              RAISE EXCEPTION 'last owner cannot be removed' USING ERRCODE = 'AR002';
            END IF;
          END IF;
          DELETE FROM arizonix.memberships
            WHERE workspace_id = p_workspace_id AND user_id = p_user_id;
          PERFORM arizonix.write_audit_event(
            p_workspace_id, 'membership.removed', 'membership', p_user_id,
            jsonb_build_object('target_user_id', p_user_id, 'previous_role', existing_role)
          );
        END
        $function$;

        CREATE OR REPLACE FUNCTION arizonix.leave_workspace(p_workspace_id uuid) RETURNS void
        LANGUAGE plpgsql SECURITY DEFINER
        SET search_path = ''
        AS $function$
        DECLARE
          actor uuid := arizonix.current_user_id();
          existing_role arizonix.workspace_role;
          owner_count integer;
        BEGIN
          PERFORM 1 FROM arizonix.workspaces w WHERE w.id = p_workspace_id FOR UPDATE;
          IF NOT FOUND THEN
            RAISE EXCEPTION 'workspace is unavailable' USING ERRCODE = 'AR004';
          END IF;
          SELECT m.role INTO existing_role FROM arizonix.memberships m
            WHERE m.workspace_id = p_workspace_id AND m.user_id = actor;
          IF existing_role IS NULL THEN
            RAISE EXCEPTION 'workspace is unavailable' USING ERRCODE = 'AR004';
          END IF;
          IF existing_role = 'owner' THEN
            SELECT count(*) INTO owner_count FROM arizonix.memberships m
              WHERE m.workspace_id = p_workspace_id AND m.role = 'owner';
            IF owner_count <= 1 THEN
              RAISE EXCEPTION 'last owner cannot leave' USING ERRCODE = 'AR002';
            END IF;
          END IF;
          DELETE FROM arizonix.memberships
            WHERE workspace_id = p_workspace_id AND user_id = actor;
          PERFORM arizonix.write_audit_event(
            p_workspace_id, 'membership.left', 'membership', actor,
            jsonb_build_object('target_user_id', actor, 'previous_role', existing_role)
          );
        END
        $function$;

        REVOKE ALL ON arizonix.audit_events FROM PUBLIC, arizonix_runtime;
        REVOKE ALL ON FUNCTION arizonix.write_audit_event(
          uuid, arizonix.audit_action, text, uuid, jsonb
        ) FROM PUBLIC, arizonix_runtime;
        REVOKE ALL ON FUNCTION arizonix.can_read_audit(uuid) FROM PUBLIC;
        REVOKE ALL ON FUNCTION arizonix.current_request_id() FROM PUBLIC;
        GRANT SELECT ON arizonix.audit_events TO arizonix_runtime;
        GRANT EXECUTE ON FUNCTION arizonix.can_read_audit(uuid) TO arizonix_runtime;
        GRANT EXECUTE ON FUNCTION arizonix.current_request_id() TO arizonix_runtime;
        """

    async def execute_script(driver_connection) -> None:  # type: ignore[no-untyped-def]
        await driver_connection.execute(sql)

    op.get_bind().connection.run_async(execute_script)


def downgrade() -> None:
    # The initial migration owns the pre-audit function definitions. A downgrade to
    # that revision is intentionally unsupported because preserving mutations while
    # silently removing their required audit write would violate the audit contract.
    raise RuntimeError("Downgrading across the audit boundary is intentionally unsupported")
