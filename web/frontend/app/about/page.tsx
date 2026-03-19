"use client";

import Link from "next/link";
import { motion } from "motion/react";
import { useState, useEffect } from "react";

const sections = [
  {
    title: "What is Curiso?",
    content:
      "Curiso is a 100% free AI-powered platform that turns any topic into a short, animated educational video. Type in what you want to learn about, and within minutes you will get a visual explanation with narration, animations, and a clear storyline. No limits, no payment required. Think of it as having a personal tutor who can explain anything visually, on demand.",
  },
  {
    title: "How it works",
    content:
      "Behind the scenes, Curiso uses a multi-stage pipeline. First, an AI plans the lesson structure and writes a narration script. Then, it generates mathematical animation code using Manim (the same engine behind 3Blue1Brown videos). The animations are rendered, paired with AI-generated voiceover, and assembled into a final video. The entire process is automated and takes about five minutes.",
  },
  {
    title: "Why we built this",
    content:
      "We believe the best way to understand something is to see it. Text explanations are great, but a well-crafted visual explanation can make a concept click in seconds. The problem is that creating these kinds of videos traditionally takes hours of work, specialized software knowledge, and animation skills. Curiso removes all of that friction. Anyone can generate a high-quality educational video just by describing what they want to learn.",
  },
];

const explorations = [
  {
    label: "Interactive videos",
    description:
      "Letting viewers pause, ask follow-up questions, and get personalized explanations mid-video.",
  },
  {
    label: "Multiple visual styles",
    description:
      "Beyond math animations: stick figure explainers, 3D scenes, whiteboard-style drawings, and diagram-based walkthroughs.",
  },
  {
    label: "Longer, deeper content",
    description:
      "Full course-length videos that break complex subjects into chapters with progressive depth.",
  },
  {
    label: "Collaborative learning",
    description:
      "Letting users remix, annotate, and build on each other's generated videos to create shared knowledge bases.",
  },
  {
    label: "Multilingual generation",
    description:
      "Generating videos in multiple languages so anyone in the world can learn in their native tongue.",
  },
  {
    label: "Real-time generation",
    description:
      "Reducing generation time from minutes to seconds, enabling instant visual answers to any question.",
  },
];

export default function AboutPage() {
  const [mounted, setMounted] = useState(false);
  useEffect(() => { setMounted(true); }, []);

  return (
    <div className="mx-auto max-w-3xl px-6 pt-8 pb-20">
      <motion.div
        initial={{ opacity: 0, y: 16 }}
        animate={mounted ? { opacity: 1, y: 0 } : { opacity: 0, y: 16 }}
        transition={{ duration: 0.5, ease: "easeOut" }}
      >
        <Link
          href="/"
          className="mb-6 inline-flex items-center text-sm text-[var(--color-muted)] hover:text-[var(--color-foreground)]"
        >
          &larr; Back to home
        </Link>

        <h1
          className="mb-2 text-3xl text-[var(--color-foreground)]"
          style={{ fontFamily: "var(--font-serif)" }}
        >
          About Curiso
        </h1>
        <p className="mb-10 text-sm text-[var(--color-muted)]">
          Understand anything visually.
        </p>
      </motion.div>

      {/* Main sections */}
      <div className="space-y-10">
        {sections.map((section, i) => (
          <motion.div
            key={section.title}
            initial={{ opacity: 0, y: 16 }}
            animate={mounted ? { opacity: 1, y: 0 } : { opacity: 0, y: 16 }}
            transition={{ delay: 0.1 + i * 0.08, duration: 0.5, ease: "easeOut" }}
          >
            <h2 className="mb-3 text-lg font-medium text-[var(--color-foreground)]">
              {section.title}
            </h2>
            <p className="text-sm leading-relaxed text-[var(--color-muted)]">
              {section.content}
            </p>
          </motion.div>
        ))}
      </div>

      {/* Explorations */}
      <motion.div
        className="mt-16"
        initial={{ opacity: 0, y: 16 }}
        animate={mounted ? { opacity: 1, y: 0 } : { opacity: 0, y: 16 }}
        transition={{ delay: 0.4, duration: 0.5, ease: "easeOut" }}
      >
        <h2 className="mb-2 text-lg font-medium text-[var(--color-foreground)]">
          What we are exploring next
        </h2>
        <p className="mb-6 text-sm text-[var(--color-muted)]">
          Curiso is just the beginning. Here are some of the directions we are actively thinking about
          in education, AI, and video generation.
        </p>

        <div className="grid grid-cols-1 gap-4 sm:grid-cols-2">
          {explorations.map((item, i) => (
            <motion.div
              key={item.label}
              className="rounded-lg border border-[var(--color-border)] bg-[var(--color-surface)] p-4"
              initial={{ opacity: 0, y: 12 }}
              animate={mounted ? { opacity: 1, y: 0 } : { opacity: 0, y: 12 }}
              transition={{ delay: 0.5 + i * 0.06, duration: 0.4, ease: "easeOut" }}
            >
              <h3 className="mb-1.5 text-sm font-medium text-[var(--color-foreground)]">
                {item.label}
              </h3>
              <p className="text-xs leading-relaxed text-[var(--color-muted)]">
                {item.description}
              </p>
            </motion.div>
          ))}
        </div>
      </motion.div>

      {/* CTA */}
      <motion.div
        className="mt-16 rounded-xl border border-[var(--color-border)] bg-[var(--color-surface)] p-8 text-center"
        initial={{ opacity: 0, y: 12 }}
        animate={mounted ? { opacity: 1, y: 0 } : { opacity: 0, y: 12 }}
        transition={{ delay: 0.7, duration: 0.5, ease: "easeOut" }}
      >
        <h2
          className="mb-2 text-xl text-[var(--color-foreground)]"
          style={{ fontFamily: "var(--font-serif)" }}
        >
          Curious about something?
        </h2>
        <p className="mb-5 text-sm text-[var(--color-muted)]">
          Curiso is 100% free with unlimited generations. Create your first video now.
        </p>
        <Link
          href="/"
          className="inline-block rounded-lg bg-[var(--color-foreground)] px-5 py-2 text-sm font-medium text-[var(--color-background)] transition-opacity hover:opacity-80"
        >
          Try Curiso
        </Link>
      </motion.div>
    </div>
  );
}
