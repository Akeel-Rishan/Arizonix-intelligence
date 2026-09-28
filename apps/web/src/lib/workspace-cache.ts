export const ACTIVE_WORKSPACE_KEY = "arizonix.active-workspace.v1";

export function clearWorkspaceCache(): void {
  window.localStorage.removeItem(ACTIVE_WORKSPACE_KEY);
}
