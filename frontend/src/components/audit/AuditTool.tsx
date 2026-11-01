"use client";

import Link from "next/link";
import { useEffect, useRef, useState } from "react";
import { Copy, Check, Download, FileJson, Loader2, Printer, ShieldCheck, Upload } from "lucide-react";
import {
  BackendHttpError,
  fetchAuditExample,
  fetchDemoCases,
  fetchJobs,
  postAudit,
  type AuditResponse,
  type ClaimType,
  type DemoCase,
  type Job,
} from "@/lib/api";
import { auditMarkdown, download, loadHistory, saveAudit } from "@/lib/history";
import { ShareGauge } from "./ShareGauge";

// Earned vs fabricated audit: the research question of this project, on one resume.
// The original is the only evidence; anything an LLM rewrite claims beyond it is
// "unsupported", and the ATS points it buys are the fabricated part of the gain.

export const CLAIM_LABEL: Record<ClaimType, string> = {
  skill: "Skill not in your resume",
  metric: "Number you never wrote",
  role_scope: "Bigger role than you stated",
  credential: "Degree or certificate not listed",
  content: "New content",
};

const slug = (s: string) => s.toLowerCase().replace(/[^a-z0-9]+/g, "-").replace(/^-|-$/g, "").slice(0, 40) || "job";

const EMPTY_JOB: Job = { id: "", title: "", company: "", tags: [], url: "", description: "" };

export function errorText(e: unknown): string {
  if (e instanceof BackendHttpError) {
    const m = e.message.match(/: (\{[\s\S]*\})$/);
    if (m) {
      try {
        return JSON.parse(m[1]).detail ?? e.message;
      } catch {
        /* fall through */
      }
    }
  }
  return e instanceof Error ? e.message : "Unexpected error.";
}

function Field({ label, hint, children }: { label: string; hint?: string; children: React.ReactNode }) {
  return (
    <div className="grid gap-1.5">
      <span className="text-[14px] font-semibold text-ink">{label}</span>
      {hint && <span className="-mt-1 text-[13px] text-ink-3">{hint}</span>}
      {children}
    </div>
  );
}

// A textarea that also takes a dropped or picked .txt / .md file.
function DropText({ value, onChange, disabled, className, label }: {
  value: string; onChange: (v: string) => void; disabled?: boolean; className?: string; label: string;
}) {
  const [over, setOver] = useState(false);
  const [note, setNote] = useState<string | null>(null);
  const read = async (f?: File | null) => {
    if (!f) return;
    if (!/\.(txt|md|text)$/i.test(f.name) && !f.type.startsWith("text/")) {
      setNote(`${f.name} is not a text file. Copy the text out of it and paste it here.`);
      return;
    }
    setNote(null);
    onChange(await f.text());
  };
  return (
    <div className={`drop ${over ? "drop-over" : ""}`}
      onDragOver={(e) => { e.preventDefault(); setOver(true); }}
      onDragLeave={() => setOver(false)}
      onDrop={(e) => { e.preventDefault(); setOver(false); read(e.dataTransfer.files[0]); }}>
      <textarea className={className} value={value} disabled={disabled} aria-label={label}
        onChange={(e) => onChange(e.target.value)} />
      <label className="drop-pick">
        <Upload className="size-3.5" /> Open a .txt file
        <input type="file" accept=".txt,.md,text/plain" className="sr-only" disabled={disabled}
          onChange={(e) => read(e.target.files?.[0])} />
      </label>
      {note && <p className="mt-1 text-[12.5px] text-eye">{note}</p>}
    </div>
  );
}

const inputCls =
  "w-full rounded-lg border border-line-2 bg-paper-2 px-3 py-2 text-[14px] text-ink outline-none focus-visible:border-ink focus-visible:ring-3 focus-visible:ring-ink/20";

