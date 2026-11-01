import type { Metadata } from "next";
import Link from "next/link";
import { ClaimTypes, ScreenerChart } from "@/components/findings/Findings";
import { PageHead } from "@/components/site/PageHead";

export const metadata: Metadata = { title: "Findings" };

const FACTS = [
  { n: "380", t: "resume and job pairs, real resumes against dated job listings" },
  { n: "22", t: "unsupported claims in a typical rewrite" },
  { n: "98%", t: "of rewrites made at least one" },
  { n: "769 → 464", t: "words: the rewrite also shortens the resume" },
];

export default function FindingsPage() {
  return (
    <div className="page-wrap">
      <PageHead title="What we found on 380 real resumes">
        Each resume was rewritten by a local AI for a real job, then scored by three screeners. We removed every claim the
        original doesn&apos;t support and scored it again. The red part of each bar is the score that disappeared.
      </PageHead>

      <dl className="facts">
        {FACTS.map((f) => (
          <div key={f.n}>
            <dt className="font-display">{f.n}</dt>
            <dd>{f.t}</dd>
          </div>
        ))}
      </dl>

      <section className="section">
        <div className="section-head">
          <h2 className="h2">Most of the gain is bought</h2>
        </div>
        <ScreenerChart />
        <div className="findings-notes">
          <p>
            <b>A keyword ATS pays only for the invented part.</b> The rewrite shortened resumes from 769 to 464 words and lost
            real keywords. Without its unsupported claims it scored 4.3 points <em>below</em> the original.
          </p>
          <p>
            <b>A model grading its own writing is kinder to its inventions.</b> Qwen scored the rewrite 5.1 points higher than
            Gemma did, and 6.5 of those points went to the fabricated part. The honest part got the same score from both.
          </p>
          <p>
            <b>It isn&apos;t the length.</b> Removing the same number of supported lines instead moved the scores by less than
            3 points.
          </p>
        </div>
      </section>

      <section className="section">
        <div className="section-head">
          <h2 className="h2">Five ways a rewrite claims more than you did</h2>
          <p className="lede">
            The checker sorts every addition into one of these. Invented skills pay the most under a keyword ATS,
            significantly more than any other type. LLM screeners spread their reward more evenly.
          </p>
        </div>
        <ClaimTypes />
      </section>

      <section className="section">
        <div className="section-head">
          <h2 className="h2">See it on one resume</h2>
          <p className="lede">The five demo cases reproduce these patterns on resumes you can read in full.</p>
        </div>
        <div className="flex flex-wrap gap-3">
          <Link href="/audit?case=05-data-analyst-mixed" className="btn-dark h-11 px-5 text-[15px]">Audit demo case 5</Link>
          <Link href="/spot" className="btn-line h-11 px-5 text-[15px]">Try to spot them yourself</Link>
        </div>
      </section>
    </div>
  );
}
