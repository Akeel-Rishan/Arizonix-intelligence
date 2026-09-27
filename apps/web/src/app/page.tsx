import Link from "next/link";

import { ApiHealthCard } from "@/components/dashboard/api-health-card";
import { PageHeader } from "@/components/layout/page-header";
import { EmptyState } from "@/components/ui/empty-state";

export default function OverviewPage() {
  return (
    <div>
      <PageHeader
        title="Research overview"
        description="Investigate one business carefully, keep conclusions tied to evidence, and preserve uncertainty for human review."
      />

      <div className="mt-8 grid gap-6 xl:grid-cols-[minmax(0,1.15fr)_minmax(19rem,0.85fr)]">
        <EmptyState
          title="No prospects have been added"
          description="This foundation does not create or imply business records. Prospect intake will be implemented in a later step."
          action={
            <Link
              className="inline-flex min-h-11 items-center rounded-xl bg-cyan-700 px-5 text-sm font-semibold text-white outline-none hover:bg-cyan-800 focus-visible:ring-2 focus-visible:ring-cyan-600 focus-visible:ring-offset-2"
              href="/prospects"
            >
              View prospects
            </Link>
          }
        />
        <ApiHealthCard />
      </div>

      <aside className="mt-6 rounded-2xl border border-slate-200 bg-slate-100 px-5 py-4 text-sm leading-6 text-slate-700">
        <strong className="font-semibold text-slate-950">Local development foundation</strong>
        <span aria-hidden="true"> — </span>
        authentication is not configured.
      </aside>
    </div>
  );
}
