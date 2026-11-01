"use client";

import Link from "next/link";
import { useEffect, useRef, useState } from "react";
import { ArrowRight, Eye, Loader2, RotateCcw } from "lucide-react";
import { CLAIM_LABEL, errorText } from "@/components/audit/AuditTool";
import { fetchDemoCases, postAudit, type AuditResponse, type AuditUnit, type DemoCase } from "@/lib/api";
import { gsap, MOTION, useGSAP } from "@/lib/gsap";

// Spot the fabrication: read a real AI rewrite next to the original, mark the lines you think
// claim more than the original supports, then compare your marks with the checker's.
// The audit runs on a pasted rewrite with no guarded rewrite, so it needs no model and is instant.

type Line = { text: string; units: AuditUnit[]; flagged: boolean };
type Verdict = "hit" | "miss" | "false" | "pass";

// a quick pen underline along the bottom of the row (rings look like strike-throughs on wide rows)
const RING = "M1.5 35 C 22 31.5, 48 37.5, 72 33.5 S 94 34.5, 98.5 32.5";

function verdict(marked: boolean, flagged: boolean): Verdict {
  if (marked && flagged) return "hit";
  if (!marked && flagged) return "miss";
  if (marked && !flagged) return "false";
  return "pass";
}

const VERDICT_TEXT: Record<Verdict, string> = {
  hit: "You caught it",
  miss: "You missed this one",
  false: "The checker found this supported",
  pass: "",
};