function GainBar({ r }: { r: AuditResponse }) {
  const { orig, llm, stripped } = r.scores;
  const lo = Math.min(orig, stripped, llm);
  const hi = Math.max(orig, stripped, llm);
  const pad = Math.max(4, (hi - lo) * 0.25);
  const min = Math.max(0, lo - pad);
  const max = Math.min(100, hi + pad);
  const x = (v: number) => `${((v - min) / (max - min)) * 100}%`;
  const earnedEnd = Math.max(orig, Math.min(stripped, llm));
  return (
    <div className="grid gap-2">
      <div className="gainbar relative h-10 rounded-lg border border-line bg-paper-2" role="img"
        aria-label={`Original ${orig}, rewrite ${llm}, earned part ends at ${earnedEnd}`}>
        {earnedEnd > orig && (
          <div className="absolute inset-y-0 bg-moss/80" style={{ left: x(orig), width: `calc(${x(earnedEnd)} - ${x(orig)})` }} />
        )}
        {llm > earnedEnd && (
          <div className="absolute inset-y-0 bg-eye/80" style={{ left: x(earnedEnd), width: `calc(${x(llm)} - ${x(earnedEnd)})` }} />
        )}
        <div className="absolute inset-y-[-6px] w-0.5 bg-ink" style={{ left: x(orig) }} />
      </div>
      <div className="relative h-5 text-[12px] text-ink-3 tabular-nums">
        <span className="absolute -translate-x-1/2" style={{ left: x(orig) }}>original {orig}</span>
        <span className="absolute -translate-x-1/2" style={{ left: x(llm) }}>rewrite {llm}</span>
      </div>
      <div className="flex flex-wrap gap-4 text-[13px] text-ink-2">
        <span className="inline-flex items-center gap-1.5"><i className="size-3 rounded-sm bg-moss/80" /> earned: the original supports it</span>
        <span className="inline-flex items-center gap-1.5"><i className="size-3 rounded-sm bg-eye/80" /> fabricated: bought by unsupported claims</span>
      </div>
    </div>
  );
}

function Headline({ r }: { r: AuditResponse }) {
  if (r.fabricated_share === null && r.gain < 0) {
    return (
      <p className="text-[18px] text-ink-2">
        The rewrite <span className="text-eye">lowered</span> the ATS score by {-r.gain} points, so there is no gain to
        split. Its unsupported claims are still marked below.
      </p>
    );
  }
  if (r.fabricated_share === null) {
    return (
      <p className="text-[18px] text-ink-2">
        The rewrite moved the ATS score by {r.gain >= 0 ? "+" : ""}{r.gain} points. That is under {r.min_gain}, too small to
        split into earned and fabricated parts.
      </p>
    );
  }
  const pct = Math.round(r.fabricated_share * 100);
  return (
    <div className="grid gap-2">
      <p className="font-display text-[30px] leading-tight font-semibold tracking-[-0.02em] text-ink">
        {pct <= 0
          ? <>All of the +{r.gain} point gain is backed by your resume.</>
          : <>{Math.max(0, pct)}% of the +{r.gain} point gain comes from claims your resume doesn&apos;t support.</>}
      </p>
      {pct > 100 && (
        <p className="text-[15px] text-ink-2">
          Over 100% means the honest part of the rewrite scores <b>below</b> your original ({r.scores.stripped} vs{" "}
          {r.scores.orig}): the rewrite dropped real material and replaced it with unsupported claims.
        </p>
      )}
    </div>
  );
}

function ScoreCard({ label, value, note, tone }: { label: string; value?: number; note: string; tone?: "eye" | "moss" }) {
  return (
    <div className="rounded-xl border border-line bg-paper p-4">
      <div className="text-[13px] text-ink-3">{label}</div>
      <div className={`font-display text-[30px] leading-none font-semibold tabular-nums ${tone === "eye" ? "text-eye" : tone === "moss" ? "text-moss" : "text-ink"}`}>
        {value ?? "–"}
      </div>
      <div className="mt-1.5 text-[12.5px] leading-snug text-ink-2">{note}</div>
    </div>
  );
}

