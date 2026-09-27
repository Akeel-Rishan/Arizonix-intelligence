"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { useEffect, useRef, useState } from "react";

import { navigationItems } from "@/lib/navigation";

export function MobileNavigation() {
  const [open, setOpen] = useState(false);
  const pathname = usePathname();
  const triggerRef = useRef<HTMLButtonElement>(null);
  const closeRef = useRef<HTMLButtonElement>(null);
  const panelRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (!open) return;
    const previousOverflow = document.body.style.overflow;
    document.body.style.overflow = "hidden";
    closeRef.current?.focus();

    const handleKeyDown = (event: KeyboardEvent) => {
      if (event.key === "Escape") {
        setOpen(false);
        triggerRef.current?.focus();
        return;
      }
      if (event.key === "Tab" && panelRef.current) {
        const focusable = Array.from(
          panelRef.current.querySelectorAll<HTMLElement>("button, a[href]")
        );
        const first = focusable[0];
        const last = focusable.at(-1);
        if (event.shiftKey && document.activeElement === first) {
          event.preventDefault();
          last?.focus();
        } else if (!event.shiftKey && document.activeElement === last) {
          event.preventDefault();
          first?.focus();
        }
      }
    };
    document.addEventListener("keydown", handleKeyDown);
    return () => {
      document.body.style.overflow = previousOverflow;
      document.removeEventListener("keydown", handleKeyDown);
    };
  }, [open]);

  const closeNavigation = (restoreFocus = false) => {
    setOpen(false);
    if (restoreFocus) window.requestAnimationFrame(() => triggerRef.current?.focus());
  };

  return (
    <>
      <header className="flex min-h-16 items-center justify-between border-b border-slate-200 bg-slate-950 px-5 text-white lg:hidden">
        <div>
          <p className="font-semibold tracking-[-0.02em]">Arizonix Intelligence</p>
          <p className="text-xs text-slate-400">Evidence-driven research</p>
        </div>
        <button
          ref={triggerRef}
          aria-controls="mobile-navigation"
          aria-expanded={open}
          className="min-h-11 rounded-xl border border-slate-700 px-4 text-sm font-semibold outline-none hover:bg-slate-800 focus-visible:ring-2 focus-visible:ring-cyan-300"
          onClick={() => setOpen(true)}
          type="button"
        >
          Menu
        </button>
      </header>

      {open ? (
        <div className="fixed inset-0 z-40 lg:hidden" role="dialog" aria-modal="true" aria-label="Primary navigation">
          <button
            aria-label="Close navigation"
            className="absolute inset-0 bg-slate-950/60"
            onClick={() => closeNavigation(true)}
            type="button"
          />
          <div ref={panelRef} id="mobile-navigation" className="absolute right-0 top-0 flex min-h-[100dvh] w-[min(88vw,22rem)] flex-col bg-slate-950 p-5 text-white shadow-2xl shadow-slate-950/30">
            <div className="flex items-center justify-between border-b border-slate-800 pb-5">
              <p className="font-semibold">Navigation</p>
              <button
                ref={closeRef}
                className="min-h-11 rounded-xl border border-slate-700 px-4 text-sm font-semibold outline-none hover:bg-slate-800 focus-visible:ring-2 focus-visible:ring-cyan-300"
                onClick={() => closeNavigation(true)}
                type="button"
              >
                Close
              </button>
            </div>
            <nav aria-label="Primary" className="mt-6">
              <ul className="space-y-2">
                {navigationItems.map((item) => {
                  const active = item.href === "/" ? pathname === "/" : pathname.startsWith(item.href);
                  return (
                    <li key={item.href}>
                      <Link
                        aria-current={active ? "page" : undefined}
                        className={`flex min-h-12 items-center rounded-xl px-4 text-base font-medium outline-none focus-visible:ring-2 focus-visible:ring-cyan-300 ${active ? "bg-cyan-300 text-slate-950" : "text-slate-200 hover:bg-slate-800"}`}
                        href={item.href}
                        onClick={() => closeNavigation()}
                      >
                        {item.label}
                      </Link>
                    </li>
                  );
                })}
              </ul>
            </nav>
          </div>
        </div>
      ) : null}
    </>
  );
}
