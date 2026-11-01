"use client";

import { useRef, useState } from "react";
import { gsap, MOTION, useGSAP } from "@/lib/gsap";

// ---------------------------------------------------------------- the four steps
const STEPS = [
  { title: "Rewrite", body: "A local model tailors your resume to the job, prompted the way a job seeker would ask. Or paste a rewrite you already have." },
  { title: "Check", body: "Every skill, number, job title, degree and sentence in the rewrite is looked up in your original. Each flag shows the closest line you actually wrote." },
  { title: "Strip", body: "Flagged lines are reverted to your own wording or cut. Nothing new is added, so what remains is the part you earned." },
  { title: "Re-score", body: "Both versions go through the same screener. The gap between them is the part of the gain your resume doesn't support." },
];

// One glyph per step, drawn on a 48x48 grid.
const GLYPHS = [
  <g key="r"><rect x="10" y="8" width="24" height="32" rx="3" /><path d="M15 16h14M15 22h10M15 28h12" /><path d="M30 36l10-16 4 3-10 16-5 1z" /></g>,
  <g key="c"><rect x="8" y="8" width="24" height="32" rx="3" /><path d="M13 16h14M13 22h10" /><circle cx="30" cy="28" r="8" /><path d="M36 34l6 6" /></g>,
  <g key="s"><rect x="10" y="8" width="28" height="32" rx="3" /><path d="M15 16h18M15 24h18M15 32h12" /><path d="M13 24c8-2 14 2 22 0" className="red" /></g>,
  <g key="x"><path d="M8 40h32" /><path d="M14 40V26M24 40V14M34 40V22" /><path d="M10 12l8 6 8-4 12 6" className="red" /></g>,
];

export function Pipeline() {
  const root = useRef<HTMLDivElement>(null);
  useGSAP(
    () => {
      const mm = gsap.matchMedia();
      mm.add(MOTION, () => {
        const tl = gsap.timeline({
          scrollTrigger: { trigger: root.current, start: "top 70%", end: "bottom 60%", scrub: 0.5 },
        });
        tl.fromTo(".pipe-rail", { scaleY: 0 }, { scaleY: 1, transformOrigin: "50% 0%", ease: "none", duration: 4 }, 0);
        STEPS.forEach((_, i) => {
          tl.fromTo(`.pipe-step:nth-child(${i + 1}) .pipe-glyph > g > *`, { drawSVG: "0%" }, { drawSVG: "100%", duration: 0.8 }, i)
            .fromTo(`.pipe-step:nth-child(${i + 1})`, { opacity: 0.25 }, { opacity: 1, duration: 0.5 }, i);
        });
      });
    },
    { scope: root },
  );
  return (
    <div ref={root} className="pipe">
      <span className="pipe-track" aria-hidden><span className="pipe-rail" /></span>
      <ol className="pipe-steps">
        {STEPS.map((s, i) => (
          <li key={s.title} className="pipe-step">
            <svg viewBox="0 0 48 48" className="pipe-glyph" aria-hidden>{GLYPHS[i]}</svg>
            <div className="grid gap-1.5">
              <span className="text-[13px] text-ink-3">Step {i + 1}</span>
              <span className="font-display text-[26px] leading-tight font-semibold text-ink">{s.title}</span>
              <p className="m-0 max-w-[58ch] text-[15px] leading-relaxed text-ink-2">{s.body}</p>
            </div>
          </li>
        ))}
      </ol>
    </div>
  );
}

// ---------------------------------------------------------------- formula playground
function Slider({ label, value, set, tone }: { label: string; value: number; set: (v: number) => void; tone: string }) {
  return (
    <label className="grid gap-1.5">
      <span className="flex items-baseline justify-between text-[14px]">
        <span className="text-ink-2">{label}</span>
        <b className="font-display text-[22px] tabular-nums" style={{ color: tone }}>{value}</b>
      </span>
      <input type="range" min={0} max={100} value={value} onChange={(e) => set(Number(e.target.value))}
        className="range" style={{ accentColor: tone }} />
    </label>
  );
}

