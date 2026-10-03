import { Suspense } from "react";

import { CompanyList } from "@/components/companies/company-list";
import { PageHeader } from "@/components/layout/page-header";

export default function ProspectsPage() {
  return (
    <div>
      <PageHeader
        title="Prospects"
        description="Workspace companies selected for careful qualification and evidence-backed research."
      />
      <div className="mt-8">
        <Suspense fallback={<p role="status">Loading companies…</p>}>
          <CompanyList />
        </Suspense>
      </div>
    </div>
  );
}
