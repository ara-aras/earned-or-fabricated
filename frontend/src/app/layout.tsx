import type { Metadata } from "next";
import { IBM_Plex_Mono, IBM_Plex_Sans, Newsreader } from "next/font/google";
import { CommandPalette } from "@/components/site/CommandPalette";
import { SiteFooter } from "@/components/site/SiteFooter";
import { SiteNav } from "@/components/site/SiteNav";
import "./globals.css";
import "./landing.css";
import "./site.css";
import "./pages.css";

const display = Newsreader({
  variable: "--font-disp",
  subsets: ["latin"],
  weight: ["500", "600", "700"],
  style: ["normal", "italic"],
  display: "swap",
});

const body = IBM_Plex_Sans({ variable: "--font-body", subsets: ["latin"], weight: ["400", "500", "600"], display: "swap" });

const code = IBM_Plex_Mono({ variable: "--font-code", subsets: ["latin"], weight: ["400", "500"], display: "swap" });

export const metadata: Metadata = {
  title: { default: "Earned or Fabricated", template: "%s · Earned or Fabricated" },
  description:
    "Checks an AI-rewritten resume against the original, and splits its ATS score gain into the part the original supports and the part bought by unsupported claims.",
};

// Runs before paint so a saved or system dark theme never flashes light first.
const THEME_SCRIPT = `try{var t=localStorage.getItem("eof.theme");if(!t)t=matchMedia("(prefers-color-scheme: dark)").matches?"dark":"light";document.documentElement.dataset.theme=t}catch(e){}`;

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en" className={`${display.variable} ${body.variable} ${code.variable}`} suppressHydrationWarning>
      <head>
        <script dangerouslySetInnerHTML={{ __html: THEME_SCRIPT }} />
      </head>
      <body suppressHydrationWarning>
        <a href="#main" className="skip-link">Skip to content</a>
        <SiteNav />
        <main id="main">{children}</main>
        <SiteFooter />
        <CommandPalette />
      </body>
    </html>
  );
}
