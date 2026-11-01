"use client";

import { useRef } from "react";
import { gsap, MOTION, SplitText, useGSAP } from "@/lib/gsap";

// Title block shared by the inner pages: the heading rises line by line out of a mask.
export function PageHead({ title, children }: { title: string; children?: React.ReactNode }) {
  const root = useRef<HTMLDivElement>(null);
  useGSAP(
    () => {
      const mm = gsap.matchMedia();
      mm.add(MOTION, () => {
        const split = SplitText.create("h1", { type: "lines", mask: "lines" });
        gsap.from(split.lines, { yPercent: 105, duration: 0.8, ease: "power3.out", stagger: 0.08, delay: 0.15 });
        return () => split.revert();
      });
    },
    { scope: root },
  );
  return (
    <div ref={root} className="page-head">
      <h1 className="page-title">{title}</h1>
      {children && <div className="lede">{children}</div>}
    </div>
  );
}
