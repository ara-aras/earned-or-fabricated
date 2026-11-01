"use client";

import Link from "next/link";
import { useRef } from "react";
import { RotateCcw } from "lucide-react";
import { gsap, MOTION, SplitText, useGSAP } from "@/lib/gsap";

// The home page's one orchestrated moment: a proof-reader's red pen marks up an AI rewrite.
// Rings and strikes are SVG paths stretched over the text they mark (preserveAspectRatio="none"
// with non-scaling strokes), so they hug the words at any width and DrawSVG can draw them.

const RING = "M10 23 C 6 9, 88 3, 95 17 C 100 31, 35 39, 11 31 C 2 27, 5 15, 24 9";
const STRIKE = "M1 23 C 28 20, 66 25, 99 19";

function Ring({ children, note }: { children: React.ReactNode; note: string }) {
  return (
    <span className="mark-wrap">
      <span className="mark-text">{children}</span>
      <svg className="mark-ring" viewBox="0 0 100 40" preserveAspectRatio="none" aria-hidden>
        <path d={RING} vectorEffect="non-scaling-stroke" pathLength={1} />
      </svg>
      <span className="mark-note">{note}</span>
    </span>
  );
}

function Strike({ from, to }: { from: string; to: string }) {
  return (
    <>
      <span className="mark-wrap">
        <span className="mark-text text-ink-3">{from}</span>
        <svg className="mark-strike" viewBox="0 0 100 40" preserveAspectRatio="none" aria-hidden>
          <path d={STRIKE} vectorEffect="non-scaling-stroke" pathLength={1} />
        </svg>
      </span>{" "}
      <Ring note="bigger role than stated">{to}</Ring>
    </>
  );
}

