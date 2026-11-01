"use client";

import Link from "next/link";
import { useRef } from "react";
import { gsap, MOTION, useGSAP } from "@/lib/gsap";

// ---------------------------------------------------------------- pinned scroll story
// Scrolling through this section plays the research question in three beats:
// the rewrite gains points, the unsupported claims are removed, and what is left is earned.

const STAGES = [
  { n: "+33", title: "An AI rewrite adds 33 points", body: "Case 05 from our demo set: a data analyst's resume, tailored by an AI tool to a job listing. The keyword screener likes it a lot more." },
  { n: "−34.6", title: "Remove what the original never says", body: "New tools, a project they “led”, a 30% time saving and a Google certificate. Each is reverted to the closest line the candidate actually wrote." },
  { n: "104%", title: "Nothing of the gain was earned", body: "Without its inventions the rewrite scores 52.1, below the original 53.3. Over 100% means the rewrite also dropped real material." },
];
// bar scale: 40..90 mapped to 0..1000
const X = (v: number) => ((v - 40) / 50) * 1000;

export function SplitStory() {
  const root = useRef<HTMLElement>(null);
  useGSAP(
    () => {
      const mm = gsap.matchMedia();
      mm.add(MOTION, () => {
        const num = root.current!.querySelector<HTMLElement>(".story-score")!;
        const s = { v: 53.3 };
        const show = () => (num.textContent = s.v.toFixed(1));
        show(); // the server renders the end state (52.1) for reduced motion
        const tl = gsap.timeline({
          defaults: { ease: "none" },
          scrollTrigger: { trigger: ".story-pin", start: "top top", end: "+=220%", scrub: 0.6, pin: true },
        });
        gsap.set(".story-stage:not(:first-child)", { autoAlpha: 0, y: 24 });
        tl.fromTo(".story-gain", { attr: { width: 0 } }, { attr: { width: X(86.7) - X(53.3) }, duration: 1 })
          .to(s, { v: 86.7, duration: 1, onUpdate: show }, "<")
          .to(".story-stage:nth-child(1)", { autoAlpha: 0, y: -24, duration: 0.3 }, "+=0.3")
          .to(".story-stage:nth-child(2)", { autoAlpha: 1, y: 0, duration: 0.3 })
          .to(".story-claim", { opacity: 1, stagger: 0.12, duration: 0.15 }, "<")
          .to(".story-claim", { y: 46, rotate: (i) => [-6, 4, -3, 7][i % 4], opacity: 0, stagger: 0.12, duration: 0.5 }, "+=0.2")
          .to(".story-gain", { fill: "var(--eye)", duration: 0.2 }, "<")
          .to(".story-gain", { attr: { width: 0, x: X(53.3) }, opacity: 0.25, duration: 0.8 }, "<+0.2")
          .to(s, { v: 52.1, duration: 0.8, onUpdate: show }, "<")
          .to(".story-dip", { attr: { width: X(53.3) - X(52.1) }, opacity: 1, duration: 0.4 })
          .to(".story-stage:nth-child(2)", { autoAlpha: 0, y: -24, duration: 0.3 }, "+=0.2")
          .to(".story-stage:nth-child(3)", { autoAlpha: 1, y: 0, duration: 0.3 })
          .to({}, { duration: 0.4 });
      });
    },
    { scope: root },
  );

  return (
    <section ref={root} className="story" aria-label="How a rewrite's gain splits, told in three steps">
      <div className="story-pin">
        <div className="story-inner">
          <div className="story-stages">
            {STAGES.map((st) => (
              <div key={st.title} className="story-stage">
                <span className="story-n">{st.n}</span>
                <h2 className="h2">{st.title}</h2>
                <p className="lede">{st.body}</p>
              </div>
            ))}
          </div>
          <div className="story-viz">
            <div className="flex items-baseline justify-between">
              <span className="text-[14px] text-ink-2">Keyword ATS score</span>
              <span className="story-score font-display text-[44px] leading-none font-semibold tabular-nums text-ink">52.1</span>
            </div>
            <div className="story-claims" aria-hidden>
              {["+ Power BI, Python, Tableau", "+ “Led” the KPI project", "+ 30% faster reporting", "+ Google certificate"].map((c) => (
                <span key={c} className="story-claim">{c}</span>
              ))}
            </div>
            <svg viewBox="0 0 1000 90" className="story-bar" aria-hidden>
              <rect x="0" y="24" width="1000" height="42" rx="10" className="story-track" />
              <rect x="0" y="24" width={X(53.3)} height="42" rx="10" className="story-orig" />
              <rect x={X(53.3)} y="24" width="0" height="42" rx="4" className="story-gain" />
              <rect x={X(52.1)} y="24" width={X(53.3) - X(52.1)} height="42" className="story-dip" />
              <line x1={X(53.3)} x2={X(53.3)} y1="12" y2="78" className="story-tick" />
              <text x={X(53.3)} y="8" textAnchor="middle" className="story-label">original 53.3</text>
              {[40, 50, 60, 70, 80, 90].map((v) => (
                <text key={v} x={Math.min(985, Math.max(15, X(v)))} y="88" textAnchor="middle" className="story-axis">{v}</text>
              ))}
            </svg>
            <p className="text-[13px] text-ink-3">Scroll to play. Real numbers from demo case 05.</p>
          </div>
        </div>
      </div>
    </section>
  );
}

