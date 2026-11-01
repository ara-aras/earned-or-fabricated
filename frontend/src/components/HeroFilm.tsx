"use client";

import { useEffect, useRef, useState } from "react";

// A short looping animation of the audit, driven by one clock t (seconds). Every frame is a pure
// function of t, so reduced-motion users simply get a still frame.

const T = 14; // loop length
const REWRITE = [2.2, 5.6];
const CHECK = [6.2, 9.0];
const STRIP = [9.4, 11.0];
const STILL = 12.4; // frame shown when motion is reduced

type Seg =
  | { kind: "same"; text: string }
  | { kind: "swap"; from: string; to: string; tag: string; at: number }
  | { kind: "add"; text: string; tag: string; at: number };

const LINES: { segs: Seg[]; newLine?: number }[] = [
  {
    segs: [
      { kind: "swap", from: "Assisted with", to: "Led", tag: "Bigger role", at: 2.4 },
      { kind: "same", text: " the redesign of four client websites" },
      { kind: "add", text: ", lifting conversion by 35%", tag: "Number you never wrote", at: 3.0 },
    ],
  },
  {
    segs: [
      { kind: "same", text: "Tracked monthly inventory in Excel" },
      { kind: "add", text: ", SQL and Tableau", tag: "Skills not in your resume", at: 4.0 },
    ],
  },
  { segs: [{ kind: "same", text: "Answered customer questions by e-mail and phone" }] },
  { segs: [{ kind: "same", text: "B.Sc. Computer Science, 2023" }] },
  {
    newLine: 4.6,
    segs: [{ kind: "add", text: "AWS Certified Cloud Practitioner", tag: "Certificate not listed", at: 4.6 }],
  },
];

const ORIG = 28;
const LLM = 37;
const STRIPPED = 31;

const clamp = (v: number, a = 0, b = 1) => Math.min(b, Math.max(a, v));
const ramp = (t: number, a: number, b: number) => clamp((t - a) / (b - a));
const ease = (x: number) => 1 - Math.pow(1 - x, 3);

function typed(text: string, t: number, at: number) {
  return text.slice(0, Math.round(ramp(t, at, at + text.length * 0.035) * text.length));
}

function scoreAt(t: number) {
  if (t < REWRITE[0]) return ORIG;
  if (t < STRIP[0]) return ORIG + (LLM - ORIG) * ease(ramp(t, REWRITE[0] + 0.3, REWRITE[1]));
  return LLM - (LLM - STRIPPED) * ease(ramp(t, STRIP[0] + 0.4, STRIP[1]));
}

function Segment({ s, t, li }: { s: Seg; t: number; li: number }) {
  if (s.kind === "same") return <span>{s.text}</span>;
  // checked: turns red as the scan line passes this line; struck: removed during the strip scene
  const scanY = ramp(t, CHECK[0], CHECK[1]) * (LINES.length + 0.5);
  const checked = t >= CHECK[0] && scanY > li + 0.5;
  const struck = ramp(t, STRIP[0] + li * 0.12, STRIP[0] + 0.6 + li * 0.12);
  const shown = s.kind === "swap" ? (t >= s.at ? typed(s.to, t, s.at) : "") : typed(s.text, t, s.at);
  const flag = checked ? "film-flag" : t >= s.at ? "film-new" : "";
  return (
    <>
      {s.kind === "swap" && (t < s.at || struck > 0) && (
        <span className="film-restore" style={{ opacity: t < s.at ? 1 : struck }}>
          {s.from}
          {t >= s.at && " "}
        </span>
      )}
      {shown && (
        <span
          className={`film-mark ${flag}`}
          style={struck > 0 ? { opacity: 1 - struck * 0.55, textDecorationLine: "line-through" } : undefined}
        >
          {shown}
          {checked && struck === 0 && (
            <span className="film-tag" aria-hidden>
              {s.tag}
            </span>
          )}
        </span>
      )}
    </>
  );
}

