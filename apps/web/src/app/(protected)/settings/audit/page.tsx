import Link from "next/link";

import { AuditEventList } from "@/components/audit/audit-event-list";
import { PageHeader } from "@/components/layout/page-header";

export default function AuditHistoryPage() {
  return (
    <div>
      <Link
        className="mb-5 inline-flex rounded text-sm font-semibold text-cyan-800 outline-none focus-visible:ring-2 focus-visible:ring-cyan-500"
        href="/settings"
      >
        ← Back to settings
      </Link>
      <PageHeader
        title="Audit history"
        description="Committed workspace and membership changes, newest first."
      />
      <div className="mt-8">
        <AuditEventList />
      </div>
    </div>
  );
}
