"use client";

import dynamic from "next/dynamic";

const Navbar = dynamic(() => import("./Navbar"), {
  ssr: false,
  loading: () => (
    <nav className="py-4">
      <div className="mx-auto flex max-w-6xl items-center justify-between px-6">
        <span
          className="text-lg text-[var(--color-foreground)]"
          style={{ fontFamily: "var(--font-serif)" }}
        >
          Curiso
        </span>
        <div className="h-8" />
      </div>
    </nav>
  ),
});

export default function NavbarWrapper() {
  return <Navbar />;
}
