import type { Metadata } from "next";
import { Inter } from "next/font/google";
import NavbarWrapper from "@/components/NavbarWrapper";
import FloatingBackground from "@/components/FloatingBackground";
import "./globals.css";

const inter = Inter({
  variable: "--font-inter",
  subsets: ["latin"],
});

export const metadata: Metadata = {
  title: "Curiso — Understand anything visually",
  description:
    "AI-generated educational videos that make any topic click. Type what you're curious about, get a beautiful animated explanation.",
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="en">
      <body className={`${inter.variable} flex min-h-screen flex-col antialiased`}>
        <FloatingBackground />
        <NavbarWrapper />
        <main className="relative flex-1">{children}</main>
        <footer className="border-t border-[var(--color-border)] py-8">
          <div className="mx-auto max-w-6xl px-6">
            <div className="flex items-center justify-between text-xs text-[var(--color-muted)]">
              <span style={{ fontFamily: "var(--font-serif)" }}>Curiso</span>
              <div className="flex gap-4">
                <a href="/about" className="transition-colors hover:text-[var(--color-foreground)]">About</a>
                <a href="#" className="transition-colors hover:text-[var(--color-foreground)]">Contact</a>
              </div>
            </div>
          </div>
        </footer>
      </body>
    </html>
  );
}
