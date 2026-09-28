import { PageHeader } from "@/components/layout/page-header";
import { AccountCard } from "@/components/settings/account-card";

export default function SettingsPage() {
  return (
    <div>
      <PageHeader
        title="Settings"
        description="Review the identity currently verified by the Arizonix API."
      />
      <div className="mt-8">
        <AccountCard />
      </div>
    </div>
  );
}
