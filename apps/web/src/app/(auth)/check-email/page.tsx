import Link from "next/link";

import { AuthFrame } from "@/components/auth/auth-frame";

export default function CheckEmailPage() {
  return (
    <AuthFrame
      title="Check your email"
      description="Your account needs email confirmation before you can sign in."
    >
      <p className="text-sm leading-6 text-slate-700">
        If the address can be registered, Supabase has sent a confirmation link. Open it in this
        browser to finish setup.
      </p>
      <Link
        className="mt-6 inline-flex min-h-11 w-full items-center justify-center rounded-xl border border-slate-300 px-5 text-sm font-semibold text-slate-800 outline-none hover:bg-slate-50 focus-visible:ring-2 focus-visible:ring-cyan-600"
        href="/login"
      >
        Return to sign in
      </Link>
    </AuthFrame>
  );
}
