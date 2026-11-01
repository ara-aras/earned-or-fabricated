import type { Metadata } from "next";
import { HeroFilm } from "@/components/HeroFilm";
import { Accuracy, FormulaPlayground, Pipeline } from "@/components/method/Method";
import { PageHead } from "@/components/site/PageHead";

export const metadata: Metadata = { title: "Method" };

export default function MethodPage() {
  return (
    <div className="page-wrap">
      <PageHead title="How the audit works">
        The checker never trusts the rewrite. Your original resume is the only evidence, and everything runs on your
        machine.
      </PageHead>

      <section className="section">
        <div className="section-head">
          <h2 className="h2">Four steps, one rewrite</h2>
        </div>
        <Pipeline />
      </section>

      <section className="section">
        <div className="section-head">
          <h2 className="h2">Watch one audit run</h2>
          <p className="lede">A short loop of the four steps on a made-up resume.</p>
        </div>
        <div className="max-w-[640px]">
          <HeroFilm />
        </div>
      </section>

      <section className="section">
        <div className="section-head">
          <h2 className="h2">Play with the formula</h2>
          <p className="lede">
            The fabricated share is the part of the gain that disappears when the unsupported claims are removed. Move the
            scores to see how it behaves, including the cases the audit treats specially.
          </p>
        </div>
        <FormulaPlayground />
      </section>

      <section className="section">
        <div className="section-head">
          <h2 className="h2">How often the checker is right</h2>
          <p className="lede">
            Measured on 100 claims labelled by hand. The checker is rule-based, so read a flag as a prompt to look, not a
            verdict.
          </p>
        </div>
        <Accuracy />
      </section>
    </div>
  );
}
