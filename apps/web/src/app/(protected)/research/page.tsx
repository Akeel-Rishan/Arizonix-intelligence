import { PageHeader } from "@/components/layout/page-header";
import { EmptyState } from "@/components/ui/empty-state";

export default function ResearchPage() {
  return (
    <div>
      <PageHeader
        title="Research"
        description="Collection and analysis runs will be coordinated here in a later step."
      />
      <div className="mt-8">
        <EmptyState
          title="Research runs are not available"
          description="No collection agents or external research providers are configured in this foundation."
        />
      </div>
    </div>
  );
}