export function SpotGame() {
  const [cases, setCases] = useState<DemoCase[]>([]);
  const [idx, setIdx] = useState(0);
  const [lines, setLines] = useState<Line[] | null>(null);
  const [marks, setMarks] = useState<Set<number>>(new Set());
  const [revealed, setRevealed] = useState(false);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [showOrig, setShowOrig] = useState(false);
  const [tally, setTally] = useState<{ hits: number; flagged: number; falses: number; rounds: number }>({ hits: 0, flagged: 0, falses: 0, rounds: 0 });
  const root = useRef<HTMLDivElement>(null);

  const { contextSafe } = useGSAP({ scope: root });

  // start a round: clear the board and fetch the checker's verdicts for the chosen case
  function pick(i: number, list = cases) {
    setIdx(i);
    setLines(null);
    setMarks(new Set());
    setRevealed(false);
    setError(null);
    if (list[i]) setLoading(true);
  }

  useEffect(() => {
    fetchDemoCases()
      .then((r) => {
        setCases(r.cases);
        pick(0, r.cases);
      })
      .catch((e) => setError(errorText(e)));
    // eslint-disable-next-line react-hooks/exhaustive-deps -- runs once; pick only sets state
  }, []);

  const c = cases[idx];

  useEffect(() => {
    if (!c) return;
    let live = true;
    const job = { id: c.id, title: c.job.title, company: c.job.company ?? "", tags: [], url: "", description: c.job.description };
    postAudit(c.original, job, c.rewrite, false)
      .then((r: AuditResponse) => {
        if (!live) return;
        setLines(
          r.lines
            .map((units) => ({ text: units.map((u) => u.text).join(" ").trim(), units, flagged: units.some((u) => u.claims.length > 0) }))
            .filter((l) => l.text.length > 0),
        );
      })
      .catch((e) => live && setError(errorText(e)))
      .finally(() => live && setLoading(false));
    return () => {
      live = false;
    };
  }, [c]);

  const toggle = contextSafe((i: number, el: HTMLElement) => {
    if (revealed) return;
    const next = new Set(marks);
    const path = el.querySelector(".spot-ring path");
    if (next.has(i)) {
      next.delete(i);
    } else {
      next.add(i);
      if (path && window.matchMedia(MOTION).matches)
        gsap.fromTo(path, { strokeDashoffset: 1 }, { strokeDashoffset: 0, duration: 0.45, ease: "power1.inOut" });
    }
    setMarks(next);
  });

  const check = contextSafe(() => {
    if (!lines) return;
    setRevealed(true);
    const flagged = lines.filter((l) => l.flagged).length;
    const hits = lines.filter((l, i) => l.flagged && marks.has(i)).length;
    const falses = lines.filter((l, i) => !l.flagged && marks.has(i)).length;
    setTally((t) => ({ hits: t.hits + hits, flagged: t.flagged + flagged, falses: t.falses + falses, rounds: t.rounds + 1 }));
    requestAnimationFrame(() => {
      if (!window.matchMedia(MOTION).matches) return;
      gsap.from(".spot-verdict", { opacity: 0, y: -4, duration: 0.3, stagger: 0.04 });
      gsap.from(".spot-score", { scale: 1.6, rotate: -14, opacity: 0, duration: 0.5, ease: "back.out(2)" });
    });
  });

  if (error && !cases.length) {
    return (
      <p role="alert" className="rounded-lg border border-eye/40 bg-[var(--eye-soft)] px-3 py-2 text-[14px] text-eye">
        {error}
      </p>
    );
  }

  const flaggedCount = lines?.filter((l) => l.flagged).length ?? 0;
  const hits = lines?.filter((l, i) => l.flagged && marks.has(i)).length ?? 0;
  const falses = lines?.filter((l, i) => !l.flagged && marks.has(i)).length ?? 0;
  const score = flaggedCount ? Math.max(0, Math.round(((hits - falses * 0.5) / flaggedCount) * 100)) : 100;

  return (
    <div ref={root} className="grid gap-6">
      <div className="flex flex-wrap items-center gap-2" role="tablist" aria-label="Rounds">
        {cases.map((x, i) => (
          <button key={x.id} type="button" role="tab" aria-selected={i === idx} className="case-chip" onClick={() => pick(i)}>
            <b>{i + 1}</b> {x.job.title}
          </button>
        ))}
        {tally.rounds > 0 && (
          <span className="ml-auto text-[13px] text-ink-2 tabular-nums">
            Across {tally.rounds} {tally.rounds === 1 ? "round" : "rounds"}: caught {tally.hits} of {tally.flagged}, {tally.falses} false {tally.falses === 1 ? "alarm" : "alarms"}
          </span>
        )}
      </div>

      {c && (
        <div className="spot-brief">
          <div className="grid gap-1">
            <span className="text-[13px] text-ink-3">Round {idx + 1}: the job</span>
            <span className="font-display text-[24px] leading-tight font-semibold text-ink">
              {c.job.title}{c.job.company ? `, ${c.job.company}` : ""}
            </span>
          </div>
          <button type="button" className="tool-btn lg:hidden" onClick={() => setShowOrig((v) => !v)} aria-expanded={showOrig}>
            <Eye className="size-3.5" /> {showOrig ? "Hide" : "Show"} the original
          </button>
        </div>
      )}

      <div className="spot-board">
        <div className={`spot-orig ${showOrig ? "is-open" : ""}`}>
          <span className="text-[13px] font-semibold text-ink-2">The original resume: the only evidence</span>
          <pre>{c?.original}</pre>
        </div>

        <div className="grid content-start gap-3">
          <span className="text-[13px] font-semibold text-ink-2">
            {revealed ? "Your marks against the checker" : "The AI rewrite. Click every line that claims more than the original."}
          </span>
          {loading && (
            <p className="inline-flex items-center gap-2 text-[14px] text-ink-3">
              <Loader2 className="size-4 animate-spin" /> Preparing the round…
            </p>
          )}
          {error && <p role="alert" className="text-[14px] text-eye">{error}</p>}
          {lines && (
            <ol className="spot-lines">
              {lines.map((l, i) => {
                const v = verdict(marks.has(i), l.flagged);
                return (
                  <li key={i}>
                    <button type="button" aria-pressed={marks.has(i)} disabled={revealed}
                      className={`spot-line ${marks.has(i) ? "is-marked" : ""} ${revealed ? `v-${v}` : ""}`}
                      onClick={(e) => toggle(i, e.currentTarget)}>
                      <span className="relative z-[1]">{l.text}</span>
                      <svg className="spot-ring" viewBox="0 0 100 40" preserveAspectRatio="none" aria-hidden>
                        <path d={RING} vectorEffect="non-scaling-stroke" pathLength={1} />
                      </svg>
                    </button>
                    {revealed && v !== "pass" && (
                      <div className={`spot-verdict v-${v}`}>
                        <b>{VERDICT_TEXT[v]}</b>
                        {l.flagged && l.units.flatMap((u) => u.claims).slice(0, 4).map((cl, ci) => (
                          <span key={ci} className="spot-claim">
                            {cl.type === "content" ? CLAIM_LABEL.content : `${CLAIM_LABEL[cl.type]}: ${cl.text}`}
                          </span>
                        ))}
                      </div>
                    )}
                  </li>
                );
              })}
            </ol>
          )}
        </div>
      </div>

      {lines && (
        <div className="spot-bar">
          {!revealed ? (
            <>
              <span className="text-[14px] text-ink-2 tabular-nums">
                {marks.size} {marks.size === 1 ? "line" : "lines"} marked of {lines.length}
              </span>
              <button type="button" className="btn-dark h-11 px-5 text-[15px]" onClick={check}>Check my marks</button>
            </>
          ) : (
            <>
              <svg viewBox="0 0 120 120" className="spot-score" aria-hidden>
                <circle cx="60" cy="60" r="52" />
                <text x="60" y="68" textAnchor="middle">{score}</text>
              </svg>
              <p className="m-0 max-w-[56ch] text-[15px] text-ink-2">
                {flaggedCount === 0
                  ? falses === 0
                    ? "Nothing in this rewrite was invented, and you left it alone. This is the honest control case."
                    : `Nothing in this rewrite was invented: it is the honest control case. You marked ${falses} supported ${falses === 1 ? "line" : "lines"}.`
                  : `You caught ${hits} of the ${flaggedCount} lines the checker flags, with ${falses} false ${falses === 1 ? "alarm" : "alarms"}. The checker itself catches about 73% of invented claims, so you may have spotted some it missed.`}
              </p>
              <div className="ml-auto flex flex-wrap gap-2">
                <button type="button" className="tool-btn" onClick={() => { setMarks(new Set()); setRevealed(false); }}>
                  <RotateCcw className="size-3.5" /> Try again
                </button>
                {idx < cases.length - 1 ? (
                  <button type="button" className="btn-dark h-10 gap-2 px-4 text-[14px]" onClick={() => pick(idx + 1)}>
                    Next round <ArrowRight className="size-4" />
                  </button>
                ) : (
                  <Link href={`/audit?case=${c?.id}`} className="btn-dark h-10 px-4 text-[14px]">Open this case in the audit</Link>
                )}
              </div>
            </>
          )}
        </div>
      )}
    </div>
  );
}
