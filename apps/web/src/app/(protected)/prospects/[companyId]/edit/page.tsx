import Link from "next/link";

import { CompanyForm } from "@/components/companies/company-form";
import { PageHeader } from "@/components/layout/page-header";

export default async function EditCompanyPage({
  params,
}: {
  params: Promise<{ companyId: string }>;
}) {
  const { companyId } = await params;
  return (
    <div>
      <Link
        className="mb-5 inline-flex text-sm font-semibold text-cyan-800"
        href={`/prospects/${companyId}`}
      >
        ← Back to company
      </Link>
      <PageHeader
        title="Edit company"
        description="Update the active workspace record using its current saved version."
      />
      <div className="mt-8">
        <CompanyForm companyId={companyId} />
      </div>
    </div>
  );
}
