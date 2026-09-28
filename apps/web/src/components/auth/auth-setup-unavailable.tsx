import { AuthFrame } from "@/components/auth/auth-frame";

export function AuthSetupUnavailable() {
  return (
    <AuthFrame
      title="Authentication setup required"
      description="This deployment cannot authenticate users yet."
    >
      <div role="alert" className="rounded-xl border border-amber-300 bg-amber-50 p-4">
        <p className="font-semibold text-amber-950">
          Supabase configuration is missing or invalid.
        </p>
        <p className="mt-1 text-sm leading-6 text-amber-900">
          Set the public Supabase URL and publishable key, then restart the web application.
        </p>
      </div>
    </AuthFrame>
  );
}
