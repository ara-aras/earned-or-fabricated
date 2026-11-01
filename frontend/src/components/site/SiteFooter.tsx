import Link from "next/link";
import { EXTRA_ROUTES, ROUTES } from "@/lib/routes";

export function SiteFooter() {
  return (
    <footer className="foot">
      <div className="foot-inner">
        <div className="grid gap-3">
          <p className="font-display text-[20px] font-semibold text-ink">
            Earned<span className="text-ink-3"> or </span>Fabricated
          </p>
          <p className="max-w-[60ch] text-[14px] text-ink-2">
            A final-year project of the Department of Computer Science and Engineering, P. A. College of Engineering,
            Mangaluru. Everything runs on your machine; your resume is never sent anywhere.
          </p>
          <p className="max-w-[60ch] text-[13px] text-ink-3">
            The checker is rule-based. On 100 hand-checked claims it caught 73% of the unsupported ones, and 80% of its
            flags were correct. Read a flag as a prompt to look, not a verdict.
          </p>
        </div>
        <nav aria-label="Footer" className="foot-links">
          {[...ROUTES, ...EXTRA_ROUTES].map((r) => (
            <Link key={r.href} href={r.href}>{r.label}</Link>
          ))}
        </nav>
      </div>
    </footer>
  );
}
