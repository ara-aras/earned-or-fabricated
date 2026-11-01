"use client";

import { useRef } from "react";
import { gsap, MOTION, useGSAP } from "@/lib/gsap";

// Half-ring gauge for the fabricated share. The arc is a real SVG path that DrawSVG
// draws to the share; above 100% the overflow wraps as a second, darker stroke.

const ARC = "M 20 110 A 90 90 0 0 1 200 110";

export function ShareGauge({ share }: { share: number | null }) {
  const root = useRef<SVGSVGElement>(null);
  const pct = share === null ? null : Math.round(share * 100);
  const main = pct === null ? 0 : Math.max(0, Math.min(100, pct));
  const over = pct === null ? 0 : Math.max(0, Math.min(100, pct - 100));
  const tone = pct === null ? "var(--ink-3)" : pct >= 50 ? "var(--eye)" : pct > 0 ? "var(--amber)" : "var(--moss)";

  useGSAP(
    () => {
      const num = root.current!.querySelector("text.big")!;
      const set = (v: number) => (num.textContent = pct === null ? "–" : `${Math.round(v)}%`);
      const mm = gsap.matchMedia();
      mm.add(MOTION, () => {
        const o = { v: 0 };
        gsap.timeline({ defaults: { ease: "power3.out" } })
          .fromTo(".g-main", { drawSVG: "0%" }, { drawSVG: `${main}%`, duration: 1.2 })
          .fromTo(".g-over", { drawSVG: "0%" }, { drawSVG: `${over}%`, duration: over ? 0.6 : 0.01 })
          .to(o, { v: pct ?? 0, duration: 1.6, onUpdate: () => set(o.v) }, 0);
      });
      mm.add("(prefers-reduced-motion: reduce)", () => {
        gsap.set(".g-main", { drawSVG: `${main}%` });
        gsap.set(".g-over", { drawSVG: `${over}%` });
        set(pct ?? 0);
      });
    },
    { scope: root, dependencies: [share], revertOnUpdate: true },
  );

  return (
    <svg ref={root} viewBox="0 0 220 130" className="gauge" role="img"
      aria-label={pct === null ? "No gain to split" : `${pct}% of the gain is fabricated`}>
      <path d={ARC} className="g-track" />
      <path d={ARC} className="g-main" style={{ stroke: tone }} />
      <path d={ARC} className="g-over" />
      <text x="110" y="98" textAnchor="middle" className="big" style={{ fill: tone }}>{pct === null ? "–" : `${pct}%`}</text>
      <text x="110" y="122" textAnchor="middle" className="small">of the gain is fabricated</text>
    </svg>
  );
}