function CopyButton({ text }: { text: string }) {
  const [done, setDone] = useState(false);
  return (
    <button
      type="button"
      onClick={() => {
        navigator.clipboard?.writeText(text).then(() => {
          setDone(true);
          setTimeout(() => setDone(false), 1500);
        });
      }}
      className="tool-btn"
    >
      {done ? <Check className="size-3.5" /> : <Copy className="size-3.5" />} {done ? "Copied" : "Copy"}
    </button>
  );
}

export function RewriteView({ r }: { r: AuditResponse }) {
  return (
    <div className="grid gap-1 rounded-xl border border-line bg-paper-2 p-4 text-[14px] leading-relaxed sm:p-5">
      {r.lines.map((line, li) => (
        <div key={li} className="min-h-[1em]">
          {line.map((u, ui) =>
            u.claims.length ? (
              <span key={ui} className="group relative">
                <mark className="rounded bg-[var(--eye-soft)] px-0.5 text-ink decoration-eye/60 underline decoration-wavy underline-offset-4">
                  {u.text}
                </mark>{" "}
                <span className="mt-1 mb-2 flex flex-wrap gap-1.5">
                  {u.claims.map((c, ci) => (
                    <span key={ci} className="rounded-full border border-eye/40 bg-paper px-2 py-0.5 text-[12px] text-eye">
                      {c.type === "content" ? CLAIM_LABEL[c.type] : <>{CLAIM_LABEL[c.type]}: <b>{c.text}</b></>}
                    </span>
                  ))}
                  {u.closest_original && (
                    <span className="basis-full text-[12.5px] text-ink-3">
                      Closest line in your resume: &ldquo;{u.closest_original}&rdquo;
                    </span>
                  )}
                </span>
              </span>
            ) : (
              <span key={ui}>{u.text} </span>
            ),
          )}
        </div>
      ))}
    </div>
  );
}

function SideBySide({ r, original }: { r: AuditResponse; original: string }) {
  return (
    <div className="grid gap-4 lg:grid-cols-2">
      <div className="grid content-start gap-2">
        <span className="text-[13px] font-semibold text-ink-2">Your original</span>
        <pre className="m-0 rounded-xl border border-line bg-paper p-4 font-[family-name:var(--font-body)] text-[14px] leading-relaxed whitespace-pre-wrap text-ink-2 sm:p-5">
          {original}
        </pre>
      </div>
      <div className="grid content-start gap-2">
        <span className="text-[13px] font-semibold text-ink-2">The rewrite, marked</span>
        <RewriteView r={r} />
      </div>
    </div>
  );
}

type View = "marked" | "side" | "guarded";

