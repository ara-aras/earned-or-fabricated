import type { Metadata } from "next";
import { PageHead } from "@/components/site/PageHead";
import { SpotGame } from "@/components/spot/SpotGame";

export const metadata: Metadata = { title: "Spot the fabrication" };

export default function SpotPage() {
  return (
    <div className="page-wrap">
      <PageHead title="Spot the fabrication">
        Five real AI rewrites. Read each one against the original and mark every line that claims a skill, number, role or
        certificate the original never mentions. Then see how your eye compares with the checker.
      </PageHead>
      <SpotGame />
    </div>
  );
}
