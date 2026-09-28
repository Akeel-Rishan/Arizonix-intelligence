import Link from "next/link";
import type { ReactNode } from "react";

export function AuthFrame({
  title,
  description,
  children,
}: {
  title: string;
  description: string;
  children: ReactNode;
}) {
  return (
    <main className="grid min-h-[100dvh] place-items-center bg-slate-950 px-5 py-10">
      <div className="w-full max-w-md">
        <Link
          href="/login"
          className="inline-flex rounded-lg text-sm font-semibold tracking-tight text-cyan-300 outline-none focus-visible:ring-2 focus-visible:ring-cyan-300 focus-visible:ring-offset-4 focus-visible:ring-offset-slate-950"
        >
          Arizonix Intelligence
        </Link>
        <section className="mt-6 rounded-2xl border border-slate-700 bg-white p-6 shadow-2xl shadow-black/20 sm:p-8">
          <h1 className="text-2xl font-semibold tracking-[-0.03em] text-slate-950">{title}</h1>
          <p className="mt-2 text-sm leading-6 text-slate-600">{description}</p>
          <div className="mt-7">{children}</div>
        </section>
        <p className="mt-5 text-center text-xs leading-5 text-slate-400">
          Evidence-driven business research.
        </p>
      </div>
    </main>
  );
}
