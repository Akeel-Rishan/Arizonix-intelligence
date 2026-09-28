import { PageHeader } from "@/components/layout/page-header";
import { EmptyState } from "@/components/ui/empty-state";

export default function ProspectsPage() {
  return (
    <div>
      <PageHeader
        title="Prospects"
        description="Businesses selected for careful qualification will appear here."
      />
      <div className="mt-8">
        <EmptyState
          title="Prospect intake is not implemented"
          description="A later step will add validated company intake. No sample businesses are shown."
        />
      </div>
    </div>
  );
}
