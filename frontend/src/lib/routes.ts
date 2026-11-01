// Every page of the site, used by the nav, the footer and the command palette.
export const ROUTES = [
  { href: "/audit", label: "Audit", blurb: "Check a rewrite against your original resume" },
  { href: "/spot", label: "Spot it", blurb: "Game: find the invented lines before the checker does" },
  { href: "/findings", label: "Findings", blurb: "What 380 rewritten resumes showed" },
  { href: "/method", label: "Method", blurb: "How the checker works, and how accurate it is" },
  { href: "/history", label: "History", blurb: "Audits you ran in this browser" },
] as const;

export const EXTRA_ROUTES = [
  { href: "/", label: "Home", blurb: "Start page" },
  { href: "/about", label: "About", blurb: "The team and the project" },
] as const;
