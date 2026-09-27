import { PageHeader } from "@/components/layout/page-header";
import { EmptyState } from "@/components/ui/empty-state";

export default function SettingsPage() {
  return (
    <div>
      <PageHeader
        title="Settings"
        description="Workspace and provider configuration will be managed here when those systems exist."
      />
      <div className="mt-8">
        <EmptyState
          title="Settings are not available"
          description="This local foundation needs no credentials, paid services, or external provider configuration."
        />
      </div>
    </div>
  );
}
