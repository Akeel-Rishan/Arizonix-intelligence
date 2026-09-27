"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";

import { navigationItems } from "@/lib/navigation";

function isActiveRoute(pathname: string, href: string): boolean {
  return href === "/" ? pathname === href : pathname.startsWith(href);
}

export function Sidebar() {
  const pathname = usePathname();

  return (
    <aside className="hidden min-h-[100dvh] w-72 shrink-0 border-r border-slate-200 bg-slate-950 px-5 py-7 text-slate-100 lg:flex lg:flex-col">
      <div className="px-3">
        <p className="text-lg font-semibold tracking-[-0.025em]">Arizonix Intelligence</p>
        <p className="mt-1.5 text-sm leading-5 text-slate-400">Evidence-driven business research.</p>
      </div>
      <nav aria-label="Primary" className="mt-10">
        <ul className="space-y-1.5">
          {navigationItems.map((item) => {
            const active = isActiveRoute(pathname, item.href);
            return (
              <li key={item.href}>
                <Link
                  aria-current={active ? "page" : undefined}
                  className={`flex min-h-11 items-center gap-3 rounded-xl px-3 py-2.5 text-sm font-medium outline-none transition-colors focus-visible:ring-2 focus-visible:ring-cyan-300 focus-visible:ring-offset-2 focus-visible:ring-offset-slate-950 ${
                    active
                      ? "bg-cyan-300 text-slate-950"
                      : "text-slate-300 hover:bg-slate-800 hover:text-white"
                  }`}
                  href={item.href}
                >
                  <span aria-hidden="true" className="w-6 font-mono text-[10px] font-bold tracking-wider">
                    {item.shortLabel}
                  </span>
                  {item.label}
                </Link>
              </li>
            );
          })}
        </ul>
      </nav>
      <p className="mt-auto px-3 pt-8 text-xs leading-5 text-slate-500">Local foundation</p>
    </aside>
  );
}

