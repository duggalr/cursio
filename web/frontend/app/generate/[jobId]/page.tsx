"use client";

import Link from "next/link";

export default function JobProgressPage() {
  return (
    <div className="mx-auto max-w-lg px-6 py-16 text-center">
      <h1
        className="mb-2 text-2xl text-[var(--color-foreground)]"
        style={{ fontFamily: "var(--font-serif)" }}
      >
        Generation paused
      </h1>
      <p className="mb-6 text-sm text-[var(--color-muted)]">
        Video generation is temporarily disabled while we work on infrastructure improvements.
      </p>
      <Link href="/" className="text-sm text-[var(--color-foreground)] underline">
        Back to gallery
      </Link>
    </div>
  );
}
