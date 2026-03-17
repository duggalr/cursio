"use client";

import { useEffect, useState, useCallback, useRef } from "react";
import { useRouter } from "next/navigation";
import Link from "next/link";
import { motion, AnimatePresence } from "motion/react";
import VideoCard from "@/components/VideoCard";
import AuthModal from "@/components/AuthModal";
import { fetchVideos, fetchJobStatus, fetchActiveJob, generateVideo, type Video } from "@/lib/api";
import type { User, SupabaseClient } from "@supabase/supabase-js";

const suggestedTopics = [
  { label: "How gravity works", prompt: "Explain how gravity works — from Newton's apple to Einstein's curved spacetime" },
  { label: "Why the sky is blue", prompt: "Why is the sky blue? Explain Rayleigh scattering and how light interacts with the atmosphere" },
  { label: "How neural networks learn", prompt: "How do neural networks learn? Walk through forward propagation, loss functions, and backpropagation" },
  { label: "The Fibonacci sequence", prompt: "What is the Fibonacci sequence, where does it appear in nature, and why is it connected to the golden ratio?" },
  { label: "How encryption works", prompt: "How does public-key encryption work? Explain RSA and why it keeps our data safe" },
];

const steps = [
  { key: "planning", label: "Planning scenes" },
  { key: "generating", label: "Writing animation code" },
  { key: "rendering", label: "Rendering animations" },
  { key: "voiceover", label: "Generating narration" },
  { key: "assembling", label: "Assembling final video" },
];

function getStepIndex(status: string): number {
  const idx = steps.findIndex((s) => s.key === status);
  return idx === -1 ? 0 : idx;
}

