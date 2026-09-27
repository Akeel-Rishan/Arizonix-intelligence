import { PageHeader } from "@/components/layout/page-header";
import { EmptyState } from "@/components/ui/empty-state";

export default function EvidencePage() {
  return (
    <div>
      <PageHeader title="Evidence" description="Source-backed observations and their provenance will be organized here." />
      <div className="mt-8"><EmptyState title="No evidence has been collected" description="Evidence storage and source collection will be implemented after the local foundation is verified." /></div>
    </div>
  );
}

