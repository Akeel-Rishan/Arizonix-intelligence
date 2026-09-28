import { signOutAction } from "@/app/(protected)/actions";

export function UserMenu({ email, compact = false }: { email: string | null; compact?: boolean }) {
  return (
    <div className={compact ? "border-t border-slate-800 pt-5" : "mt-auto px-3 pt-8"}>
      <p className="truncate text-xs text-slate-400" title={email ?? "Signed-in user"}>
        {email ?? "Signed-in user"}
      </p>
      <form action={signOutAction}>
        <button
          className="mt-2 min-h-10 w-full rounded-lg border border-slate-700 px-3 text-left text-sm font-semibold text-slate-200 outline-none hover:bg-slate-800 focus-visible:ring-2 focus-visible:ring-cyan-300"
          type="submit"
        >
          Sign out
        </button>
      </form>
    </div>
  );
}
