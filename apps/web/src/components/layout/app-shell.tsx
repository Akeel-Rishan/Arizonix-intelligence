"use client";

import { usePathname } from "next/navigation";
import type { ReactNode } from "react";

import { MobileNavigation } from "@/components/layout/mobile-navigation";
import { Sidebar } from "@/components/layout/sidebar";
import { WorkspaceProvider } from "@/components/workspaces/workspace-provider";

export function AppShell({ children, email }: { children: ReactNode; email: string | null }) {
  const pathname = usePathname();
  if (pathname === "/onboarding") {
    return (
      <WorkspaceProvider>
        <main className="min-h-[100dvh] bg-slate-50 px-5 py-8 sm:px-8" id="main-content">
          {children}
        </main>
      </WorkspaceProvider>
    );
  }
  return (
    <WorkspaceProvider>
      <div className="min-h-[100dvh] bg-slate-50 lg:flex">
        <a
          className="fixed left-4 top-3 z-50 -translate-y-24 rounded-lg bg-cyan-300 px-4 py-2 font-semibold text-slate-950 outline-none transition-transform focus:translate-y-0 focus:ring-2 focus:ring-slate-950"
          href="#main-content"
        >
          Skip to content
        </a>
        <Sidebar email={email} />
        <div className="min-w-0 flex-1">
          <MobileNavigation email={email} />
          <main
            id="main-content"
            tabIndex={-1}
            className="mx-auto w-full max-w-6xl px-5 py-8 outline-none sm:px-8 sm:py-10 lg:px-12 lg:py-12"
          >
            {children}
          </main>
        </div>
      </div>
    </WorkspaceProvider>
  );
}
