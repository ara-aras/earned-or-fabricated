"use client";

import { useRef } from "react";
import { gsap, MOTION, ScrollTrigger, useGSAP } from "@/lib/gsap";

// Remounts on every navigation: a red-pen sweep crosses the top, the page settles in under it.
export default function Template({ children }: { children: React.ReactNode }) {
  const root = useRef<HTMLDivElement>(null);
  useGSAP(
    () => {
      const mm = gsap.matchMedia();
      mm.add(MOTION, () => {
        gsap.timeline()
          .fromTo(".route-sweep", { scaleX: 0, transformOrigin: "0 50%" }, { scaleX: 1, duration: 0.45, ease: "power3.inOut" })
          .to(".route-sweep", { opacity: 0, duration: 0.25 })
          // a transformed ancestor breaks pinning, so clear it and re-measure the scroll triggers after
          .from(".route-page", {
            y: 14, opacity: 0, duration: 0.5, ease: "power2.out", clearProps: "all",
            onComplete: () => ScrollTrigger.refresh(),
          }, 0.12);
      });
    },
    { scope: root },
  );
  return (
    <div ref={root}>
      <div className="route-sweep" aria-hidden />
      <div className="route-page">{children}</div>
    </div>
  );
}
