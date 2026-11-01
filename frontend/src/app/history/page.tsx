import type { Metadata } from "next";
import { HistoryList } from "@/components/history/HistoryList";
import { PageHead } from "@/components/site/PageHead";

export const metadata: Metadata = { title: "History" };

export default function HistoryPage() {
  return (
    <div className="page-wrap">
      <PageHead title="Your audits">
        Kept in this browser only. Open one to see it again, download its report, or watch how your rewrites change over
        time.
      </PageHead>
      <HistoryList />
    </div>
  );
}
