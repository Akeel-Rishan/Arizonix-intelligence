import { CreateWorkspaceForm } from "@/components/workspaces/create-workspace-form";

export default function OnboardingPage() {
  return (
    <div className="mx-auto max-w-2xl py-8 sm:py-16">
      <p className="text-sm font-semibold uppercase tracking-[0.18em] text-cyan-700">
        Workspace setup
      </p>
      <h1 className="mt-3 text-3xl font-semibold tracking-tight text-slate-950 sm:text-4xl">
        Create your first workspace
      </h1>
      <p className="mt-4 max-w-xl leading-7 text-slate-600">
        Workspaces keep research and member access isolated. You will become the first owner.
      </p>
      <CreateWorkspaceForm />
    </div>
  );
}
