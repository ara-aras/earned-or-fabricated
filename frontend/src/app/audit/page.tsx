import type { Metadata } from "next";
import { AuditTool } from "@/components/audit/AuditTool";
import { PageHead } from "@/components/site/PageHead";

export const metadata: Metadata = { title: "Audit a rewrite" };

export default function AuditPage() {
  return (
    <div className="page-wrap">
      <PageHead title="Audit your own rewrite">
        Paste your original resume and the job. Add the version ChatGPT or another tool wrote for you, or let a local model
        write one. You get the score split and every unsupported line marked.
      </PageHead>
      <AuditTool />
    </div>
  );
}