export function HeroFilm() {
  const [t, setT] = useState(STILL);
  const [playing, setPlaying] = useState(false);
  const raf = useRef<number | null>(null);
  const last = useRef<number | null>(null);
  const root = useRef<HTMLDivElement>(null);
  const visible = useRef(true);

  // autoplay unless the visitor asked for reduced motion
  useEffect(() => {
    // deferred a frame so the server-rendered still frame hydrates first
    const start = requestAnimationFrame(() => {
      if (!window.matchMedia("(prefers-reduced-motion: reduce)").matches) {
        setT(0);
        setPlaying(true);
      }
    });
    const io = new IntersectionObserver(([e]) => (visible.current = e.isIntersecting), { threshold: 0.2 });
    if (root.current) io.observe(root.current);
    return () => {
      cancelAnimationFrame(start);
      io.disconnect();
    };
  }, []);

  useEffect(() => {
    if (!playing) return;
    const tick = (now: number) => {
      if (last.current !== null && visible.current) {
        const dt = (now - last.current) / 1000;
        setT((v) => (v + dt) % T);
      }
      last.current = now;
      raf.current = requestAnimationFrame(tick);
    };
    raf.current = requestAnimationFrame(tick);
    return () => {
      if (raf.current) cancelAnimationFrame(raf.current);
      last.current = null;
    };
  }, [playing]);

  const score = scoreAt(t);
  const split = ramp(t, STRIP[1], STRIP[1] + 0.6);
  const scanY = ramp(t, CHECK[0], CHECK[1]);
  const scanOn = t >= CHECK[0] && t <= CHECK[1] + 0.2;
  const max = 50;
  const pct = (v: number) => `${(v / max) * 100}%`;

  return (
    <figure ref={root} className="film" aria-label="Animated example of an audit">
      <div className="film-sheet">
        <div className="film-head">
          <span className="font-display text-[19px] font-semibold tracking-[-0.01em] text-ink">Priya Nair</span>
          <span className="text-[13px] text-ink-3">Applying for: Data Analyst</span>
        </div>
        <ul className="film-lines">
          {LINES.map((line, li) =>
            line.newLine !== undefined && t < line.newLine ? null : (
              <li
                key={li}
                style={
                  line.newLine !== undefined && t >= STRIP[0]
                    ? { opacity: 1 - ramp(t, STRIP[0] + 0.5, STRIP[0] + 1.1) }
                    : undefined
                }
              >
                {line.segs.map((s, si) => (
                  <Segment key={si} s={s} t={t} li={li} />
                ))}
              </li>
            ),
          )}
        </ul>
        {scanOn && <div className="film-scan" style={{ top: `calc(64px + ${scanY} * (100% - 150px))` }} aria-hidden />}

        <div className="film-meter">
          <div className="flex items-baseline justify-between text-[13px] text-ink-2">
            <span>ATS score</span>
            <span className="font-display text-[26px] leading-none font-semibold tabular-nums text-ink">
              {Math.round(score)}
            </span>
          </div>
          <div className="film-track">
            <div className="film-fill" style={{ width: pct(ORIG) }} />
            {split === 0 ? (
              <div className="film-gain" style={{ left: pct(ORIG), width: pct(Math.max(0, score - ORIG)) }} />
            ) : (
              <>
                <div className="film-earned" style={{ left: pct(ORIG), width: pct(STRIPPED - ORIG) }} />
                <div
                  className="film-fab"
                  style={{ left: pct(STRIPPED), width: pct(LLM - STRIPPED), opacity: 0.35 + 0.65 * split }}
                />
              </>
            )}
          </div>
          <p className="film-caption" style={{ opacity: split }}>
            {LLM - ORIG} points gained: {STRIPPED - ORIG} earned, {LLM - STRIPPED} bought by claims the original
            doesn&apos;t make.
          </p>
        </div>
      </div>

    </figure>
  );
}
