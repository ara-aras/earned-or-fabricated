import type { Metadata } from "next";
import Link from "next/link";
import { PageHead } from "@/components/site/PageHead";

export const metadata: Metadata = { title: "About" };

const TEAM = ["M. Shafikuddeen", "Mohammed Sahil", "Noorul Ameen", "Shammas Muneer Ali"];
const initials = (n: string) => n.replace(/^M\. /, "M ").split(" ").filter(Boolean).slice(0, 2).map((w) => w[0]).join("");

export default function AboutPage() {
  return (
    <div className="page-wrap">
      <PageHead title="About the project">
        A final-year project of the Department of Computer Science and Engineering, P. A. College of Engineering,
        Mangaluru.
      </PageHead>

      <section className="section">
        <div className="section-head">
          <h2 className="h2">The question</h2>
          <p className="lede">
            AI resume rewriters raise applicant-tracking scores. We measured how much of that gain comes from claims the
            original resume does not support: skills the candidate never listed, numbers they never wrote, inflated roles,
            and degrees or certificates they do not hold. We also built a guarded rewriter that keeps only the earned part.
          </p>
        </div>
        <Link href="/findings" className="btn-line h-11 w-fit px-5 text-[15px]">Read the findings</Link>
      </section>

      <section className="section">
        <div className="section-head">
          <h2 className="h2">The team</h2>
        </div>
        <ul className="team">
          {TEAM.map((n) => (
            <li key={n}>
              <span className="team-mono font-display" aria-hidden>{initials(n)}</span>
              <span className="font-semibold text-ink">{n}</span>
            </li>
          ))}
          <li>
            <span className="team-mono team-guide font-display" aria-hidden>MS</span>
            <span className="grid">
              <span className="font-semibold text-ink">Prof. Mohammed Saifudeen</span>
              <span className="text-[13px] text-ink-3">Project guide</span>
            </span>
          </li>
        </ul>
      </section>

      <section className="section">
        <div className="section-head">
          <h2 className="h2">Privacy</h2>
          <p className="lede">
            The rewriter is a local model run through Ollama, and the checker is plain rules. Your resume goes from this page
            to the backend on your own machine and nowhere else. Saved audits live in this browser&apos;s storage; you can
            delete them on the History page.
          </p>
        </div>
      </section>
    </div>
  );
}
