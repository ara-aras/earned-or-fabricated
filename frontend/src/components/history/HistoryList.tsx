"use client";

import Link from "next/link";
import { useEffect, useState } from "react";
import { Download, Trash2 } from "lucide-react";
import { auditMarkdown, clearHistory, download, loadHistory, onHistoryChange, removeAudit, type SavedAudit } from "@/lib/history";

const fmt = (t: number) =>
  new Date(t).toLocaleString(undefined, { day: "numeric", month: "short", hour: "2-digit", minute: "2-digit" });

// One row's split bar: original, earned and fabricated on a shared 0–100 axis.
function MiniSplit({ s }: { s: SavedAudit }) {
  const { orig, llm, stripped } = s.result.scores;
  const earnedEnd = Math.max(orig, Math.min(stripped, llm));
  return (
    <svg viewBox="0 0 200 14" className="mini-split" role="img"
      aria-label={`Original ${orig}, rewrite ${llm}, earned up to ${earnedEnd}`}>
      <rect x="0" y="3" width="200" height="8" rx="4" className="t" />
      <rect x="0" y="3" width={orig * 2} height="8" rx="4" className="o" />
      {earnedEnd > orig && <rect x={orig * 2} y="3" width={(earnedEnd - orig) * 2} height="8" className="e" />}
      {llm > earnedEnd && <rect x={earnedEnd * 2} y="3" width={(llm - earnedEnd) * 2} height="8" className="f" />}
    </svg>
  );
}

// Fabricated share across your audits, oldest to newest.
function Trend({ list }: { list: SavedAudit[] }) {
  const pts = [...list].reverse().filter((h) => h.result.fabricated_share !== null);
  if (pts.length < 2) return null;
  const W = 600;
  const H = 140;
  const max = Math.max(1.2, ...pts.map((p) => p.result.fabricated_share!));
  const xy = pts.map((p, i) => [24 + (i / (pts.length - 1)) * (W - 48), H - 20 - (p.result.fabricated_share! / max) * (H - 40)]);
  const y100 = H - 20 - (1 / max) * (H - 40);
  return (
    <figure className="trend">
      <figcaption className="text-[13px] text-ink-3">Fabricated share of each audit, oldest first</figcaption>
      <svg viewBox={`0 0 ${W} ${H}`} role="img" aria-label="Line chart of fabricated share across your audits">
        <line x1="24" x2={W - 24} y1={H - 20} y2={H - 20} className="axis" />
        <line x1="24" x2={W - 24} y1={y100} y2={y100} className="ref" />
        <text x={W - 24} y={y100 - 6} textAnchor="end" className="lbl">100%</text>
        <polyline points={xy.map((p) => p.join(",")).join(" ")} className="line" />
        {xy.map(([x, y], i) => (
          <circle key={i} cx={x} cy={y} r="4.5" className="dot">
            <title>{`${pts[i].job.title}: ${Math.round(pts[i].result.fabricated_share! * 100)}%`}</title>
          </circle>
        ))}
      </svg>
    </figure>
  );
}

export function HistoryList() {
  const [list, setList] = useState<SavedAudit[] | null>(null);

  useEffect(() => {
    const sync = () => setList(loadHistory());
    sync();
    return onHistoryChange(sync);
  }, []);

  if (list === null) return null;

  if (list.length === 0) {
    return (
      <div className="empty">
        <svg viewBox="0 0 80 80" aria-hidden className="empty-glyph">
          <rect x="18" y="10" width="44" height="58" rx="4" />
          <path d="M27 26h26M27 35h18M27 44h22" />
          <path className="pen" d="M44 40c8-4 17 0 16 5-1 6-13 8-19 4-4-3-1-7 4-9" />
        </svg>
        <p className="font-display text-[22px] font-semibold text-ink">No audits yet</p>
        <p className="max-w-[46ch] text-[15px] text-ink-2">Every audit you run is kept here, in this browser only, so you can reopen it or compare rewrites later.</p>
        <Link href="/audit" className="btn-dark h-11 px-5 text-[15px]">Run your first audit</Link>
      </div>
    );
  }

  return (
    <div className="grid gap-8">
      <Trend list={list} />
      <ul className="history">
        {list.map((h) => {
          const pct = h.result.fabricated_share === null ? null : Math.round(h.result.fabricated_share * 100);
          return (
            <li key={h.id} className="history-row">
              <Link href={`/audit?h=${h.id}`} className="grid min-w-0 gap-1">
                <span className="truncate font-semibold text-ink">{h.job.title || "Untitled job"}{h.job.company ? `, ${h.job.company}` : ""}</span>
                <span className="text-[13px] text-ink-3">
                  {fmt(h.at)}. {h.result.source === "pasted" ? "Pasted rewrite" : `Rewritten by ${h.result.model}`}, {h.result.n_flagged_units} flagged {h.result.n_flagged_units === 1 ? "line" : "lines"}
                </span>
              </Link>
              <MiniSplit s={h} />
              <span className={`history-pct ${pct === null ? "text-ink-3" : pct >= 50 ? "text-eye" : pct > 0 ? "text-amber" : "text-moss"}`}>
                {pct === null ? "–" : `${pct}%`}
              </span>
              <span className="flex gap-1">
                <button type="button" className="icon-btn" aria-label={`Download the report for ${h.job.title}`}
                  onClick={() => download(`resume-audit-${h.id}.md`, auditMarkdown(h.job, h.result))}>
                  <Download className="size-4" />
                </button>
                <button type="button" className="icon-btn" aria-label={`Delete the audit for ${h.job.title}`} onClick={() => removeAudit(h.id)}>
                  <Trash2 className="size-4" />
                </button>
              </span>
            </li>
          );
        })}
      </ul>
      <button type="button" className="tool-btn w-fit"
        onClick={() => window.confirm("Delete every saved audit from this browser?") && clearHistory()}>
        <Trash2 className="size-3.5" /> Delete all saved audits
      </button>
    </div>
  );
}