// ---------------------------------------------------------------- three screeners
const SCREENERS = [
  { share: 146, name: "Keyword ATS", note: "rule-based, like most tracking systems", gain: 9.4, earned: -4.3 },
  { share: 45, name: "Qwen 3.5 4B", note: "the same model that wrote the rewrite", gain: 42.1, earned: 23.3 },
  { share: 33, name: "Gemma 3 4B", note: "an LLM screener from another family", gain: 37.0, earned: 24.7 },
];

export function ScreenerStats() {
  const root = useRef<HTMLElement>(null);
  useGSAP(
    () => {
      const mm = gsap.matchMedia();
      mm.add(MOTION, () => {
        gsap.utils.toArray<HTMLElement>(".stat-n").forEach((el) => {
          const to = Number(el.dataset.to);
          const o = { v: 0 };
          gsap.to(o, {
            v: to, duration: 1.4, ease: "power2.out",
            onUpdate: () => (el.textContent = `${Math.round(o.v)}%`),
            scrollTrigger: { trigger: el, start: "top 85%", once: true },
          });
        });
        gsap.from(".stat-bar rect.fab", {
          attr: { width: 0 }, duration: 1, ease: "power2.out", stagger: 0.15,
          scrollTrigger: { trigger: ".stats", start: "top 80%", once: true },
        });
      });
    },
    { scope: root },
  );
  const lo = -8;
  const hi = 46;
  const x = (v: number) => ((v - lo) / (hi - lo)) * 300;
  return (
    <section ref={root} className="section">
      <div className="section-head">
        <h2 className="h2">Three screeners, one pattern</h2>
        <p className="lede">380 resume and job pairs, each rewritten by a local AI and scored three ways. The share is how much of the gain the original resume does not support.</p>
      </div>
      <div className="stats">
        {SCREENERS.map((s) => (
          <div key={s.name} className="stat">
            <span className="stat-n font-display" data-to={s.share}>{s.share}%</span>
            <span className="grid gap-0.5">
              <span className="font-semibold text-ink">{s.name}</span>
              <span className="text-[13px] text-ink-3">{s.note}</span>
            </span>
            <svg viewBox="0 0 300 18" className="stat-bar" role="img"
              aria-label={`Gain ${s.gain} points, earned ${s.earned}`}>
              <line x1={x(0)} x2={x(0)} y1="0" y2="18" className="zero" />
              <rect x={x(Math.min(0, s.earned))} y="4" height="10" width={Math.abs(x(s.earned) - x(0))} className="earned" />
              <rect x={x(s.earned)} y="4" height="10" width={x(s.gain) - x(s.earned)} className="fab" />
            </svg>
          </div>
        ))}
      </div>
      <Link href="/findings" className="btn-line mt-6 h-11 w-fit px-5 text-[14px]">Read the full findings</Link>
    </section>
  );
}

// ---------------------------------------------------------------- where to go next
const PAGES = [
  {
    href: "/audit", title: "Audit a rewrite", body: "Paste your resume and a job. Bring a ChatGPT rewrite or let a local model write one. Every unsupported line gets marked.",
    glyph: <><rect x="6" y="5" width="22" height="30" rx="3" /><path d="M11 13h12M11 18h9M11 23h11" /><circle cx="30" cy="28" r="7" /><path d="M35 33l5 5" /></>,
  },
  {
    href: "/spot", title: "Spot the fabrication", body: "A game. Read a real AI rewrite, mark the lines you think were invented, then see how you did against the checker.",
    glyph: <><circle cx="22" cy="22" r="15" /><circle cx="22" cy="22" r="8" /><path d="M22 2v8M22 34v8M2 22h8M34 22h8" /></>,
  },
  {
    href: "/findings", title: "Findings", body: "Which claims pay the most, why a model grading its own writing is kinder to it, and why length is not the explanation.",
    glyph: <><path d="M5 38h34" /><path d="M10 38V22M19 38V12M28 38V26M37 38V8" /></>,
  },
  {
    href: "/method", title: "Method", body: "The formula, the four steps of the audit, a playground for the numbers, and how often the checker is right.",
    glyph: <><circle cx="8" cy="22" r="4" /><circle cx="22" cy="10" r="4" /><circle cx="22" cy="34" r="4" /><circle cx="36" cy="22" r="4" /><path d="M11 19l8-6M11 25l8 6M25 12l8 7M25 32l8-7" /></>,
  },
];

export function ExploreList() {
  return (
    <section className="section">
      <div className="section-head">
        <h2 className="h2">Where to next</h2>
      </div>
      <ul className="explore">
        {PAGES.map((p) => (
          <li key={p.href}>
            <Link href={p.href} className="explore-row">
              <svg viewBox="0 0 44 44" className="explore-glyph" aria-hidden>{p.glyph}</svg>
              <span className="grid gap-1">
                <span className="font-display text-[26px] leading-tight font-semibold tracking-[-0.015em] text-ink">{p.title}</span>
                <span className="max-w-[62ch] text-[15px] text-ink-2">{p.body}</span>
              </span>
            </Link>
          </li>
        ))}
      </ul>
    </section>
  );
}
