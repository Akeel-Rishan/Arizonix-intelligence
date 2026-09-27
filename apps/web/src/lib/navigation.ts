export type NavigationItem = {
  label: string;
  href: string;
  shortLabel: string;
};

export const navigationItems: readonly NavigationItem[] = [
  { label: "Overview", href: "/", shortLabel: "OV" },
  { label: "Prospects", href: "/prospects", shortLabel: "PR" },
  { label: "Research", href: "/research", shortLabel: "RS" },
  { label: "Evidence", href: "/evidence", shortLabel: "EV" },
  { label: "Human Review", href: "/review", shortLabel: "HR" },
  { label: "Settings", href: "/settings", shortLabel: "ST" },
] as const;

