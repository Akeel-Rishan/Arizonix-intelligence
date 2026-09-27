import { PageHeader } from "@/components/layout/page-header";
import { EmptyState } from "@/components/ui/empty-state";

export default function ReviewPage() {
  return (
    <div>
      <PageHeader title="Human Review" description="Independent findings will require an explicit human decision before outreach." />
      <div className="mt-8"><EmptyState title="Nothing is awaiting review" description="Review queues and approval controls are planned for a later step. No action is available yet." /></div>
    </div>
  );
}

