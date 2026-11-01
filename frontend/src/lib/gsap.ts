"use client";

// One place to register GSAP plugins. Import gsap from here, never from "gsap" directly,
// so every component gets ScrollTrigger, SplitText and DrawSVG already registered.
import gsap from "gsap";
import { DrawSVGPlugin } from "gsap/DrawSVGPlugin";
import { ScrollTrigger } from "gsap/ScrollTrigger";
import { SplitText } from "gsap/SplitText";
import { useGSAP } from "@gsap/react";

if (typeof window !== "undefined") {
  gsap.registerPlugin(useGSAP, ScrollTrigger, SplitText, DrawSVGPlugin);
}

export const REDUCED = "(prefers-reduced-motion: reduce)";
export const MOTION = "(prefers-reduced-motion: no-preference)";

export { gsap, ScrollTrigger, SplitText, DrawSVGPlugin, useGSAP };