export function HomeHero() {
  const root = useRef<HTMLElement>(null);
  const tl = useRef<gsap.core.Timeline | null>(null);

  useGSAP(
    () => {
      const mm = gsap.matchMedia();
      mm.add(MOTION, () => {
        const split = SplitText.create(".home-title", { type: "lines", mask: "lines", linesClass: "home-line" });
        const score = { v: 28 };
        const out = root.current!.querySelector<HTMLElement>(".proof-score")!;
        out.textContent = "28"; // the server renders the final frame (31) for reduced motion
        tl.current = gsap
          .timeline({ defaults: { ease: "power3.out" } })
          .from(split.lines, { yPercent: 105, duration: 0.9, stagger: 0.09 })
          .from(".home-copy .reveal", { y: 12, opacity: 0, duration: 0.6, stagger: 0.08 }, "-=0.5")
          .from(".proof-sheet", { y: 30, rotate: -1.5, opacity: 0, duration: 0.9 }, 0.2)
          .from(".proof-line", { opacity: 0, x: -8, duration: 0.4, stagger: 0.07 }, 0.55)
          .add("pen", 1.4)
          .fromTo(".mark-strike path", { strokeDashoffset: 1 }, { strokeDashoffset: 0, duration: 0.35, ease: "power1.inOut" }, "pen")
          .fromTo(".mark-ring path", { strokeDashoffset: 1 }, { strokeDashoffset: 0, duration: 0.55, ease: "power1.inOut", stagger: 0.42 }, "pen+=0.2")
          .from(".mark-note", { opacity: 0, y: 4, duration: 0.3, stagger: 0.42 }, "pen+=0.55")
          .set(".proof-gain", { opacity: 1 }, 0)
          .from(".proof-gain", { scaleX: 0, transformOrigin: "0 50%", duration: 0.9, ease: "power2.inOut" }, "pen")
          .to(score, { v: 37, duration: 0.9, ease: "power2.inOut", onUpdate: () => (out.textContent = String(Math.round(score.v))) }, "pen")
          .add("split", ">+0.5")
          .to(".proof-gain", { opacity: 0, duration: 0.2 }, "split")
          .from(".proof-earned, .proof-fab", { opacity: 0, duration: 0.3 }, "split")
          .to(".proof-fab", { y: 7, rotate: 2, duration: 0.5, ease: "back.out(3)" }, "split+=0.25")
          .to(score, { v: 31, duration: 0.6, onUpdate: () => (out.textContent = String(Math.round(score.v))) }, "split+=0.25")
          .from(".proof-caption", { opacity: 0, y: 6, duration: 0.4 }, "split+=0.5")
          .from(".proof-stamp", { scale: 1.8, rotate: -24, opacity: 0, duration: 0.5, ease: "back.out(2.2)" }, "split+=0.7")
          .from(".proof-replay", { opacity: 0, duration: 0.3 });
        return () => split.revert();
      });
    },
    { scope: root },
  );

  return (
    <section ref={root} className="home-hero">
      <div className="home-copy">
        <h1 className="hero-title home-title">Your AI rewrite scores higher. How much of that is you?</h1>
        <p className="lede reveal">
          AI tools raise resume screening scores, partly by adding skills, numbers and seniority you never claimed. This
          audit checks every line against your original and splits the new score into what you earned and what was
          invented for you.
        </p>
        <div className="reveal flex flex-wrap items-center gap-3 pt-2">
          <Link href="/audit" className="btn-dark h-12 px-6 text-[15px]">Audit your rewrite</Link>
          <Link href="/spot" className="btn-line h-12 px-5 text-[15px]">Play spot the fabrication</Link>
        </div>
        <p className="reveal text-[13px] text-ink-3">Measured on 380 real resumes and three screeners. Runs on your machine.</p>
      </div>

      <figure className="proof" aria-label="Animated example: a red pen marks the invented claims in an AI rewrite, and the score gain splits into earned and fabricated parts">
        <div className="proof-sheet">
          <div className="proof-head">
            <span className="font-display text-[20px] font-semibold tracking-[-0.01em] text-ink">Priya Nair</span>
            <span className="text-[13px] text-ink-3">AI rewrite for: Data Analyst</span>
          </div>
          <ul className="proof-lines">
            <li className="proof-line">
              <Strike from="Assisted with" to="Led" /> the redesign of four client websites,{" "}
              <Ring note="number you never wrote">lifting conversion by 35%</Ring>
            </li>
            <li className="proof-line">
              Tracked monthly inventory in Excel, <Ring note="skills not in your resume">SQL and Tableau</Ring>
            </li>
            <li className="proof-line">Answered customer questions by e-mail and phone</li>
            <li className="proof-line">B.Sc. Computer Science, 2023</li>
            <li className="proof-line">
              <Ring note="certificate not listed">AWS Certified Cloud Practitioner</Ring>
            </li>
          </ul>

          <div className="proof-meter">
            <div className="flex items-baseline justify-between text-[13px] text-ink-2">
              <span>ATS score</span>
              <span className="proof-score font-display text-[28px] leading-none font-semibold tabular-nums text-ink">31</span>
            </div>
            <svg viewBox="0 0 500 22" className="proof-bar" aria-hidden>
              <rect className="proof-track" x="0" y="3" width="500" height="16" rx="8" />
              <rect className="proof-orig" x="0" y="3" width="280" height="16" rx="8" />
              <rect className="proof-gain" x="276" y="3" width="94" height="16" rx="3" />
              <rect className="proof-earned" x="276" y="3" width="34" height="16" rx="3" />
              <rect className="proof-fab" x="312" y="3" width="58" height="16" rx="3" />
            </svg>
            <p className="proof-caption">+9 points: 3 earned, 6 bought by claims the original never makes.</p>
          </div>

          <svg className="proof-stamp" viewBox="0 0 120 120" aria-hidden>
            <circle cx="60" cy="60" r="54" />
            <circle cx="60" cy="60" r="46" />
            <text x="60" y="58" textAnchor="middle" className="stamp-big">67%</text>
            <text x="60" y="78" textAnchor="middle" className="stamp-small">not earned</text>
          </svg>
          <button type="button" onClick={() => tl.current?.restart()} className="proof-replay" aria-label="Replay the animation">
            <RotateCcw className="size-3.5" /> Replay
          </button>
        </div>
      </figure>
    </section>
  );
}
