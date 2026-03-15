"use client";

import { motion } from "motion/react";

const floatingIcons = [
  // Atom / molecule
  {
    svg: (
      <svg viewBox="0 0 64 64" fill="none" stroke="currentColor" strokeWidth="1.2">
        <ellipse cx="32" cy="32" rx="28" ry="12" transform="rotate(0 32 32)" />
        <ellipse cx="32" cy="32" rx="28" ry="12" transform="rotate(60 32 32)" />
        <ellipse cx="32" cy="32" rx="28" ry="12" transform="rotate(120 32 32)" />
        <circle cx="32" cy="32" r="3" fill="currentColor" />
      </svg>
    ),
    size: 64,
    position: { top: "8%", left: "4%" },
    duration: 22,
    delay: 0,
  },
  // Pi symbol
  {
    svg: (
      <svg viewBox="0 0 64 64" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round">
        <path d="M16 18h32M24 18v28M40 18v20c0 5 3 8 8 8" />
      </svg>
    ),
    size: 52,
    position: { top: "18%", right: "6%" },
    duration: 26,
    delay: 2,
  },
  // Light bulb
  {
    svg: (
      <svg viewBox="0 0 64 64" fill="none" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round">
        <path d="M24 44v4a4 4 0 004 4h8a4 4 0 004-4v-4" />
        <path d="M24 44c-6-4-10-10-10-18a18 18 0 0136 0c0 8-4 14-10 18" />
        <path d="M26 50h12" />
        <line x1="32" y1="8" x2="32" y2="4" />
        <line x1="50" y1="16" x2="54" y2="13" />
        <line x1="14" y1="16" x2="10" y2="13" />
      </svg>
    ),
    size: 58,
    position: { top: "45%", left: "2%" },
    duration: 20,
    delay: 4,
  },
  // DNA helix
  {
    svg: (
      <svg viewBox="0 0 64 64" fill="none" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round">
        <path d="M20 4c0 12 24 12 24 24s-24 12-24 24" />
        <path d="M44 4c0 12-24 12-24 24s24 12 24 24" />
        <line x1="22" y1="12" x2="42" y2="12" />
        <line x1="20" y1="28" x2="44" y2="28" />
        <line x1="22" y1="44" x2="42" y2="44" />
      </svg>
    ),
    size: 56,
    position: { top: "65%", right: "3%" },
    duration: 24,
    delay: 1,
  },
  // Sigma / summation
  {
    svg: (
      <svg viewBox="0 0 64 64" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
        <polyline points="44,14 20,14 36,32 20,50 44,50" />
      </svg>
    ),
    size: 46,
    position: { top: "82%", left: "8%" },
    duration: 28,
    delay: 3,
  },
  // Infinity
  {
    svg: (
      <svg viewBox="0 0 64 64" fill="none" stroke="currentColor" strokeWidth="1.5">
        <path d="M32 32c-6-8-16-12-20-6s0 14 8 16 16-2 12-10c4 8 8 16 16 10s4-18-4-16-6 8-12 6" />
      </svg>
    ),
    size: 50,
    position: { top: "35%", right: "10%" },
    duration: 30,
    delay: 5,
  },
  // Triangle / geometry
  {
    svg: (
      <svg viewBox="0 0 64 64" fill="none" stroke="currentColor" strokeWidth="1.5" strokeLinejoin="round">
        <polygon points="32,8 56,52 8,52" />
        <circle cx="32" cy="38" r="10" />
      </svg>
    ),
    size: 54,
    position: { top: "12%", left: "48%" },
    duration: 25,
    delay: 6,
  },
  // Sine wave
  {
    svg: (
      <svg viewBox="0 0 80 40" fill="none" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round">
        <path d="M4 20 C14 4, 24 4, 34 20 S54 36, 64 20 S74 4, 76 20" />
      </svg>
    ),
    size: 70,
    position: { bottom: "12%", left: "32%" },
    duration: 22,
    delay: 7,
  },
];

export default function FloatingBackground() {
  return (
    <div className="pointer-events-none fixed inset-0 overflow-hidden" aria-hidden="true">
      {floatingIcons.map((icon, i) => (
        <motion.div
          key={i}
          className="absolute text-[var(--color-border)]"
          style={{
            ...icon.position,
            width: icon.size,
            height: icon.size,
            opacity: 0,
          }}
          animate={{
            y: [0, -14, 0, 10, 0],
            rotate: [0, 4, -3, 2, 0],
            opacity: [0.45, 0.65, 0.45, 0.55, 0.45],
          }}
          transition={{
            duration: icon.duration,
            repeat: Infinity,
            ease: "easeInOut",
            delay: icon.delay,
          }}
        >
          {icon.svg}
        </motion.div>
      ))}
    </div>
  );
}
