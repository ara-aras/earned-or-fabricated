"use client";

import type { AuditResponse, Job } from "@/lib/api";

// Past audits live only in this browser (localStorage). Nothing is sent anywhere,
// which keeps the "your resume never leaves your machine" promise of the app.

export type SavedAudit = {
  id: string;
  at: number;
  job: Pick<Job, "title" | "company">;
  resume: string;
  rewrite: string;
  result: AuditResponse;
};

const KEY = "eof.history.v1";
const MAX = 25;
const EVENT = "eof-history";

export function loadHistory(): SavedAudit[] {
  try {
    const raw = localStorage.getItem(KEY);
    return raw ? (JSON.parse(raw) as SavedAudit[]) : [];
  } catch {
    return [];
  }
}

function store(list: SavedAudit[]) {
  try {
    localStorage.setItem(KEY, JSON.stringify(list.slice(0, MAX)));
  } catch {
    // quota or blocked storage: history is a convenience, the audit still works
  }
  window.dispatchEvent(new Event(EVENT));
}

export function saveAudit(entry: Omit<SavedAudit, "id" | "at">): SavedAudit {
  const saved: SavedAudit = { ...entry, id: Math.random().toString(36).slice(2, 10), at: Date.now() };
  store([saved, ...loadHistory()]);
  return saved;
}

export function removeAudit(id: string) {
  store(loadHistory().filter((h) => h.id !== id));
}

export function clearHistory() {
  store([]);
}

export function onHistoryChange(fn: () => void) {
  window.addEventListener(EVENT, fn);
  window.addEventListener("storage", fn);
  return () => {
    window.removeEventListener(EVENT, fn);
    window.removeEventListener("storage", fn);
  };
}

/** A plain-text report of one audit, for download or pasting into an e-mail. */
export function auditMarkdown(job: Pick<Job, "title" | "company">, r: AuditResponse): string {
  const pct = r.fabricated_share === null ? "n/a" : `${Math.round(r.fabricated_share * 100)}%`;
  const lines = [
    `# Resume audit: ${job.title}${job.company ? `, ${job.company}` : ""}`,
    "",
    `| Version | ATS score |`,
    `| --- | --- |`,
    `| Original | ${r.scores.orig} |`,
    `| Rewrite | ${r.scores.llm} |`,
    `| Rewrite minus unsupported claims | ${r.scores.stripped} |`,
    ...(r.scores.guarded !== undefined ? [`| Guarded rewrite | ${r.scores.guarded} |`] : []),
    "",
    `Gain ${r.gain >= 0 ? "+" : ""}${r.gain} points. Earned ${r.earned_gain}, fabricated ${r.fabricated_gain}. Fabricated share: ${pct}.`,
    "",
    `## ${r.n_flagged_units} of ${r.n_units} lines carry unsupported claims`,
    "",
  ];
  for (const line of r.lines)
    for (const u of line)
      if (u.claims.length)
        lines.push(`- "${u.text.trim()}"`, ...u.claims.map((c) => `  - ${c.type}: ${c.text || c.reason}`));
  if (r.texts.guarded) lines.push("", "## Guarded rewrite", "", r.texts.guarded);
  return lines.join("\n");
}

export function download(name: string, text: string, type = "text/markdown") {
  const url = URL.createObjectURL(new Blob([text], { type }));
  const a = Object.assign(document.createElement("a"), { href: url, download: name });
  a.click();
  setTimeout(() => URL.revokeObjectURL(url), 1000);
}