export function AuditTool() {
  const [resume, setResume] = useState("");
  const [job, setJob] = useState<Job>(EMPTY_JOB);
  const [rewrite, setRewrite] = useState("");
  const [guarded, setGuarded] = useState(true);
  const [busy, setBusy] = useState(false);
  const [elapsed, setElapsed] = useState(0);
  const [error, setError] = useState<string | null>(null);
  const [result, setResult] = useState<AuditResponse | null>(null);
  const [snapshot, setSnapshot] = useState<Job[]>([]);
  const [cases, setCases] = useState<DemoCase[]>([]);
  const [caseId, setCaseId] = useState<string | null>(null);
  const [view, setView] = useState<View>("marked");
  const [ran, setRan] = useState<{ resume: string; job: Job } | null>(null);
  const abort = useRef<AbortController | null>(null);
  const resultsRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (!busy) return;
    const t0 = Date.now();
    const id = setInterval(() => setElapsed(Math.round((Date.now() - t0) / 1000)), 500);
    return () => clearInterval(id);
  }, [busy]);

  useEffect(() => () => abort.current?.abort(), []);

  function applyCase(c: DemoCase) {
    setCaseId(c.id);
    setResume(c.original);
    setJob({ ...EMPTY_JOB, id: c.id, title: c.job.title, company: c.job.company ?? "", description: c.job.description });
    setRewrite(c.rewrite);
    setGuarded(false); // instant: a pasted rewrite needs no model unless a guarded rewrite is asked for
  }

  useEffect(() => {
    fetchJobs()
      .then((r) => setSnapshot(r.jobs))
      .catch(() => setSnapshot([]));
    // ?h=<id> reopens an audit from History; ?case=<id> loads a demo case (from the command palette)
    const params = new URLSearchParams(window.location.search);
    const saved = params.get("h") ? loadHistory().find((x) => x.id === params.get("h")) : undefined;
    if (saved) {
      const j = { ...EMPTY_JOB, ...saved.job };
      // one-time restore from the URL and localStorage, which the server render cannot see
      /* eslint-disable react-hooks/set-state-in-effect */
      setResume(saved.resume);
      setRewrite(saved.rewrite);
      setJob(j);
      setRan({ resume: saved.resume, job: j });
      setResult(saved.result);
      /* eslint-enable react-hooks/set-state-in-effect */
    }
    fetchDemoCases()
      .then((r) => {
        setCases(r.cases);
        const c = r.cases.find((x) => x.id === params.get("case"));
        if (c) applyCase(c);
      })
      .catch(() => setCases([]));
  }, []);

  async function loadExample() {
    setError(null);
    try {
      const ex = await fetchAuditExample();
      setCaseId(null);
      setResume(ex.resume_text);
      setJob({ ...EMPTY_JOB, ...ex.job });
    } catch (e) {
      setError(errorText(e));
    }
  }

  async function run() {
    abort.current?.abort();
    abort.current = new AbortController();
    setBusy(true);
    setElapsed(0);
    setError(null);
    try {
      const r = await postAudit(resume, job, rewrite, guarded, abort.current.signal);
      setResult(r);
      setRan({ resume, job });
      setView("marked");
      saveAudit({ job: { title: job.title, company: job.company }, resume, rewrite, result: r });
      requestAnimationFrame(() => resultsRef.current?.scrollIntoView({ behavior: "smooth", block: "start" }));
    } catch (e) {
      if (!(e instanceof DOMException && e.name === "AbortError")) setError(errorText(e));
    } finally {
      setBusy(false);
    }
  }

  const canRun = resume.trim().length > 0 && (job.title.trim() || job.description.trim()) && !busy;
  const needsModel = !rewrite.trim() || guarded;
  const reportJob = ran?.job ?? job;

  return (
    <section id="audit" className="scroll-mt-20">
      <div className="tool grid gap-6 p-5 sm:p-7 print-hide">
        {cases.length > 0 && (
          <div className="grid gap-2">
            <span className="text-[14px] font-semibold text-ink">Try a demo case</span>
            <div className="flex flex-wrap gap-2">
              {cases.map((c, i) => (
                <button key={c.id} type="button" disabled={busy} onClick={() => applyCase(c)} title={c.shows}
                  aria-pressed={caseId === c.id} className="case-chip">
                  <b>{i + 1}</b> {c.job.title}
                </button>
              ))}
            </div>
            {caseId && <p className="text-[13px] text-ink-3">{cases.find((c) => c.id === caseId)?.shows}</p>}
          </div>
        )}
        <div className="grid gap-6 lg:grid-cols-2">
          <Field label="Your original resume" hint="Plain text, typed, pasted or dropped. This is the only evidence the checker accepts.">
            <DropText label="Your original resume" className={`${inputCls} min-h-[320px] font-[family-name:var(--font-code)] text-[13px]`}
              value={resume} onChange={(v) => { setResume(v); setCaseId(null); }} disabled={busy} />
          </Field>
          <div className="grid content-start gap-4">
            {snapshot.length > 0 && (
              <Field label="Pick a real listing" hint="From the dated job snapshot the experiment uses, or type your own below.">
                <select className={inputCls} disabled={busy} aria-label="Pick a real listing"
                  value={job.id && snapshot.some((j) => j.id === job.id) ? job.id : ""}
                  onChange={(e) => {
                    const j = snapshot.find((x) => x.id === e.target.value);
                    if (j) setJob({ ...EMPTY_JOB, ...j });
                  }}>
                  <option value="">Choose a job…</option>
                  {[...new Set(snapshot.map((j) => j.category ?? ""))].sort().map((cat) => (
                    <optgroup key={cat} label={cat.replace(/-/g, " ").toLowerCase()}>
                      {snapshot.filter((j) => (j.category ?? "") === cat).map((j) => (
                        <option key={j.id} value={j.id}>{j.title}{j.company ? `, ${j.company}` : ""}</option>
                      ))}
                    </optgroup>
                  ))}
                </select>
              </Field>
            )}
            <Field label="Job title">
              <input className={inputCls} value={job.title} disabled={busy} aria-label="Job title"
                onChange={(e) => setJob({ ...job, title: e.target.value })} />
            </Field>
            <Field label="Job description">
              <textarea className={`${inputCls} min-h-[236px]`} value={job.description} disabled={busy} aria-label="Job description"
                onChange={(e) => setJob({ ...job, description: e.target.value })} />
            </Field>
          </div>
        </div>

        <details className="rounded-xl border border-line bg-paper-2 p-4" open={rewrite.length > 0}>
          <summary className="cursor-pointer text-[14px] font-semibold text-ink">
            Already rewrote it with ChatGPT, Gemini or another tool? Paste that version (optional)
          </summary>
          <p className="mt-2 text-[13px] text-ink-3">Leave empty and a local model writes one, prompted the way a job seeker would.</p>
          <div className="mt-3">
            <DropText label="Rewritten resume" className={`${inputCls} min-h-[200px] text-[13px]`} value={rewrite}
              disabled={busy} onChange={setRewrite} />
          </div>
        </details>

        <div className="flex flex-wrap items-center gap-4">
          <button type="button" onClick={run} disabled={!canRun}
            className="inline-flex h-11 items-center gap-2 rounded-xl bg-ink px-5 text-[15px] font-semibold text-paper hover:bg-ink/85 disabled:opacity-40">
            {busy ? <Loader2 className="size-4 animate-spin" /> : <ShieldCheck className="size-4" />}
            {busy ? `Auditing… ${elapsed}s` : "Audit the rewrite"}
          </button>
          <button type="button" onClick={loadExample} disabled={busy}
            className="h-11 rounded-xl border border-line-2 px-4 text-[14px] text-ink-2 hover:bg-paper-2 disabled:opacity-40">
            Load a random dataset resume
          </button>
          <label className="inline-flex items-center gap-2 text-[14px] text-ink-2">
            <input type="checkbox" checked={guarded} onChange={(e) => setGuarded(e.target.checked)} disabled={busy}
              className="size-4 accent-[var(--moss)]" />
            Also write a guarded rewrite (keeps only earned gain)
          </label>
        </div>
        {busy && needsModel && (
          <p className="-mt-2 text-[13px] text-ink-3">The local model is writing and revising. This usually takes 30–90 seconds.</p>
        )}
        {error && (
          <p role="alert" className="rounded-lg border border-eye/40 bg-[var(--eye-soft)] px-3 py-2 text-[14px] text-eye">{error}</p>
        )}
      </div>

      {result && (
        <div ref={resultsRef} className="scroll-mt-20 grid gap-8 pt-12">
          <h2 className="print-only font-display text-[28px] font-semibold">
            Resume audit: {reportJob.title}{reportJob.company ? `, ${reportJob.company}` : ""}
          </h2>
          {result.refusal && (
            <p className="rounded-lg border border-amber/40 bg-[var(--amber-soft)] px-3 py-2 text-[14px] text-ink">
              The model answered with an assessment instead of a resume. Small models do this for some mismatched jobs
              (8% of the pilot); the experiment counts these as refusals and leaves them out.
            </p>
          )}
          <div className="result-top">
            <ShareGauge share={result.fabricated_share} />
            <div className="grid content-center gap-5">
              <Headline r={result} />
              <GainBar r={result} />
            </div>
          </div>
          <div className="print-hide flex flex-wrap items-center gap-2">
            <button type="button" className="tool-btn"
              onClick={() => download(`resume-audit-${slug(reportJob.title)}.md`, auditMarkdown(reportJob, result))}>
              <Download className="size-3.5" /> Report (.md)
            </button>
            <button type="button" className="tool-btn"
              onClick={() => download(`resume-audit-${slug(reportJob.title)}.json`, JSON.stringify(result, null, 2), "application/json")}>
              <FileJson className="size-3.5" /> Raw result (.json)
            </button>
            <button type="button" className="tool-btn" onClick={() => window.print()}>
              <Printer className="size-3.5" /> Print
            </button>
            <span className="text-[13px] text-ink-3">
              Saved to <Link href="/history" className="underline underline-offset-2">History</Link> in this browser.
            </span>
          </div>

          <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-4">
            <ScoreCard label="Your original" value={result.scores.orig} note="ATS score as you wrote it." />
            <ScoreCard label={result.source === "pasted" ? "Your pasted rewrite" : `AI rewrite (${result.model})`}
              value={result.scores.llm} note="Everything the rewrite claims." tone="eye" />
            <ScoreCard label="Rewrite minus unsupported claims" value={result.scores.stripped}
              note="Flagged lines cut or reverted to your closest original line." />
            <ScoreCard label="Guarded rewrite" value={result.scores.guarded} tone="moss"
              note={result.scores.guarded === undefined ? "Not requested." : `Revised ${result.guarded_rounds}× until nothing was flagged.`} />
          </div>

          <div className="view-tabs print-hide" role="tablist" aria-label="Result view">
            {([["marked", "Marked rewrite"], ["side", "Side by side"], ["guarded", "Guarded rewrite"]] as [View, string][]).map(([v, label]) => (
              <button key={v} type="button" role="tab" aria-selected={view === v} onClick={() => setView(v)}
                disabled={v === "guarded" && !result.texts.guarded}
                title={v === "guarded" && !result.texts.guarded ? "Tick “Also write a guarded rewrite” and run again" : undefined}>
                {label}
              </button>
            ))}
          </div>

          {view !== "guarded" && (
            <div className="grid gap-3">
              <h2 className="font-display text-[24px] font-semibold tracking-[-0.02em] text-ink">
                {result.n_flagged_units} of {result.n_units} lines carry unsupported claims
              </h2>
              <div className="flex flex-wrap gap-2">
                {(Object.keys(CLAIM_LABEL) as ClaimType[]).map((t) => (
                  <span key={t} className={`rounded-full border px-3 py-1 text-[13px] ${result.counts[t] ? "border-eye/40 text-eye" : "border-line text-ink-3"}`}>
                    {CLAIM_LABEL[t]}: <b className="tabular-nums">{result.counts[t]}</b>
                  </span>
                ))}
              </div>
              {view === "side" ? <SideBySide r={result} original={ran?.resume ?? resume} /> : <RewriteView r={result} />}
            </div>
          )}

          {result.texts.guarded && view === "guarded" && (
            <div className="grid gap-3">
              <div className="flex items-center justify-between gap-4">
                <h2 className="font-display text-[24px] font-semibold tracking-[-0.02em] text-ink">Guarded rewrite</h2>
                <CopyButton text={result.texts.guarded} />
              </div>
              <p className="text-[14px] text-ink-2">
                Same tailoring, but every claim is backed by your original. Score {result.scores.guarded} vs{" "}
                {result.scores.orig} originally.
              </p>
              <pre className="max-h-[520px] overflow-auto rounded-xl border border-line bg-paper-2 p-4 text-[13px] leading-relaxed whitespace-pre-wrap text-ink">
                {result.texts.guarded}
              </pre>
            </div>
          )}

          <p className="max-w-[70ch] text-[13px] text-ink-3">
            The checker is rule-based: it accepts a claim when the skill, number, role word or degree appears in your original
            (synonyms included), and flags lines whose wording is mostly new. It can be wrong both ways; see{" "}
            <Link href="/method" className="underline underline-offset-2">Method</Link> for its measured accuracy.
          </p>
        </div>
      )}
    </section>
  );
}
