"use client";

import { useRef } from "react";
import { gsap, MOTION, useGSAP } from "@/lib/gsap";

// Results of the main run: 380 resume–job pairs, Qwen 3.5 4B rewriter (report Tables 6.4 and 6.8).
const SCREENERS = [
  { name: "Keyword ATS", note: "rule-based, like most applicant tracking systems", gain: 9.4, earned: -4.3, share: 146 },
  { name: "Gemma 3 4B", note: "an LLM screener from another model family", gain: 37.01, earned: 24.71, share: 33 },
  { name: "Qwen 3.5 4B", note: "the same model that wrote the rewrite", gain: 42.09, earned: 23.25, share: 45 },
];

const LO = -8;
const HI = 46;
const W = 760;
const L = 0;
const x = (v: number) => L + ((v - LO) / (HI - LO)) * (W - L);

export function ScreenerChart() {
  const root = useRef<HTMLDivElement>(null);
  useGSAP(
    () => {
      const mm = gsap.matchMedia();
      mm.add(MOTION, () => {
        const tl = gsap.timeline({ scrollTrigger: { trigger: root.current, start: "top 75%", once: true } });
        tl.from(".sc-earned", { attr: { width: 0, x: x(0) }, duration: 0.8, ease: "power2.out", stagger: 0.15 })
          .from(".sc-fab", { attr: { width: 0 }, duration: 0.9, ease: "power2.out", stagger: 0.15 }, 0.4)
          .from(".sc-share", { opacity: 0, x: -10, duration: 0.4, stagger: 0.15 }, 0.9);
      });
    },
    { scope: root },
  );
  return (
    <div ref={root} className="sc">
      {SCREENERS.map((s) => {
        const a = Math.min(0, s.earned);
        return (
          <div key={s.name} className="sc-row">
            <div className="grid gap-0.5">
              <span className="font-semibold text-ink">{s.name}</span>
              <span className="text-[13px] text-ink-3">{s.note}</span>
            </div>
            <svg viewBox={`0 0 ${W} 44`} className="sc-svg" role="img"
              aria-label={`${s.name}: gain ${s.gain.toFixed(1)} points, earned ${s.earned}, ${s.share}% fabricated`}>
              {[0, 10, 20, 30, 40].map((v) => <line key={v} x1={x(v)} x2={x(v)} y1="0" y2="44" className="sc-grid" />)}
              <rect className="sc-earned" x={x(a)} y="8" height="28" width={x(Math.max(0, s.earned)) - x(a)}
                style={s.earned < 0 ? { fill: "var(--moss)", opacity: 0.35 } : undefined} />
              <rect className="sc-fab" x={x(s.earned)} y="8" height="28" width={x(s.gain) - x(s.earned)} />
              <line x1={x(0)} x2={x(0)} y1="0" y2="44" className="sc-zero" />
            </svg>
            <div className="sc-share grid">
              <span className="font-display text-[30px] leading-none font-semibold tabular-nums text-eye">{s.share}%</span>
              <span className="text-[13px] text-ink-3">of a {s.gain.toFixed(1)}-point gain</span>
            </div>
          </div>
        );
      })}
      <div className="sc-row sc-axis" aria-hidden>
        <span />
        <svg viewBox={`0 0 ${W} 18`} className="sc-svg">
          {[0, 10, 20, 30, 40].map((v) => (
            <text key={v} x={x(v)} y="13" textAnchor="middle">{v === 0 ? "original" : `+${v}`}</text>
          ))}
        </svg>
        <span />
      </div>
      <div className="flex flex-wrap gap-5 pt-2 text-[13px] text-ink-2">
        <span className="inline-flex items-center gap-2"><i className="size-3 rounded-sm bg-moss" /> earned: the original supports it</span>
        <span className="inline-flex items-center gap-2"><i className="size-3 rounded-sm bg-eye" /> fabricated: bought by unsupported claims</span>
        <span className="inline-flex items-center gap-2"><i className="size-3 rounded-sm bg-moss/35" /> below zero: the honest part scores under the original</span>
      </div>
    </div>
  );
}

const CLAIMS = [
  { name: "Skills you never listed", before: "Tracked inventory in Excel", added: ", SQL and Tableau", per: 7.1, pays: 2.3 },
  { name: "Numbers you never wrote", before: "Improved the checkout flow", added: " by 35%", per: 0.7, pays: 0.9 },
  { name: "A bigger role", swapFrom: "Assisted with", swapTo: "Led", rest: " the website redesign", per: 3.2, pays: 0.3 },
  { name: "Degrees and certificates", before: "B.Sc. Computer Science", added: "; AWS Certified", per: 0.6, pays: 0.5 },
  { name: "New content", before: "Answered customer e-mails", added: "; built a self-service help centre", per: 10.8, pays: 0.3 },
];

export function ClaimTypes() {
  const root = useRef<HTMLDivElement>(null);
  useGSAP(
    () => {
      const mm = gsap.matchMedia();
      mm.add(MOTION, () => {
        gsap.from(".ct-bar", {
          attr: { width: 0 }, duration: 0.8, ease: "power2.out", stagger: 0.06,
          scrollTrigger: { trigger: root.current, start: "top 75%", once: true },
        });
        gsap.utils.toArray<SVGPathElement>(".ct-pen").forEach((p) =>
          gsap.fromTo(p, { strokeDashoffset: 1 }, { strokeDashoffset: 0, duration: 0.6, ease: "power1.inOut", scrollTrigger: { trigger: p, start: "top 85%", once: true } }),
        );
      });
    },
    { scope: root },
  );
  const maxPer = 11;
  const maxPays = 2.5;
  return (
    <div ref={root} className="ct">
      <div className="ct-head" aria-hidden>
        <span />
        <span>Per resume</span>
        <span>ATS points each</span>
      </div>
      {CLAIMS.map((c) => (
        <div key={c.name} className="ct-row">
          <div className="grid gap-1.5">
            <span className="font-semibold text-ink">{c.name}</span>
            <span className="claim-example">
              {c.swapFrom ? (
                <>
                  <s className="text-ink-3">{c.swapFrom}</s> <mark className="pen">{c.swapTo}</mark>
                  {c.rest}
                </>
              ) : (
                <>
                  {c.before}
                  <mark className="pen">{c.added}</mark>
                </>
              )}
            </span>
            <svg viewBox="0 0 200 8" className="ct-under" preserveAspectRatio="none" aria-hidden>
              <path className="ct-pen" d="M2 5 C 50 2, 120 7, 198 4" vectorEffect="non-scaling-stroke" pathLength={1} />
            </svg>
          </div>
          <span className="ct-cell">
            <b>{c.per}</b>
            <svg viewBox="0 0 100 8" aria-hidden><rect className="ct-bar ink" x="0" y="0" height="8" rx="2" width={(c.per / maxPer) * 100} /></svg>
          </span>
          <span className="ct-cell">
            <b>{c.pays}</b>
            <svg viewBox="0 0 100 8" aria-hidden><rect className="ct-bar eye" x="0" y="0" height="8" rx="2" width={(c.pays / maxPays) * 100} /></svg>
          </span>
        </div>
      ))}
    </div>
  );
}
