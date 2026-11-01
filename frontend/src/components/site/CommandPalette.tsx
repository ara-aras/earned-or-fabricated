"use client";

import { useRouter } from "next/navigation";
import { useEffect, useMemo, useRef, useState } from "react";
import { CornerDownLeft, FileText, Moon, Navigation } from "lucide-react";
import { fetchDemoCases, type DemoCase } from "@/lib/api";
import { gsap, useGSAP } from "@/lib/gsap";
import { EXTRA_ROUTES, ROUTES } from "@/lib/routes";

type Item = { id: string; group: string; label: string; hint: string; run: () => void };

// Ctrl/Cmd+K: jump to any page, load a demo case into the audit, or flip the theme.
export function CommandPalette() {
  const router = useRouter();
  const [open, setOpen] = useState(false);
  const [q, setQ] = useState("");
  const [sel, setSel] = useState(0);
  const [cases, setCases] = useState<DemoCase[]>([]);
  const panel = useRef<HTMLDivElement>(null);
  const input = useRef<HTMLInputElement>(null);

  useEffect(() => {
    const show = () => {
      setQ("");
      setSel(0);
      setOpen(true);
    };
    const onKey = (e: KeyboardEvent) => {
      if ((e.ctrlKey || e.metaKey) && e.key.toLowerCase() === "k") {
        e.preventDefault();
        setQ("");
        setSel(0);
        setOpen((v) => !v);
      }
    };
    const onOpen = show;
    window.addEventListener("keydown", onKey);
    window.addEventListener("eof-palette", onOpen);
    return () => {
      window.removeEventListener("keydown", onKey);
      window.removeEventListener("eof-palette", onOpen);
    };
  }, []);

  useEffect(() => {
    if (!open) return;
    requestAnimationFrame(() => input.current?.focus());
    if (!cases.length) fetchDemoCases().then((r) => setCases(r.cases)).catch(() => {});
  }, [open, cases.length]);

  useGSAP(
    () => {
      if (open) gsap.from(panel.current, { y: -12, opacity: 0, scale: 0.98, duration: 0.22, ease: "power2.out" });
    },
    { dependencies: [open] },
  );

  const items: Item[] = useMemo(() => {
    const go = (href: string) => () => {
      setOpen(false);
      router.push(href);
    };
    return [
      ...[...EXTRA_ROUTES.slice(0, 1), ...ROUTES, ...EXTRA_ROUTES.slice(1)].map((r) => ({
        id: r.href, group: "Pages", label: r.label, hint: r.blurb, run: go(r.href),
      })),
      ...cases.map((c, i) => ({
        id: c.id, group: "Demo cases", label: `Audit demo ${i + 1}: ${c.job.title}`,
        hint: c.shows.split(".")[0], run: go(`/audit?case=${c.id}`),
      })),
      {
        id: "theme", group: "Actions", label: "Toggle light / dark theme", hint: "Also on the moon button in the bar",
        run: () => {
          const el = document.documentElement;
          const next = el.dataset.theme === "dark" ? "light" : "dark";
          el.dataset.theme = next;
          try {
            localStorage.setItem("eof.theme", next);
          } catch {
            /* ignore */
          }
          setOpen(false);
        },
      },
    ];
  }, [cases, router]);

  const shown = items.filter((i) => `${i.label} ${i.hint}`.toLowerCase().includes(q.trim().toLowerCase()));

  if (!open) return null;

  const onKey = (e: React.KeyboardEvent) => {
    if (e.key === "Escape") setOpen(false);
    if (e.key === "ArrowDown") {
      e.preventDefault();
      setSel((s) => Math.min(shown.length - 1, s + 1));
    }
    if (e.key === "ArrowUp") {
      e.preventDefault();
      setSel((s) => Math.max(0, s - 1));
    }
    if (e.key === "Enter") shown[sel]?.run();
  };

  let lastGroup = "";
  return (
    <div className="palette-veil" onMouseDown={() => setOpen(false)}>
      <div ref={panel} className="palette" role="dialog" aria-modal="true" aria-label="Search pages and actions"
        onMouseDown={(e) => e.stopPropagation()} onKeyDown={onKey}>
        <input ref={input} value={q} onChange={(e) => { setQ(e.target.value); setSel(0); }}
          placeholder="Go to a page, load a demo case…" aria-label="Search" className="palette-input"
          role="combobox" aria-expanded="true" aria-controls="palette-list" aria-activedescendant={shown[sel]?.id} />
        <ul id="palette-list" role="listbox" className="palette-list">
          {shown.length === 0 && <li className="px-4 py-6 text-[14px] text-ink-3">No page or action matches “{q}”.</li>}
          {shown.map((it, i) => {
            const head = it.group !== lastGroup ? it.group : null;
            lastGroup = it.group;
            const Icon = it.group === "Pages" ? Navigation : it.group === "Demo cases" ? FileText : Moon;
            return (
              <li key={it.id} role="presentation">
                {head && <div className="palette-group">{head}</div>}
                <div id={it.id} role="option" aria-selected={i === sel} className="palette-item"
                  onMouseEnter={() => setSel(i)} onClick={it.run}>
                  <Icon className="size-4 shrink-0 text-ink-3" />
                  <span className="grid min-w-0">
                    <span className="truncate text-[14px] font-semibold text-ink">{it.label}</span>
                    <span className="truncate text-[12.5px] text-ink-3">{it.hint}</span>
                  </span>
                  {i === sel && <CornerDownLeft className="ml-auto size-3.5 shrink-0 text-ink-3" />}
                </div>
              </li>
            );
          })}
        </ul>
      </div>
    </div>
  );
}
