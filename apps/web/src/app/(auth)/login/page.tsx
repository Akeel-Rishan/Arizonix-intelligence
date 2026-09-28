import { AuthForm } from "@/components/auth/auth-form";
import { AuthFrame } from "@/components/auth/auth-frame";
import { AuthSetupUnavailable } from "@/components/auth/auth-setup-unavailable";
import { loginAction } from "@/app/(auth)/actions";
import { safeRedirectPath } from "@/lib/auth/redirect";
import { getPublicAuthConfig, PublicConfigurationError } from "@/lib/config";

export default async function LoginPage({
  searchParams,
}: {
  searchParams: Promise<{ next?: string; confirmation?: string }>;
}) {
  try {
    getPublicAuthConfig();
  } catch (error: unknown) {
    if (error instanceof PublicConfigurationError) return <AuthSetupUnavailable />;
    throw error;
  }
  const params = await searchParams;
  const next = safeRedirectPath(params.next);
  return (
    <AuthFrame title="Welcome back" description="Sign in to continue your research workspace.">
      {params.confirmation === "expired" ? (
        <div
          role="alert"
          className="mb-5 rounded-xl border border-amber-200 bg-amber-50 p-3 text-sm text-amber-950"
        >
          That confirmation link is invalid or expired. Request a new sign-up email and try again.
        </div>
      ) : null}
      <AuthForm action={loginAction} mode="login" next={next} />
    </AuthFrame>
  );
}