export default function HomePage() {
  const [mounted, setMounted] = useState(false);
  const router = useRouter();
  const [videos, setVideos] = useState<Video[]>([]);
  const [initialLoad, setInitialLoad] = useState(true);
  const [refreshing, setRefreshing] = useState(false);
  const [search, setSearch] = useState("");
  const [sort, setSort] = useState<"recent" | "most_liked">("recent");
  const debounceRef = useRef<ReturnType<typeof setTimeout> | null>(null);

  // Auth state
  const [user, setUser] = useState<User | null>(null);
  const [authModal, setAuthModal] = useState(false);
  const [authMode, setAuthMode] = useState<"signin" | "signup">("signup");
  const supabaseRef = useRef<SupabaseClient | null>(null);

  // Generate state
  const [topic, setTopic] = useState("");
  const [duration, setDuration] = useState("short");
  const [submitting, setSubmitting] = useState(false);
  const [generateError, setGenerateError] = useState<string | null>(null);

  // Job progress (inline) — restore from localStorage on mount
  const [activeJobId, setActiveJobId] = useState<string | null>(null);
  const [jobStatus, setJobStatus] = useState<string | null>(null);
  const [jobVideoId, setJobVideoId] = useState<string | null>(null);
  const [jobError, setJobError] = useState<string | null>(null);
  const pollRef = useRef<ReturnType<typeof setInterval> | null>(null);

  // Track mount to prevent SSR → hydration animation flash
  useEffect(() => { setMounted(true); }, []);

  // Restore active job from backend on login
  useEffect(() => {
    if (!user || !supabaseRef.current) return;
    (async () => {
      try {
        const { data: { session } } = await supabaseRef.current!.auth.getSession();
        if (!session?.access_token) return;
        const job = await fetchActiveJob(session.access_token);
        if (job && job.status !== "completed" && job.status !== "failed") {
          setActiveJobId(job.id);
          setJobStatus(job.status);
        }
      } catch {
        // ignore — no active job
      }
    })();
  }, [user]);

  // Init auth
  useEffect(() => {
    let subscription: { unsubscribe: () => void } | null = null;
    async function init() {
      try {
        const { createClient } = await import("@/lib/supabase");
        const supabase = createClient();
        supabaseRef.current = supabase;
        const { data: { user } } = await supabase.auth.getUser();
        setUser(user);
        const { data: { subscription: sub } } = supabase.auth.onAuthStateChange(
          (_event: string, session: { user: User | null } | null) => {
            setUser(session?.user ?? null);
          }
        );
        subscription = sub;
      } catch {
        // Supabase not configured
      }
    }
    init();
    return () => { subscription?.unsubscribe(); };
  }, []);

  // Load videos
  const loadVideos = useCallback(async (isInitial = false) => {
    if (isInitial) setInitialLoad(true);
    else setRefreshing(true);
    try {
      const data = await fetchVideos({ search: search || undefined, sort });
      setVideos(data.videos);
    } catch {
      setVideos([]);
    } finally {
      setInitialLoad(false);
      setRefreshing(false);
    }
  }, [search, sort]);

  useEffect(() => {
    if (videos.length === 0 && !search) {
      loadVideos(true);
    } else {
      loadVideos(false);
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [search, sort]);

  // Debounced real-time search
  const handleSearchInput = (value: string) => {
    if (debounceRef.current) clearTimeout(debounceRef.current);
    debounceRef.current = setTimeout(() => {
      setSearch(value);
    }, 300);
  };

  // Poll job status
  useEffect(() => {
    if (!activeJobId) return;
    const poll = async () => {
      try {
        const data = await fetchJobStatus(activeJobId);
        setJobStatus(data.status);
        if (data.status === "completed") {
          localStorage.removeItem("curiso_active_job");
          if (pollRef.current) clearInterval(pollRef.current);
          if (data.video_id) {
            router.push(`/video/${data.video_id}`);
          }
        } else if (data.status === "failed") {
          setJobError(data.error || "Generation failed");
          localStorage.removeItem("curiso_active_job");
          if (pollRef.current) clearInterval(pollRef.current);
        }
      } catch {
        // keep polling
      }
    };
    poll();
    pollRef.current = setInterval(poll, 3000);
    return () => { if (pollRef.current) clearInterval(pollRef.current); };
  }, [activeJobId, loadVideos]);

  const handleGenerate = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!topic.trim()) return;

    if (!user) {
      setAuthMode("signup");
      setAuthModal(true);
      return;
    }

    setSubmitting(true);
    setGenerateError(null);
    setActiveJobId(null);
    setJobStatus(null);
    setJobVideoId(null);
    setJobError(null);

    try {
      const { data: { session } } = await supabaseRef.current!.auth.getSession();
      if (!session?.access_token) {
        setAuthModal(true);
        return;
      }
      const { job_id } = await generateVideo(topic, duration, session.access_token);
      localStorage.setItem("curiso_active_job", job_id);
      setActiveJobId(job_id);
      setJobStatus("planning");
      setTopic("");
    } catch (err) {
      setGenerateError(err instanceof Error ? err.message : "Failed to start generation");
    } finally {
      setSubmitting(false);
    }
  };

  const currentStepIdx = jobStatus ? getStepIndex(jobStatus) : -1;

  return (
    <>
      <div className="mx-auto max-w-6xl px-6 pt-8 pb-16">
        {/* Header + Prompt */}
        <motion.div
          className="mb-8"
          initial={{ opacity: 0, y: 16 }}
          animate={mounted ? { opacity: 1, y: 0 } : { opacity: 0, y: 16 }}
          transition={{ duration: 0.5, ease: "easeOut" }}
        >
          <div className="mb-5">
            <h1
              className="text-2xl text-[var(--color-foreground)]"
              style={{ fontFamily: "var(--font-serif)" }}
            >
              Learn anything.
            </h1>
            <motion.p
              className="mt-1.5 text-sm text-[var(--color-muted)]"
              initial={{ opacity: 0 }}
              animate={mounted ? { opacity: 1 } : { opacity: 0 }}
              transition={{ delay: 0.3, duration: 0.5 }}
            >
              Enter a topic you're curious about, pick a video length, and let AI generate an animated explanation for you.
            </motion.p>
          </div>

          <motion.form
            onSubmit={handleGenerate}
            initial={{ opacity: 0, y: 12 }}
            animate={mounted ? { opacity: 1, y: 0 } : { opacity: 0, y: 12 }}
            transition={{ delay: 0.15, duration: 0.5, ease: "easeOut" }}
          >
            <div className="rounded-xl border border-[var(--color-border)] bg-[var(--color-surface)] p-4 shadow-[0_1px_3px_rgba(0,0,0,0.04)] transition-shadow focus-within:shadow-[0_2px_8px_rgba(0,0,0,0.06)]">
              <textarea
                value={topic}
                onChange={(e) => setTopic(e.target.value)}
                placeholder="What are you curious about?"
                rows={2}
                className="w-full resize-none bg-transparent text-sm text-[var(--color-foreground)] placeholder-[var(--color-muted)] outline-none"
              />
              {!topic.trim() && (
                <div className="flex flex-wrap gap-1.5 pt-1 pb-2">
                  {suggestedTopics.map((s) => (
                    <button
                      key={s.label}
                      type="button"
                      onClick={() => setTopic(s.prompt)}
                      className="rounded-full border border-[var(--color-border)] px-2.5 py-1 text-xs text-[var(--color-muted)] transition-colors hover:border-[var(--color-muted)] hover:text-[var(--color-foreground)]"
                    >
                      {s.label}
                    </button>
                  ))}
                </div>
              )}
              <div className="flex items-center justify-between pt-2">
                <div className="flex gap-1">
                  {["short", "medium", "long"].map((d) => (
                    <button
                      key={d}
                      type="button"
                      onClick={() => setDuration(d)}
                      className={`rounded-md px-3 py-1 text-xs capitalize transition-colors ${
                        duration === d
                          ? "bg-[var(--color-surface-hover)] font-medium text-[var(--color-foreground)]"
                          : "text-[var(--color-muted)] hover:text-[var(--color-foreground)]"
                      }`}
                    >
                      {d}
                    </button>
                  ))}
                </div>
                <button
                  type="submit"
                  disabled={submitting || !topic.trim()}
                  className="rounded-lg bg-[var(--color-foreground)] px-4 py-1.5 text-xs font-medium text-[var(--color-background)] transition-opacity disabled:opacity-40"
                >
                  {submitting ? "Starting..." : "Generate"}
                </button>
              </div>
            </div>
          </motion.form>

          <AnimatePresence>
            {generateError && (
              <motion.p
                className="mt-3 text-xs text-red-600"
                initial={{ opacity: 0, height: 0 }}
                animate={{ opacity: 1, height: "auto" }}
                exit={{ opacity: 0, height: 0 }}
              >
                {generateError}
              </motion.p>
            )}
          </AnimatePresence>

          {/* Inline generation progress */}
          <AnimatePresence>
            {activeJobId && jobStatus && jobStatus !== "completed" && !jobError && (
              <motion.div
                className="mt-4 rounded-lg border border-[var(--color-border)] bg-[var(--color-surface)] px-4 py-3"
                initial={{ opacity: 0, y: -8 }}
                animate={{ opacity: 1, y: 0 }}
                exit={{ opacity: 0, y: -8 }}
                transition={{ duration: 0.3 }}
              >
                <div className="flex items-center gap-3">
                  <div className="h-4 w-4 animate-spin rounded-full border-2 border-[var(--color-border)] border-t-[var(--color-foreground)]" />
                  <span className="text-sm text-[var(--color-foreground)]">
                    {steps[currentStepIdx]?.label || "Processing"}...
                  </span>
                  <span className="text-xs text-[var(--color-muted)]">
                    Step {currentStepIdx + 1} of {steps.length}
                  </span>
                </div>
                <div className="mt-2 flex gap-1">
                  {steps.map((_, idx) => (
                    <motion.div
                      key={idx}
                      className="h-1 flex-1 rounded-full"
                      initial={{ backgroundColor: "var(--color-border)" }}
                      animate={{
                        backgroundColor: idx <= currentStepIdx
                          ? "var(--color-foreground)"
                          : "var(--color-border)",
                      }}
                      transition={{ duration: 0.4 }}
                    />
                  ))}
                </div>
                <p className="mt-2.5 text-[11px] text-[var(--color-muted)]">
                  This usually takes around 5 minutes. You can refresh or leave this page — we'll notify you when it's ready.
                </p>
              </motion.div>
            )}
          </AnimatePresence>

          {/* Job complete */}
          <AnimatePresence>
            {jobStatus === "completed" && jobVideoId && (
              <motion.div
                className="mt-4 flex items-center gap-3 rounded-lg border border-[var(--color-border)] bg-[var(--color-surface)] px-4 py-3"
                initial={{ opacity: 0, scale: 0.97 }}
                animate={{ opacity: 1, scale: 1 }}
                exit={{ opacity: 0, scale: 0.97 }}
                transition={{ duration: 0.3 }}
              >
                <svg xmlns="http://www.w3.org/2000/svg" className="h-4 w-4 text-green-600" viewBox="0 0 20 20" fill="currentColor">
                  <path fillRule="evenodd" d="M16.707 5.293a1 1 0 010 1.414l-8 8a1 1 0 01-1.414 0l-4-4a1 1 0 011.414-1.414L8 12.586l7.293-7.293a1 1 0 011.414 0z" clipRule="evenodd" />
                </svg>
                <span className="text-sm text-[var(--color-foreground)]">Video ready!</span>
                <Link
                  href={`/video/${jobVideoId}`}
                  className="ml-auto text-sm font-medium text-[var(--color-foreground)] underline"
                >
                  Watch now
                </Link>
                <button
                  onClick={() => { setActiveJobId(null); setJobStatus(null); setJobVideoId(null); localStorage.removeItem("curiso_active_job"); }}
                  className="text-xs text-[var(--color-muted)] hover:text-[var(--color-foreground)]"
                >
                  Dismiss
                </button>
              </motion.div>
            )}
          </AnimatePresence>

          {/* Job failed */}
          <AnimatePresence>
            {jobError && (
              <motion.div
                className="mt-4 flex items-center gap-3 rounded-lg border border-red-200 bg-red-50 px-4 py-3"
                initial={{ opacity: 0 }}
                animate={{ opacity: 1 }}
                exit={{ opacity: 0 }}
              >
                <span className="text-sm text-red-700">Generation failed.</span>
                <button
                  onClick={() => { setActiveJobId(null); setJobStatus(null); setJobError(null); localStorage.removeItem("curiso_active_job"); }}
                  className="ml-auto text-xs text-red-600 underline"
                >
                  Dismiss
                </button>
              </motion.div>
            )}
          </AnimatePresence>
        </motion.div>

        {/* Gallery header + Sort + Search controls */}
        <motion.div
          className="mb-5"
          initial={{ opacity: 0 }}
          animate={mounted ? { opacity: 1 } : { opacity: 0 }}
          transition={{ delay: 0.3, duration: 0.4 }}
        >
          <p className="mb-3 text-xs text-[var(--color-muted)]">
            Explore videos others have generated below.
          </p>
          <div className="flex items-center justify-between">
          <div className="flex gap-4 text-sm">
            <button
              onClick={() => setSort("recent")}
              className={`transition-colors ${
                sort === "recent"
                  ? "font-medium text-[var(--color-foreground)]"
                  : "text-[var(--color-muted)] hover:text-[var(--color-foreground)]"
              }`}
            >
              Recent
            </button>
            <button
              onClick={() => setSort("most_liked")}
              className={`transition-colors ${
                sort === "most_liked"
                  ? "font-medium text-[var(--color-foreground)]"
                  : "text-[var(--color-muted)] hover:text-[var(--color-foreground)]"
              }`}
            >
              Most Liked
            </button>
          </div>

          <input
            type="text"
            onChange={(e) => handleSearchInput(e.target.value)}
            placeholder="Search..."
            className="w-40 rounded-lg border border-[var(--color-border)] bg-[var(--color-surface)] px-3 py-1.5 text-xs text-[var(--color-foreground)] placeholder-[var(--color-muted)] outline-none transition-colors focus:border-[var(--color-muted)]"
          />
          </div>
        </motion.div>

        {/* Video Grid */}
        <div className="relative min-h-[200px]">
          {/* Refreshing overlay spinner */}
          <AnimatePresence>
            {refreshing && (
              <motion.div
                className="absolute inset-0 z-10 flex items-start justify-center pt-20"
                initial={{ opacity: 0 }}
                animate={{ opacity: 1 }}
                exit={{ opacity: 0 }}
                transition={{ duration: 0.15 }}
              >
                <div className="h-5 w-5 animate-spin rounded-full border-2 border-[var(--color-border)] border-t-[var(--color-foreground)]" />
              </motion.div>
            )}
          </AnimatePresence>

          <div className={`transition-opacity duration-200 ${refreshing ? "opacity-40" : "opacity-100"}`}>
            {initialLoad ? (
              <div className="grid grid-cols-1 gap-5 sm:grid-cols-2 lg:grid-cols-3">
                {Array.from({ length: 6 }).map((_, i) => (
                  <div key={i} className="animate-pulse overflow-hidden rounded-lg border border-[var(--color-border)] bg-[var(--color-surface)]">
                    <div className="aspect-video bg-[var(--color-surface-hover)]" />
                    <div className="space-y-2 p-3.5">
                      <div className="h-3.5 w-3/4 rounded bg-[var(--color-surface-hover)]" />
                      <div className="h-3 w-1/2 rounded bg-[var(--color-surface-hover)]" />
                    </div>
                  </div>
                ))}
              </div>
            ) : videos.length === 0 ? (
              <motion.div
                className="py-20 text-center"
                initial={{ opacity: 0 }}
                animate={{ opacity: 1 }}
                transition={{ delay: 0.2 }}
              >
                <p className="text-sm text-[var(--color-muted)]">
                  {search ? `No videos found for "${search}"` : "No videos yet. Generate one above!"}
                </p>
              </motion.div>
            ) : (
              <div className="grid grid-cols-1 gap-5 sm:grid-cols-2 lg:grid-cols-3">
                {videos.map((video, i) => (
                  <motion.div
                    key={video.id}
                    className="h-full"
                    initial={{ opacity: 0, y: 16 }}
                    animate={mounted ? { opacity: 1, y: 0 } : { opacity: 0, y: 16 }}
                    transition={{ delay: 0.1 + i * 0.06, duration: 0.4, ease: "easeOut" }}
                  >
                    <VideoCard video={video} />
                  </motion.div>
                ))}
              </div>
            )}
          </div>
        </div>
      </div>

      <AuthModal isOpen={authModal} onClose={() => setAuthModal(false)} initialMode={authMode} />
    </>
  );
}
