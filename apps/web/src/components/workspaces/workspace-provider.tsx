"use client";

import { usePathname, useRouter } from "next/navigation";
import {
  createContext,
  type ReactNode,
  useCallback,
  useContext,
  useEffect,
  useMemo,
  useRef,
  useState,
} from "react";

import { fetchWorkspaces, WorkspaceApiError } from "@/lib/api-client";
import type { Workspace } from "@/lib/types";
import { ACTIVE_WORKSPACE_KEY } from "@/lib/workspace-cache";

type WorkspaceContextValue = {
  workspaces: Workspace[];
  activeWorkspace: Workspace | null;
  loading: boolean;
  error: string | null;
  selectWorkspace: (id: string) => void;
  refreshWorkspaces: (preferredId?: string) => Promise<void>;
};

const WorkspaceContext = createContext<WorkspaceContextValue | null>(null);

export function WorkspaceProvider({ children }: { children: ReactNode }) {
  const [workspaces, setWorkspaces] = useState<Workspace[]>([]);
  const [activeId, setActiveId] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const requestVersion = useRef(0);
  const pathname = usePathname();
  const router = useRouter();

  const refreshWorkspaces = useCallback(async (preferredId?: string) => {
    const version = ++requestVersion.current;
    setLoading(true);
    try {
      const page = await fetchWorkspaces();
      if (version !== requestVersion.current) return;
      const stored = preferredId ?? window.localStorage.getItem(ACTIVE_WORKSPACE_KEY);
      const next = page.items.find((workspace) => workspace.id === stored) ?? page.items[0] ?? null;
      setWorkspaces(page.items);
      setActiveId(next?.id ?? null);
      setError(null);
      if (next) window.localStorage.setItem(ACTIVE_WORKSPACE_KEY, next.id);
      else window.localStorage.removeItem(ACTIVE_WORKSPACE_KEY);
    } catch (caught: unknown) {
      if (version !== requestVersion.current) return;
      setError(
        caught instanceof WorkspaceApiError
          ? caught.userMessage
          : "Workspaces are temporarily unavailable.",
      );
    } finally {
      if (version === requestVersion.current) setLoading(false);
    }
  }, []);

  useEffect(() => {
    const timer = window.setTimeout(() => void refreshWorkspaces(), 0);
    return () => {
      window.clearTimeout(timer);
      requestVersion.current += 1;
    };
  }, [refreshWorkspaces]);

  useEffect(() => {
    if (!loading && !error && workspaces.length === 0 && pathname !== "/onboarding") {
      router.replace("/onboarding");
    } else if (!loading && !error && workspaces.length > 0 && pathname === "/onboarding") {
      router.replace("/");
    }
  }, [error, loading, pathname, router, workspaces.length]);

  const selectWorkspace = useCallback((id: string) => {
    setActiveId((current) => {
      if (current === id) return current;
      requestVersion.current += 1;
      window.localStorage.setItem(ACTIVE_WORKSPACE_KEY, id);
      return id;
    });
  }, []);

  const value = useMemo<WorkspaceContextValue>(
    () => ({
      workspaces,
      activeWorkspace: workspaces.find((workspace) => workspace.id === activeId) ?? null,
      loading,
      error,
      selectWorkspace,
      refreshWorkspaces,
    }),
    [activeId, error, loading, refreshWorkspaces, selectWorkspace, workspaces],
  );
  return <WorkspaceContext.Provider value={value}>{children}</WorkspaceContext.Provider>;
}

export function useWorkspace(): WorkspaceContextValue {
  const context = useContext(WorkspaceContext);
  if (!context) throw new Error("useWorkspace must be used inside WorkspaceProvider");
  return context;
}
