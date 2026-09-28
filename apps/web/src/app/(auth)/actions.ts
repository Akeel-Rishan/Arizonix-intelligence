"use server";

import { redirect } from "next/navigation";

import { safeRedirectPath } from "@/lib/auth/redirect";
import { getPublicAuthConfig, PublicConfigurationError } from "@/lib/config";
import { createSupabaseServerClient } from "@/lib/supabase/server";

export type AuthActionState = {
  message?: string;
  fieldErrors?: { email?: string; password?: string; confirmation?: string };
  values?: { email?: string };
};

const EMAIL_PATTERN = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;

function readCredentials(
  formData: FormData,
  includeConfirmation: boolean,
): {
  email: string;
  password: string;
  confirmation: string;
  fieldErrors: NonNullable<AuthActionState["fieldErrors"]>;
} {
  const email = String(formData.get("email") ?? "")
    .trim()
    .toLowerCase();
  const password = String(formData.get("password") ?? "");
  const confirmation = String(formData.get("confirmation") ?? "");
  const fieldErrors: NonNullable<AuthActionState["fieldErrors"]> = {};
  if (!EMAIL_PATTERN.test(email)) fieldErrors.email = "Enter a valid email address.";
  if (password.length < 8) fieldErrors.password = "Password must be at least 8 characters.";
  if (includeConfirmation && password !== confirmation) {
    fieldErrors.confirmation = "Passwords do not match.";
  }
  return { email, password, confirmation, fieldErrors };
}

function configurationMessage(error: unknown): AuthActionState | null {
  if (error instanceof PublicConfigurationError) {
    return { message: "Authentication is not configured. Ask an administrator to check setup." };
  }
  return null;
}

export async function loginAction(
  previousState: AuthActionState,
  formData: FormData,
): Promise<AuthActionState> {
  void previousState;
  const { email, password, fieldErrors } = readCredentials(formData, false);
  if (Object.keys(fieldErrors).length) return { fieldErrors, values: { email } };

  try {
    const supabase = await createSupabaseServerClient();
    const { error } = await supabase.auth.signInWithPassword({ email, password });
    if (error) {
      return { message: "Email or password is incorrect.", values: { email } };
    }
  } catch (error: unknown) {
    return (
      configurationMessage(error) ?? {
        message: "Sign in is temporarily unavailable. Please try again.",
        values: { email },
      }
    );
  }
  redirect(safeRedirectPath(String(formData.get("next") ?? "/")));
}

export async function signupAction(
  previousState: AuthActionState,
  formData: FormData,
): Promise<AuthActionState> {
  void previousState;
  const { email, password, fieldErrors } = readCredentials(formData, true);
  if (Object.keys(fieldErrors).length) return { fieldErrors, values: { email } };
  const destination = safeRedirectPath(String(formData.get("next") ?? "/"));

  try {
    const config = getPublicAuthConfig();
    const confirmUrl = new URL("/auth/confirm", config.siteUrl);
    confirmUrl.searchParams.set("next", destination);
    const supabase = await createSupabaseServerClient();
    const { data, error } = await supabase.auth.signUp({
      email,
      password,
      options: { emailRedirectTo: confirmUrl.toString() },
    });
    if (error) {
      return {
        message: "We could not create the account. Check your details and try again.",
        values: { email },
      };
    }
    if (data.session) redirect(destination);
  } catch (error: unknown) {
    const setupError = configurationMessage(error);
    if (setupError) return setupError;
    throw error;
  }
  redirect(`/check-email?email=${encodeURIComponent(email)}`);
}
