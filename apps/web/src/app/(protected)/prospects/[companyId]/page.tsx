import Link from "next/link";

import { CompanyDetail } from "@/components/companies/company-detail";

export default async function CompanyPage({ params }: { params: Promise<{ companyId: string }> }) {
  const { companyId } = await params;
  return (
    <div>
      <Link className="mb-5 inline-flex text-sm font-semibold text-cyan-800" href="/prospects">
        ← Back to companies
      </Link>
      <CompanyDetail companyId={companyId} />
    </div>
  );
}
