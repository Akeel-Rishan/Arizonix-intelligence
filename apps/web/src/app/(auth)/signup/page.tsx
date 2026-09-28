import { signupAction } from "@/app/(auth)/actions";
import { AuthForm } from "@/components/auth/auth-form";
import { AuthFrame } from "@/components/auth/auth-frame";
import { AuthSetupUnavailable } from "@/components/auth/auth-setup-unavailable";
import { safeRedirectPath } from "@/lib/auth/redirect";
import { getPublicAuthConfig, PublicConfigurationError } from "@/lib/config";

export default async function SignupPage({
  searchParams,
}: {
  searchParams: Promise<{ next?: string }>;
}) {
  try {
    getPublicAuthConfig();
  } catch (error: unknown) {
    if (error instanceof PublicConfigurationError) return <AuthSetupUnavailable />;
    throw error;
  }
  const params = await searchParams;
  return (
    <AuthFrame
      title="Create your account"
      description="Use your email and a password of at least 8 characters."
    >
      <AuthForm action={signupAction} mode="signup" next={safeRedirectPath(params.next)} />
    </AuthFrame>
  );
}
