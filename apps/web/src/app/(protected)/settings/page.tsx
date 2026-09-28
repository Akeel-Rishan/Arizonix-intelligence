import { PageHeader } from "@/components/layout/page-header";
import { AccountCard } from "@/components/settings/account-card";
import { WorkspaceSettings } from "@/components/workspaces/workspace-settings";

export default function SettingsPage() {
  return (
    <div>
      <PageHeader
        title="Settings"
        description="Manage your verified identity, active workspace, roles, and members."
      />
      <div className="mt-8 space-y-6">
        <AccountCard />
        <WorkspaceSettings />
      </div>
    </div>
  );
}
