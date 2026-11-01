"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { useRef, useState, useSyncExternalStore } from "react";
import { Menu, Moon, Search, Sun, X } from "lucide-react";
import { gsap, MOTION, useGSAP } from "@/lib/gsap";
import { ROUTES } from "@/lib/routes";

// A hand-drawn pen stroke, normalised to a 100x10 box and stretched under the active link.
const UNDERLINE = "M2 6.5 C 20 3.5, 42 8, 60 5 S 88 3.8, 98 5.6";

export function useTheme() {
  // <html data-theme> is the source of truth: the theme script in layout.tsx sets it before
  // hydration, and the command palette may change it too
  const theme = useSyncExternalStore(
    (cb) => {
      const mo = new MutationObserver(cb);
      mo.observe(document.documentElement, { attributes: true, attributeFilter: ["data-theme"] });
      return () => mo.disconnect();
    },
    () => (document.documentElement.dataset.theme === "dark" ? "dark" : "light"),
    () => "light" as const,
  );
  const toggle = () => {
    const next = theme === "dark" ? "light" : "dark";
    document.documentElement.dataset.theme = next;
    try {
      localStorage.setItem("eof.theme", next);
    } catch {
      /* private mode: the toggle still works for this visit */
    }
  };
  return { theme, toggle };
}

export function SiteNav() {
  const path = usePathname();
  const { theme, toggle } = useTheme();
  const [open, setOpen] = useState(false);
  const root = useRef<HTMLElement>(null);

  // redraw the pen stroke under whichever link is now active
  useGSAP(
    () => {
      const mm = gsap.matchMedia();
      mm.add(MOTION, () => {
        if (!root.current?.querySelector(".nav-pen")) return; // home and about have no nav link
        gsap.fromTo(".nav-pen path", { strokeDashoffset: 1 }, { strokeDashoffset: 0, duration: 0.55, ease: "power2.out", delay: 0.1 });
      });
    },
    { scope: root, dependencies: [path], revertOnUpdate: true },
  );

  const isActive = (href: string) => path === href || path.startsWith(href + "/");

  return (
    <header ref={root} className="nav">
      <div className="nav-inner">
        <Link href="/" className="brand" aria-label="Earned or Fabricated, home">
          <svg viewBox="0 0 28 28" className="brand-mark" aria-hidden>
            <rect x="5" y="3" width="18" height="22" rx="2.5" />
            <path d="M9 10h10M9 14h6M9 18h8" />
            <path className="brand-ring" d="M17.5 13.4c3.6-1.4 7 .3 6.6 2.6-.4 2.6-5.6 3.3-8.4 1.6-2-1.2-.6-3.4 1.8-4.2" />
          </svg>
          <span>
            Earned<span className="text-ink-3"> or </span>Fabricated
          </span>
        </Link>

        <nav aria-label="Pages" className="nav-links">
          {ROUTES.map((r) => (
            <Link key={r.href} href={r.href} className={isActive(r.href) ? "is-active" : undefined}
              aria-current={isActive(r.href) ? "page" : undefined}>
              {r.label}
              {isActive(r.href) && (
                <svg className="nav-pen" viewBox="0 0 100 10" preserveAspectRatio="none" aria-hidden>
                  <path d={UNDERLINE} vectorEffect="non-scaling-stroke" pathLength={1} />
                </svg>
              )}
            </Link>
          ))}
        </nav>

        <div className="nav-tools">
          <button type="button" className="icon-btn kbd-btn" onClick={() => window.dispatchEvent(new Event("eof-palette"))}
            aria-label="Search pages and actions (Ctrl K)">
            <Search className="size-4" />
            <kbd>Ctrl K</kbd>
          </button>
          <button type="button" className="icon-btn" onClick={toggle}
            aria-label={theme === "dark" ? "Switch to light theme" : "Switch to dark theme"}>
            {theme === "dark" ? <Sun className="size-4" /> : <Moon className="size-4" />}
          </button>
          <Link href="/audit" className="btn-dark nav-cta h-10 px-4 text-[14px]">
            Audit a resume
          </Link>
          <button type="button" className="icon-btn nav-burger" onClick={() => setOpen((v) => !v)}
            aria-expanded={open} aria-controls="mobile-nav" aria-label={open ? "Close menu" : "Open menu"}>
            {open ? <X className="size-4" /> : <Menu className="size-4" />}
          </button>
        </div>
      </div>

      {open && (
        <nav id="mobile-nav" aria-label="Pages" className="mobile-nav">
          {ROUTES.map((r) => (
            <Link key={r.href} href={r.href} aria-current={isActive(r.href) ? "page" : undefined} onClick={() => setOpen(false)}>
              <span className="font-display text-[22px] font-semibold text-ink">{r.label}</span>
              <span className="text-[13px] text-ink-3">{r.blurb}</span>
            </Link>
          ))}
        </nav>
      )}
    </header>
  );
}
