"""Create workspace persistence, restricted grants, and RLS.

Revision ID: 20260928_0001
Revises:
Create Date: 2026-09-28
"""

from collections.abc import Sequence

from alembic import op

revision: str = "20260928_0001"
down_revision: str | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    sql = """
        DO $roles$
        BEGIN
          IF NOT EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'arizonix_owner') OR
             NOT EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'arizonix_runtime') THEN
            RAISE EXCEPTION 'Run scripts/bootstrap_database.py before migrations';
          END IF;
        END
        $roles$;

        CREATE SCHEMA arizonix AUTHORIZATION arizonix_owner;
        REVOKE ALL ON SCHEMA arizonix FROM PUBLIC;

        CREATE TYPE arizonix.workspace_role AS ENUM ('owner', 'admin', 'analyst', 'viewer');
        ALTER TYPE arizonix.workspace_role OWNER TO arizonix_owner;

        CREATE TABLE arizonix.application_users (
          id uuid PRIMARY KEY,
          email varchar(320),
          created_at timestamptz NOT NULL DEFAULT now(),
          updated_at timestamptz NOT NULL DEFAULT now()
        );

        CREATE TABLE arizonix.workspaces (
          id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
          name varchar(100) NOT NULL,
          created_by uuid NOT NULL REFERENCES arizonix.application_users(id),
          created_at timestamptz NOT NULL DEFAULT now(),
          updated_at timestamptz NOT NULL DEFAULT now(),
          CONSTRAINT ck_workspaces_valid_name
            CHECK (char_length(btrim(name)) BETWEEN 2 AND 100)
        );

        CREATE TABLE arizonix.memberships (
          workspace_id uuid NOT NULL REFERENCES arizonix.workspaces(id) ON DELETE CASCADE,
          user_id uuid NOT NULL REFERENCES arizonix.application_users(id) ON DELETE CASCADE,
          role arizonix.workspace_role NOT NULL,
          created_at timestamptz NOT NULL DEFAULT now(),
          updated_at timestamptz NOT NULL DEFAULT now(),
          CONSTRAINT pk_memberships PRIMARY KEY (workspace_id, user_id)
        );
        CREATE INDEX ix_memberships_user_workspace
          ON arizonix.memberships (user_id, workspace_id);

        ALTER TABLE arizonix.application_users OWNER TO arizonix_owner;
        ALTER TABLE arizonix.workspaces OWNER TO arizonix_owner;
        ALTER TABLE arizonix.memberships OWNER TO arizonix_owner;

        CREATE FUNCTION arizonix.set_updated_at() RETURNS trigger
        LANGUAGE plpgsql
        SET search_path = ''
        AS $function$
        BEGIN
          NEW.updated_at = now();
          RETURN NEW;
        END
        $function$;
        ALTER FUNCTION arizonix.set_updated_at() OWNER TO arizonix_owner;

        CREATE TRIGGER application_users_updated_at
          BEFORE UPDATE ON arizonix.application_users
          FOR EACH ROW EXECUTE FUNCTION arizonix.set_updated_at();
        CREATE TRIGGER workspaces_updated_at
          BEFORE UPDATE ON arizonix.workspaces
          FOR EACH ROW EXECUTE FUNCTION arizonix.set_updated_at();
        CREATE TRIGGER memberships_updated_at
          BEFORE UPDATE ON arizonix.memberships
          FOR EACH ROW EXECUTE FUNCTION arizonix.set_updated_at();

        CREATE FUNCTION arizonix.current_user_id() RETURNS uuid
        LANGUAGE sql STABLE
        SET search_path = ''
        AS $function$
          SELECT nullif(current_setting('arizonix.user_id', true), '')::uuid
        $function$;
        ALTER FUNCTION arizonix.current_user_id() OWNER TO arizonix_owner;

        CREATE FUNCTION arizonix.is_workspace_member(p_workspace_id uuid) RETURNS boolean
        LANGUAGE sql STABLE SECURITY DEFINER
        SET search_path = ''
        AS $function$
          SELECT arizonix.current_user_id() IS NOT NULL AND EXISTS (
            SELECT 1 FROM arizonix.memberships m
            WHERE m.workspace_id = p_workspace_id
              AND m.user_id = arizonix.current_user_id()
          )
        $function$;
        ALTER FUNCTION arizonix.is_workspace_member(uuid) OWNER TO arizonix_owner;

        CREATE FUNCTION arizonix.shares_workspace(p_user_id uuid) RETURNS boolean
        LANGUAGE sql STABLE SECURITY DEFINER
        SET search_path = ''
        AS $function$
          SELECT arizonix.current_user_id() IS NOT NULL AND EXISTS (
            SELECT 1
            FROM arizonix.memberships mine
            JOIN arizonix.memberships theirs
              ON theirs.workspace_id = mine.workspace_id
            WHERE mine.user_id = arizonix.current_user_id()
              AND theirs.user_id = p_user_id
          )
        $function$;
        ALTER FUNCTION arizonix.shares_workspace(uuid) OWNER TO arizonix_owner;

        ALTER TABLE arizonix.application_users ENABLE ROW LEVEL SECURITY;
        ALTER TABLE arizonix.workspaces ENABLE ROW LEVEL SECURITY;
        ALTER TABLE arizonix.memberships ENABLE ROW LEVEL SECURITY;

        CREATE POLICY application_users_select ON arizonix.application_users
          FOR SELECT TO arizonix_runtime
          USING (
            id = arizonix.current_user_id() OR arizonix.shares_workspace(id)
          );
        CREATE POLICY workspaces_select ON arizonix.workspaces
          FOR SELECT TO arizonix_runtime
          USING (arizonix.is_workspace_member(id));
        CREATE POLICY memberships_select ON arizonix.memberships
          FOR SELECT TO arizonix_runtime
          USING (arizonix.is_workspace_member(workspace_id));

        CREATE FUNCTION arizonix.provision_application_user(p_user_id uuid, p_email text)
        RETURNS void
        LANGUAGE plpgsql SECURITY DEFINER
        SET search_path = ''
        AS $function$
        BEGIN
          IF arizonix.current_user_id() IS NULL OR arizonix.current_user_id() <> p_user_id THEN
            RAISE EXCEPTION 'verified identity does not match user' USING ERRCODE = 'AR003';
          END IF;
          INSERT INTO arizonix.application_users (id, email)
          VALUES (p_user_id, left(p_email, 320))
          ON CONFLICT (id) DO UPDATE
            SET email = COALESCE(EXCLUDED.email, arizonix.application_users.email);
        END
        $function$;
        ALTER FUNCTION arizonix.provision_application_user(uuid, text) OWNER TO arizonix_owner;

        CREATE FUNCTION arizonix.create_workspace(p_name text) RETURNS uuid
        LANGUAGE plpgsql SECURITY DEFINER
        SET search_path = ''
        AS $function$
        DECLARE
          actor uuid := arizonix.current_user_id();
          new_workspace_id uuid;
        BEGIN
          IF actor IS NULL THEN
            RAISE EXCEPTION 'identity is required' USING ERRCODE = 'AR003';
          END IF;
          IF NOT EXISTS (SELECT 1 FROM arizonix.application_users u WHERE u.id = actor) THEN
            RAISE EXCEPTION 'application user is unavailable' USING ERRCODE = 'AR005';
          END IF;
          INSERT INTO arizonix.workspaces (name, created_by)
          VALUES (btrim(p_name), actor)
          RETURNING id INTO new_workspace_id;
          INSERT INTO arizonix.memberships (workspace_id, user_id, role)
          VALUES (new_workspace_id, actor, 'owner');
          RETURN new_workspace_id;
        END
        $function$;
        ALTER FUNCTION arizonix.create_workspace(text) OWNER TO arizonix_owner;

        CREATE FUNCTION arizonix.rename_workspace(p_workspace_id uuid, p_name text) RETURNS void
        LANGUAGE plpgsql SECURITY DEFINER
        SET search_path = ''
        AS $function$
        DECLARE actor_role arizonix.workspace_role;
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
          IF actor_role NOT IN ('owner', 'admin') THEN
            RAISE EXCEPTION 'permission denied' USING ERRCODE = 'AR003';
          END IF;
          UPDATE arizonix.workspaces SET name = btrim(p_name) WHERE id = p_workspace_id;
        END
        $function$;
        ALTER FUNCTION arizonix.rename_workspace(uuid, text) OWNER TO arizonix_owner;

        CREATE FUNCTION arizonix.add_workspace_member(
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
          ) THEN
            RAISE EXCEPTION 'permission denied' USING ERRCODE = 'AR003';
          END IF;
          IF NOT EXISTS (SELECT 1 FROM arizonix.application_users u WHERE u.id = p_user_id) THEN
            RAISE EXCEPTION 'application user is unavailable' USING ERRCODE = 'AR005';
          END IF;
          BEGIN
            INSERT INTO arizonix.memberships (workspace_id, user_id, role)
            VALUES (p_workspace_id, p_user_id, requested_role);
          EXCEPTION WHEN unique_violation THEN
            RAISE EXCEPTION 'duplicate membership' USING ERRCODE = 'AR001';
          END;
        END
        $function$;
        ALTER FUNCTION arizonix.add_workspace_member(uuid, uuid, text) OWNER TO arizonix_owner;

        CREATE FUNCTION arizonix.change_workspace_member_role(
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
            actor_role = 'admin'
            AND existing_role IN ('analyst', 'viewer')
            AND requested_role IN ('analyst', 'viewer')
          ) THEN
            RAISE EXCEPTION 'permission denied' USING ERRCODE = 'AR003';
          END IF;
          IF existing_role = 'owner' AND requested_role <> 'owner' THEN
            SELECT count(*) INTO owner_count FROM arizonix.memberships m
              WHERE m.workspace_id = p_workspace_id AND m.role = 'owner';
            IF owner_count <= 1 THEN
              RAISE EXCEPTION 'last owner cannot be demoted' USING ERRCODE = 'AR002';
            END IF;
          END IF;
          UPDATE arizonix.memberships SET role = requested_role
            WHERE workspace_id = p_workspace_id AND user_id = p_user_id;
        END
        $function$;
        ALTER FUNCTION arizonix.change_workspace_member_role(uuid, uuid, text)
          OWNER TO arizonix_owner;

        CREATE FUNCTION arizonix.remove_workspace_member(
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
          ) THEN
            RAISE EXCEPTION 'permission denied' USING ERRCODE = 'AR003';
          END IF;
          IF existing_role = 'owner' THEN
            SELECT count(*) INTO owner_count FROM arizonix.memberships m
              WHERE m.workspace_id = p_workspace_id AND m.role = 'owner';
            IF owner_count <= 1 THEN
              RAISE EXCEPTION 'last owner cannot be removed' USING ERRCODE = 'AR002';
            END IF;
          END IF;
          DELETE FROM arizonix.memberships
            WHERE workspace_id = p_workspace_id AND user_id = p_user_id;
        END
        $function$;
        ALTER FUNCTION arizonix.remove_workspace_member(uuid, uuid) OWNER TO arizonix_owner;

        CREATE FUNCTION arizonix.leave_workspace(p_workspace_id uuid) RETURNS void
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
        END
        $function$;
        ALTER FUNCTION arizonix.leave_workspace(uuid) OWNER TO arizonix_owner;

        REVOKE ALL ON ALL TABLES IN SCHEMA arizonix FROM PUBLIC;
        REVOKE ALL ON ALL FUNCTIONS IN SCHEMA arizonix FROM PUBLIC;
        REVOKE ALL ON SCHEMA arizonix FROM PUBLIC;
        DO $revoke_supabase$
        BEGIN
          IF EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'anon') THEN
            REVOKE ALL ON SCHEMA arizonix FROM anon;
            REVOKE ALL ON ALL TABLES IN SCHEMA arizonix FROM anon;
            REVOKE ALL ON ALL FUNCTIONS IN SCHEMA arizonix FROM anon;
          END IF;
          IF EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'authenticated') THEN
            REVOKE ALL ON SCHEMA arizonix FROM authenticated;
            REVOKE ALL ON ALL TABLES IN SCHEMA arizonix FROM authenticated;
            REVOKE ALL ON ALL FUNCTIONS IN SCHEMA arizonix FROM authenticated;
          END IF;
        END
        $revoke_supabase$;

        GRANT USAGE ON SCHEMA arizonix TO arizonix_runtime;
        GRANT SELECT ON arizonix.application_users, arizonix.workspaces, arizonix.memberships
          TO arizonix_runtime;
        GRANT EXECUTE ON FUNCTION arizonix.current_user_id() TO arizonix_runtime;
        GRANT EXECUTE ON FUNCTION arizonix.is_workspace_member(uuid) TO arizonix_runtime;
        GRANT EXECUTE ON FUNCTION arizonix.shares_workspace(uuid) TO arizonix_runtime;
        GRANT EXECUTE ON FUNCTION arizonix.provision_application_user(uuid, text)
          TO arizonix_runtime;
        GRANT EXECUTE ON FUNCTION arizonix.create_workspace(text) TO arizonix_runtime;
        GRANT EXECUTE ON FUNCTION arizonix.rename_workspace(uuid, text) TO arizonix_runtime;
        GRANT EXECUTE ON FUNCTION arizonix.add_workspace_member(uuid, uuid, text)
          TO arizonix_runtime;
        GRANT EXECUTE ON FUNCTION arizonix.change_workspace_member_role(uuid, uuid, text)
          TO arizonix_runtime;
        GRANT EXECUTE ON FUNCTION arizonix.remove_workspace_member(uuid, uuid)
          TO arizonix_runtime;
        GRANT EXECUTE ON FUNCTION arizonix.leave_workspace(uuid) TO arizonix_runtime;
        """

    async def execute_script(driver_connection) -> None:  # type: ignore[no-untyped-def]
        await driver_connection.execute(sql)

    op.get_bind().connection.run_async(execute_script)


def downgrade() -> None:
    op.execute("DROP SCHEMA IF EXISTS arizonix CASCADE")