export function FormulaPlayground() {
  const [orig, setOrig] = useState(53);
  const [llm, setLlm] = useState(87);
  const [stripped, setStripped] = useState(52);
  const gain = llm - orig;
  const share = gain >= 2 ? (llm - stripped) / gain : null;
  const pct = share === null ? null : Math.round(share * 100);
  const say =
    pct === null
      ? gain < 0
        ? "The rewrite lowered the score, so there is nothing to split."
        : "The gain is under 2 points: too small to split reliably, so the audit reports no share."
      : pct > 100
        ? "Over 100%: without its inventions the rewrite scores below the original. It dropped real material."
        : pct <= 0
          ? "Every point of the gain is backed by the original. An honest rewrite."
          : pct >= 50
            ? "Most of the gain is bought by claims the original doesn't make."
            : "Most of the gain is earned, but part of it is bought.";
  const X = (v: number) => (v / 100) * 600;
  const earnedEnd = Math.max(orig, Math.min(stripped, llm));
  return (
    <div className="play">
      <div className="grid gap-5">
        <Slider label="Original score" value={orig} set={setOrig} tone="var(--ink)" />
        <Slider label="AI rewrite score" value={llm} set={setLlm} tone="var(--amber)" />
        <Slider label="Rewrite minus unsupported claims" value={stripped} set={setStripped} tone="var(--moss)" />
      </div>
      <div className="grid content-start gap-4">
        <p className="formula">
          fabricated share = (<span style={{ color: "var(--amber)" }}>{llm}</span> − <span style={{ color: "var(--moss)" }}>{stripped}</span>) ÷ (<span style={{ color: "var(--amber)" }}>{llm}</span> − <span>{orig}</span>)
          {" "}= <b className={pct === null ? "text-ink-3" : pct >= 50 ? "text-eye" : pct > 0 ? "text-amber" : "text-moss"}>{pct === null ? "n/a" : `${pct}%`}</b>
        </p>
        <svg viewBox="0 0 600 40" className="w-full" role="img" aria-label="The three scores on one bar">
          <rect x="0" y="10" width="600" height="20" rx="6" fill="var(--agar)" />
          <rect x="0" y="10" width={X(orig)} height="20" rx="6" fill="var(--ink)" />
          {earnedEnd > orig && <rect x={X(orig)} y="10" width={X(earnedEnd) - X(orig)} height="20" fill="var(--moss)" />}
          {llm > earnedEnd && <rect x={X(earnedEnd)} y="10" width={X(llm) - X(earnedEnd)} height="20" fill="var(--eye)" />}
          {stripped < orig && <rect x={X(stripped)} y="10" width={X(orig) - X(stripped)} height="20" fill="var(--eye)" opacity="0.4" />}
        </svg>
        <p className="m-0 text-[15px] text-ink-2">{say}</p>
      </div>
    </div>
  );
}

// ---------------------------------------------------------------- checker accuracy
function Ring({ value, label, body }: { value: number; label: string; body: string }) {
  const C = 2 * Math.PI * 44;
  return (
    <div className="acc">
      <svg viewBox="0 0 110 110" className="acc-ring" role="img" aria-label={`${label}: ${value}%`}>
        <circle cx="55" cy="55" r="44" className="t" />
        <circle cx="55" cy="55" r="44" className="v" style={{ strokeDasharray: `${(value / 100) * C} ${C}` }} transform="rotate(-90 55 55)" />
        <text x="55" y="62" textAnchor="middle">{value}%</text>
      </svg>
      <div className="grid gap-1">
        <span className="font-semibold text-ink">{label}</span>
        <p className="m-0 max-w-[44ch] text-[14px] text-ink-2">{body}</p>
      </div>
    </div>
  );
}

export function Accuracy() {
  const root = useRef<HTMLDivElement>(null);
  useGSAP(
    () => {
      const mm = gsap.matchMedia();
      mm.add(MOTION, () => {
        gsap.from(".acc-ring .v", {
          drawSVG: "0%", duration: 1.3, ease: "power2.out", stagger: 0.2,
          scrollTrigger: { trigger: root.current, start: "top 80%", once: true },
        });
      });
    },
    { scope: root },
  );
  return (
    <div ref={root} className="grid gap-6 md:grid-cols-2">
      <Ring value={73} label="Catches 73% of invented claims"
        body="Of the claims a person marked unsupported, the checker flagged 73%. The other 27% slip through unmarked." />
      <Ring value={80} label="80% of its flags are right"
        body="One flag in five points at a claim the person judged to be supported by the original." />
    </div>
  );
}
