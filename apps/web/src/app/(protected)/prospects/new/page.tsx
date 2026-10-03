import Link from "next/link";

import { CompanyForm } from "@/components/companies/company-form";
import { PageHeader } from "@/components/layout/page-header";

export default function NewCompanyPage() {
  return (
    <div>
      <Link className="mb-5 inline-flex text-sm font-semibold text-cyan-800" href="/prospects">
        ← Back to companies
      </Link>
      <PageHeader
        title="Add company"
        description="Create a manually entered, unverified company record in the active workspace."
      />
      <div className="mt-8">
        <CompanyForm />
      </div>
    </div>
  );
}
