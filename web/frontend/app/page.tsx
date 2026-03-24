"use client";

import { useEffect, useState, useCallback, useRef } from "react";
import { useRouter } from "next/navigation";
import Link from "next/link";
import { motion, AnimatePresence } from "motion/react";
import VideoCard from "@/components/VideoCard";
import AuthModal from "@/components/AuthModal";
import { Dice5 } from "lucide-react";
import { fetchVideos, fetchTags, fetchJobStatus, fetchActiveJob, generateVideo, generateFromPaper, type Video, type TagWithCount } from "@/lib/api";
import type { User, SupabaseClient } from "@supabase/supabase-js";

const allTopics = [
  { label: "How gravity works", prompt: "Explain how gravity works, from Newton's apple to Einstein's curved spacetime" },
  { label: "Why the sky is blue", prompt: "Why is the sky blue? Explain Rayleigh scattering and how light interacts with the atmosphere" },
  { label: "How neural networks learn", prompt: "How do neural networks learn? Walk through forward propagation, loss functions, and backpropagation" },
  { label: "The Fibonacci sequence", prompt: "What is the Fibonacci sequence, where does it appear in nature, and why is it connected to the golden ratio?" },
  { label: "How encryption works", prompt: "How does public-key encryption work? Explain RSA and why it keeps our data safe" },
  { label: "Why 0.999... equals 1", prompt: "Why is 0.999 repeating exactly equal to 1? Prove it visually" },
  { label: "What is a black hole", prompt: "What is a black hole and what happens if you fall into one?" },
  { label: "How noise cancelling works", prompt: "How does noise cancelling actually cancel noise? Explain destructive interference" },
  { label: "Why mirrors flip left/right", prompt: "Why do mirrors flip left and right but not up and down?" },
  { label: "What is Euler's number e", prompt: "What is Euler's number e and why does it show up everywhere in math and nature?" },
  { label: "How GPS uses relativity", prompt: "How does GPS use Einstein's relativity to stay accurate?" },
  { label: "Why we dream", prompt: "Why do we dream and what happens in the brain during REM sleep?" },
  { label: "How CRISPR edits DNA", prompt: "How does CRISPR edit DNA like a molecular pair of scissors?" },
  { label: "What causes inflation", prompt: "What causes inflation and why does your money lose value over time?" },
  { label: "How a CPU works", prompt: "How does a CPU execute instructions? Explain the fetch-decode-execute cycle" },
  { label: "Why planes fly", prompt: "How do airplane wings generate lift? Explain Bernoulli's principle and angle of attack" },
  { label: "How WiFi sends data", prompt: "How does WiFi transmit data through the air using radio waves?" },
  { label: "What is entropy", prompt: "What is entropy and why can't you unscramble an egg?" },
  { label: "How vaccines work", prompt: "How do vaccines teach your immune system to fight a virus?" },
  { label: "The double slit experiment", prompt: "How does the double slit experiment prove light is both a wave and a particle?" },
  { label: "How blockchain works", prompt: "What is a blockchain and how does it prevent double spending?" },
  { label: "Why compound interest matters", prompt: "What is compound interest and why did Einstein call it the 8th wonder of the world?" },
  { label: "How QR codes store data", prompt: "How does a QR code store information in a grid of squares?" },
  { label: "What is the Turing machine", prompt: "What is a Turing machine and why did it lead to modern computers?" },
  { label: "How magnets work", prompt: "How do magnets work at the atomic level? Why do some metals stick together?" },
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
  const [myVideoCount, setMyVideoCount] = useState<number | null>(null);
  const [communityTotal, setCommunityTotal] = useState<number | null>(null);
  const [initialLoad, setInitialLoad] = useState(true);
  const [refreshing, setRefreshing] = useState(false);
  const [loadingMore, setLoadingMore] = useState(false);
  const [hasMore, setHasMore] = useState(true);
  const [page, setPage] = useState(1);
  const [search, setSearch] = useState("");
  const loadMoreRef = useRef<HTMLDivElement | null>(null);
  const [tab, setTab] = useState<"my_videos" | "community">("community");
  const [communitySort, setCommunitySort] = useState<"recent" | "most_liked">("recent");
  const [availableTags, setAvailableTags] = useState<TagWithCount[]>([]);
  const [selectedTag, setSelectedTag] = useState<string>("");
  const [tabInitialized, setTabInitialized] = useState(false);
  const debounceRef = useRef<ReturnType<typeof setTimeout> | null>(null);

  // Auth state
  const [user, setUser] = useState<User | null>(null);
  const [authModal, setAuthModal] = useState(false);
  const [authMode, setAuthMode] = useState<"signin" | "signup">("signup");
  const supabaseRef = useRef<SupabaseClient | null>(null);

  // Randomize suggested topics (only on client to avoid hydration mismatch)
  const [suggestedTopics, setSuggestedTopics] = useState<typeof allTopics>([]);
  useEffect(() => {
    const shuffled = [...allTopics].sort(() => Math.random() - 0.5);
    setSuggestedTopics(shuffled.slice(0, 5));
  }, []);
  const refreshTopics = () => {
    const shuffled = [...allTopics].sort(() => Math.random() - 0.5);
    setSuggestedTopics(shuffled.slice(0, 5));
  };

  // Generate state
  const [inputMode, setInputMode] = useState<"topic" | "paper">("topic");
  const [paperFile, setPaperFile] = useState<File | null>(null);
  const [topic, setTopic] = useState("");
  const [duration, setDuration] = useState("short");
  const [useResearch, setUseResearch] = useState(false);
  const [qualityMode, setQualityMode] = useState(false);
  const [submitting, setSubmitting] = useState(false);
  const [generateError, setGenerateError] = useState<string | null>(null);
  const [genCount, setGenCount] = useState<number | null>(null);
  const GEN_LIMIT = 8;

  // Job progress (inline) — restore from localStorage on mount
  const [activeJobId, setActiveJobId] = useState<string | null>(null);
  const [jobStatus, setJobStatus] = useState<string | null>(null);
  const [jobVideoId, setJobVideoId] = useState<string | null>(null);
  const [jobError, setJobError] = useState<string | null>(null);
  const pollRef = useRef<ReturnType<typeof setInterval> | null>(null);

  // Track mount to prevent SSR → hydration animation flash
  useEffect(() => { setMounted(true); }, []);

  // Fetch available tags
  useEffect(() => {
    fetchTags().then(setAvailableTags).catch(() => {});
  }, []);

  // Read tag from URL on mount
  useEffect(() => {
    const params = new URLSearchParams(window.location.search);
    const tagParam = params.get("tag");
    if (tagParam) {
      setSelectedTag(tagParam);
      setTab("community");
    }
  }, []);

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

  // Fetch generation count for current month
  useEffect(() => {
    if (!user || !supabaseRef.current) return;
    (async () => {
      try {
        const now = new Date();
        const monthStart = new Date(now.getFullYear(), now.getMonth(), 1).toISOString();
        const { count } = await supabaseRef.current!
          .from("generation_jobs")
          .select("id", { count: "exact", head: true })
          .eq("user_id", user.id)
          .gte("created_at", monthStart);
        setGenCount(count || 0);
      } catch {
        // ignore
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

  // Default to "My Videos" tab once auth is resolved
  useEffect(() => {
    if (tabInitialized) return;
    if (user) {
      setTab("my_videos");
      setTabInitialized(true);
    } else if (user === null && supabaseRef.current) {
      setTabInitialized(true);
    }
  }, [user, tabInitialized]);

  const PAGE_SIZE = 12;

  // Load videos (initial or next page)
  const loadVideos = useCallback(async (pageNum: number, append = false) => {
    if (tab === "my_videos") {
      if (!supabaseRef.current || !user) {
        setVideos([]);
        setInitialLoad(false);
        return;
      }
      if (!append) setInitialLoad(true);
      try {
        let query = supabaseRef.current
          .from("videos")
          .select("id, slug, title, topic, tags, thumbnail_url, video_url, view_count, narration_text, created_at, duration_profile")
          .eq("user_id", user.id)
          .order("created_at", { ascending: false });
        if (selectedTag) {
          query = query.contains("tags", JSON.stringify([selectedTag]));
        }
        const { data } = await query;
        let filtered = (data || []).map((v: Record<string, unknown>) => ({ ...v, like_count: 0 } as Video));
        // Client-side search filter for My Videos
        if (search) {
          const words = search.toLowerCase().split(/\s+/).filter(Boolean);
          filtered = filtered.filter((v) =>
            words.some((w) => v.title.toLowerCase().includes(w) || v.topic.toLowerCase().includes(w))
          );
        }
        setVideos(filtered);
        // Track total my videos count (before search filter)
        setMyVideoCount((data || []).length);
        setHasMore(false); // My Videos loads all at once
      } catch {
        setVideos([]);
      } finally {
        setInitialLoad(false);
      }
      return;
    }

    if (!append) setInitialLoad(true);
    else setLoadingMore(true);

    try {
      const data = await fetchVideos({
        search: search || undefined,
        sort: communitySort,
        tag: selectedTag || undefined,
        page: pageNum,
        limit: PAGE_SIZE,
      });
      if (append) {
        setVideos((prev) => [...prev, ...data.videos]);
      } else {
        setVideos(data.videos);
      }
      setCommunityTotal(data.total);
      setHasMore(data.videos.length === PAGE_SIZE && (data.total > pageNum * PAGE_SIZE));
    } catch {
      if (!append) setVideos([]);
    } finally {
      setInitialLoad(false);
      setLoadingMore(false);
    }
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [search, tab, communitySort, selectedTag, user]);

  // Reset and load page 1 when filters change
  useEffect(() => {
    setVideos([]);
    setPage(1);
    setHasMore(true);
    loadVideos(1, false);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [search, tab, communitySort, selectedTag]);

  // Infinite scroll observer
  useEffect(() => {
    if (!loadMoreRef.current) return;
    const observer = new IntersectionObserver(
      (entries) => {
        if (entries[0].isIntersecting && hasMore && !loadingMore && !initialLoad) {
          const nextPage = page + 1;
          setPage(nextPage);
          loadVideos(nextPage, true);
        }
      },
      { threshold: 0.1 }
    );
    observer.observe(loadMoreRef.current);
    return () => observer.disconnect();
  }, [hasMore, loadingMore, initialLoad, page, loadVideos]);

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

    // Validate input based on mode
    if (inputMode === "topic" && !topic.trim()) return;
    if (inputMode === "paper" && !paperFile) return;

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

      let job_id: string;
      if (inputMode === "paper" && paperFile) {
        const result = await generateFromPaper(paperFile, duration, session.access_token);
        job_id = result.job_id;
      } else {
        const result = await generateVideo(topic, duration, session.access_token, useResearch, qualityMode);
        job_id = result.job_id;
      }

      localStorage.setItem("curiso_active_job", job_id);
      setActiveJobId(job_id);
      setJobStatus("planning");
      setTopic("");
      setPaperFile(null);
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
            <motion.div
              className="mt-1.5 flex items-baseline justify-between gap-4"
              initial={{ opacity: 0 }}
              animate={mounted ? { opacity: 1 } : { opacity: 0 }}
              transition={{ delay: 0.3, duration: 0.5 }}
            >
              <p className="text-sm text-[var(--color-muted)]">
                Enter any topic or upload a research paper, and let AI generate an animated visual explanation for you.
              </p>
              <span className="hidden shrink-0 text-xs text-[var(--color-muted)] sm:inline">
                Unlimited generations. 100% free!
              </span>
            </motion.div>
          </div>

          <motion.form
            onSubmit={handleGenerate}
            initial={{ opacity: 0, y: 12 }}
            animate={mounted ? { opacity: 1, y: 0 } : { opacity: 0, y: 12 }}
            transition={{ delay: 0.15, duration: 0.5, ease: "easeOut" }}
          >
            <div className="rounded-xl border border-[var(--color-border)] bg-[var(--color-surface)] p-4 shadow-[0_1px_3px_rgba(0,0,0,0.04)] transition-shadow focus-within:shadow-[0_2px_8px_rgba(0,0,0,0.06)]">
              <div className="mb-3 flex gap-1">
                <button
                  type="button"
                  onClick={() => setInputMode("topic")}
                  className={`rounded-md px-3 py-1 text-xs transition-colors ${
                    inputMode === "topic"
                      ? "bg-[var(--color-surface-hover)] font-medium text-[var(--color-foreground)]"
                      : "text-[var(--color-muted)] hover:text-[var(--color-foreground)]"
                  }`}
                >
                  Generate from a topic
                </button>
                {user?.email === "duggalr42@gmail.com" ? (
                  <button
                    type="button"
                    onClick={() => setInputMode("paper")}
                    className={`rounded-md px-3 py-1 text-xs transition-colors ${
                      inputMode === "paper"
                        ? "bg-[var(--color-surface-hover)] font-medium text-[var(--color-foreground)]"
                        : "text-[var(--color-muted)] hover:text-[var(--color-foreground)]"
                    }`}
                  >
                    Generate from a research paper
                  </button>
                ) : (
                  <span className="rounded-md px-3 py-1 text-xs text-[var(--color-border)] cursor-not-allowed">
                    Research paper (coming soon)
                  </span>
                )}
              </div>
              {inputMode === "paper" ? (
                <div
                  className="flex flex-col items-center justify-center rounded-lg border-2 border-dashed border-[var(--color-border)] p-6 transition-colors hover:border-[var(--color-muted)]"
                  onDragOver={(e) => { e.preventDefault(); e.stopPropagation(); }}
                  onDrop={(e) => {
                    e.preventDefault();
                    e.stopPropagation();
                    const file = e.dataTransfer.files[0];
                    if (file?.type === "application/pdf") setPaperFile(file);
                  }}
                >
                  {paperFile ? (
                    <div className="flex items-center gap-3">
                      <svg xmlns="http://www.w3.org/2000/svg" className="h-5 w-5 text-[var(--color-foreground)]" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth="2">
                        <path strokeLinecap="round" strokeLinejoin="round" d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
                      </svg>
                      <div>
                        <p className="text-sm font-medium text-[var(--color-foreground)]">{paperFile.name}</p>
                        <p className="text-xs text-[var(--color-muted)]">{(paperFile.size / 1024 / 1024).toFixed(1)} MB</p>
                      </div>
                      <button
                        type="button"
                        onClick={() => setPaperFile(null)}
                        className="ml-2 text-xs text-[var(--color-muted)] hover:text-[var(--color-foreground)]"
                      >
                        Remove
                      </button>
                    </div>
                  ) : (
                    <>
                      <svg xmlns="http://www.w3.org/2000/svg" className="mb-2 h-8 w-8 text-[var(--color-muted)]" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth="1.5">
                        <path strokeLinecap="round" strokeLinejoin="round" d="M7 16a4 4 0 01-.88-7.903A5 5 0 1115.9 6L16 6a5 5 0 011 9.9M15 13l-3-3m0 0l-3 3m3-3v12" />
                      </svg>
                      <p className="text-sm text-[var(--color-muted)]">Drop a PDF here or</p>
                      <label className="mt-1 cursor-pointer text-sm font-medium text-[var(--color-foreground)] underline">
                        browse files
                        <input
                          type="file"
                          accept=".pdf,application/pdf"
                          className="hidden"
                          onChange={(e) => {
                            const file = e.target.files?.[0];
                            if (file) setPaperFile(file);
                          }}
                        />
                      </label>
                      <p className="mt-2 text-[10px] text-[var(--color-muted)]">PDF only, max 20MB</p>
                    </>
                  )}
                </div>
              ) : (
                <>
                  <textarea
                    value={topic}
                    onChange={(e) => setTopic(e.target.value)}
                    placeholder="What are you curious about?"
                    rows={2}
                    className="w-full resize-none bg-transparent text-sm text-[var(--color-foreground)] placeholder-[var(--color-muted)] outline-none"
                  />
                  {!topic.trim() && suggestedTopics.length > 0 && (
                    <div className="flex flex-wrap items-center gap-1.5 pt-1 pb-2">
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
                      <button
                        type="button"
                        onClick={refreshTopics}
                        className="rounded-full p-1.5 text-[var(--color-muted)] transition-colors hover:text-[var(--color-foreground)]"
                        title="Show different topics"
                      >
                        <svg xmlns="http://www.w3.org/2000/svg" className="h-3.5 w-3.5" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth="2">
                          <path strokeLinecap="round" strokeLinejoin="round" d="M4 4v5h5M20 20v-5h-5M5.1 15A7.002 7.002 0 0019 12M18.9 9A7.002 7.002 0 005 12" />
                        </svg>
                      </button>
                    </div>
                  )}
                </>
              )}
              <div className="flex items-center justify-between pt-2">
                {inputMode === "paper" ? (
                  <p className="text-xs text-[var(--color-muted)]">
                    Generates a 5-10 minute video using highest quality mode
                  </p>
                ) : (
                <div className="flex items-center gap-3">
                  <div className="flex gap-1">
                    {["short", "medium", "long"].map((d) => (
                      <button
                        key={d}
                        type="button"
                        disabled={d === "long"}
                        onClick={() => d !== "long" && setDuration(d)}
                        className={`rounded-md px-3 py-1 text-xs capitalize transition-colors ${
                          d === "long"
                            ? "cursor-not-allowed text-[var(--color-border)]"
                            : duration === d
                              ? "bg-[var(--color-surface-hover)] font-medium text-[var(--color-foreground)]"
                              : "text-[var(--color-muted)] hover:text-[var(--color-foreground)]"
                        }`}
                        title={d === "long" ? "Coming soon" : ""}
                      >
                        {d}{d === "long" ? " (soon)" : ""}
                      </button>
                    ))}
                  </div>

                  <div className="h-4 w-px bg-[var(--color-border)]" />

                  <button
                    type="button"
                    onClick={() => setUseResearch(!useResearch)}
                    className="flex items-center gap-2 text-xs text-[var(--color-muted)]"
                  >
                    <span
                      className={`relative inline-flex h-4 w-7 shrink-0 items-center rounded-full transition-colors ${
                        useResearch ? "bg-[var(--color-foreground)]" : "bg-[var(--color-border)]"
                      }`}
                    >
                      <span
                        className={`inline-block h-3 w-3 rounded-full bg-[var(--color-background)] transition-transform ${
                          useResearch ? "translate-x-3.5" : "translate-x-0.5"
                        }`}
                      />
                    </span>
                    <span className={useResearch ? "text-[var(--color-foreground)]" : ""}>
                      Web search
                    </span>
                    <span className="hidden text-[10px] sm:inline">
                      (for niche topics, research, or recent events)
                    </span>
                  </button>

                  <div className="h-4 w-px bg-[var(--color-border)]" />

                  <button
                    type="button"
                    onClick={() => setQualityMode(!qualityMode)}
                    className="flex items-center gap-2 text-xs text-[var(--color-muted)]"
                  >
                    <span
                      className={`relative inline-flex h-4 w-7 shrink-0 items-center rounded-full transition-colors ${
                        qualityMode ? "bg-[var(--color-foreground)]" : "bg-[var(--color-border)]"
                      }`}
                    >
                      <span
                        className={`inline-block h-3 w-3 rounded-full bg-[var(--color-background)] transition-transform ${
                          qualityMode ? "translate-x-3.5" : "translate-x-0.5"
                        }`}
                      />
                    </span>
                    <span className={qualityMode ? "text-[var(--color-foreground)]" : ""}>
                      Quality mode
                    </span>
                    <span className="hidden text-[10px] sm:inline">
                      (slower, higher quality)
                    </span>
                  </button>
                </div>
                )}
                <button
                  type="submit"
                  disabled={submitting || (inputMode === "topic" ? !topic.trim() : !paperFile) || (!!activeJobId && jobStatus !== "completed" && jobStatus !== "failed")}
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
                  This usually takes around 5 minutes. You can refresh or leave this page. We'll email you once your video is complete.
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
          <div className="flex items-center justify-between">
            <div className="flex gap-1 text-sm">
              {user && (
                <button
                  onClick={() => setTab("my_videos")}
                  className={`rounded-lg px-3 py-1.5 transition-colors ${
                    tab === "my_videos"
                      ? "bg-[var(--color-foreground)] font-medium text-[var(--color-background)]"
                      : "text-[var(--color-muted)] hover:bg-[var(--color-surface-hover)] hover:text-[var(--color-foreground)]"
                  }`}
                >
                  My Videos{myVideoCount !== null ? ` (${myVideoCount})` : ""}
                </button>
              )}
              <button
                onClick={() => setTab("community")}
                className={`rounded-lg px-3 py-1.5 transition-colors ${
                  tab === "community"
                    ? "bg-[var(--color-foreground)] font-medium text-[var(--color-background)]"
                    : "text-[var(--color-muted)] hover:bg-[var(--color-surface-hover)] hover:text-[var(--color-foreground)]"
                }`}
              >
                Community{communityTotal !== null ? ` (${communityTotal})` : ""}
              </button>

              <button
                onClick={() => {
                  if (videos.length > 0) {
                    const random = videos[Math.floor(Math.random() * videos.length)];
                    router.push(`/video/${random.slug || random.id}`);
                  }
                }}
                className="flex items-center gap-1.5 rounded-lg px-3 py-1.5 text-sm text-[var(--color-muted)] transition-colors hover:bg-[var(--color-surface-hover)] hover:text-[var(--color-foreground)]"
              >
                <Dice5 className="h-3.5 w-3.5" />
                <span className="hidden sm:inline">Random video</span>
              </button>
            </div>

            <div className="flex items-center gap-3">
              <input
                type="text"
                onChange={(e) => handleSearchInput(e.target.value)}
                placeholder="Search..."
                className="w-36 rounded-lg border border-[var(--color-border)] bg-[var(--color-surface)] px-3 py-1.5 text-xs text-[var(--color-foreground)] placeholder-[var(--color-muted)] outline-none transition-colors focus:border-[var(--color-muted)]"
              />
              {tab === "community" && (
                <select
                  value={communitySort}
                  onChange={(e) => setCommunitySort(e.target.value as "recent" | "most_liked")}
                  className="rounded-lg border border-[var(--color-border)] bg-[var(--color-surface)] px-2.5 py-1.5 text-xs text-[var(--color-muted)] outline-none transition-colors focus:border-[var(--color-muted)]"
                >
                  <option value="recent">Recent</option>
                  <option value="most_viewed">Most Viewed</option>
                </select>
              )}
            </div>
          </div>

          {/* Tag filter pills — single row, horizontally scrollable with arrows */}
          {availableTags.length > 0 && (
            <div className="relative mt-3 flex items-center gap-1">
              {/* Left arrow */}
              <button
                onClick={() => {
                  const el = document.getElementById("tag-scroll");
                  if (el) el.scrollBy({ left: -200, behavior: "smooth" });
                }}
                className="shrink-0 rounded-full p-1 text-[var(--color-muted)] transition-colors hover:bg-[var(--color-surface-hover)] hover:text-[var(--color-foreground)]"
              >
                <svg xmlns="http://www.w3.org/2000/svg" className="h-4 w-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth="2">
                  <path strokeLinecap="round" strokeLinejoin="round" d="M15 19l-7-7 7-7" />
                </svg>
              </button>

              <div className="relative min-w-0 flex-1">
                <div id="tag-scroll" className="no-scrollbar flex gap-1.5 overflow-x-auto pb-1" style={{ scrollbarWidth: "none", msOverflowStyle: "none" }}>
                  <button
                    onClick={() => setSelectedTag("")}
                    className={`shrink-0 rounded-full px-3 py-1 text-xs transition-colors ${
                      !selectedTag
                        ? "bg-[var(--color-foreground)] text-[var(--color-background)]"
                        : "border border-[var(--color-border)] text-[var(--color-muted)] hover:border-[var(--color-muted)] hover:text-[var(--color-foreground)]"
                    }`}
                  >
                    All
                  </button>
                  {availableTags.map(({ tag, count }) => (
                    <button
                      key={tag}
                      onClick={() => setSelectedTag(selectedTag === tag ? "" : tag)}
                      className={`shrink-0 rounded-full px-3 py-1 text-xs whitespace-nowrap transition-colors ${
                        selectedTag === tag
                          ? "bg-[var(--color-foreground)] text-[var(--color-background)]"
                          : "border border-[var(--color-border)] text-[var(--color-muted)] hover:border-[var(--color-muted)] hover:text-[var(--color-foreground)]"
                      }`}
                    >
                      {tag}
                      <span className="ml-1 opacity-50">{count}</span>
                    </button>
                  ))}
                </div>
                {/* Fade hints */}
                <div className="pointer-events-none absolute left-0 top-0 bottom-1 w-6 bg-gradient-to-r from-[var(--color-background)] to-transparent" />
                <div className="pointer-events-none absolute right-0 top-0 bottom-1 w-6 bg-gradient-to-l from-[var(--color-background)] to-transparent" />
              </div>

              {/* Right arrow */}
              <button
                onClick={() => {
                  const el = document.getElementById("tag-scroll");
                  if (el) el.scrollBy({ left: 200, behavior: "smooth" });
                }}
                className="shrink-0 rounded-full p-1 text-[var(--color-muted)] transition-colors hover:bg-[var(--color-surface-hover)] hover:text-[var(--color-foreground)]"
              >
                <svg xmlns="http://www.w3.org/2000/svg" className="h-4 w-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth="2">
                  <path strokeLinecap="round" strokeLinejoin="round" d="M9 5l7 7-7 7" />
                </svg>
              </button>
            </div>
          )}
        </motion.div>

        {/* Video Grid */}
        <div className="relative min-h-[200px]">
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
              {tab === "my_videos" ? (
                <div>
                  <p className="mb-2 text-sm font-medium text-[var(--color-foreground)]">
                    You haven't generated any videos yet.
                  </p>
                  <p className="mb-5 text-xs text-[var(--color-muted)]">
                    Enter a topic above and create your first video. It's free and takes about 5 minutes.
                  </p>
                  <button
                    onClick={() => window.scrollTo({ top: 0, behavior: "smooth" })}
                    className="inline-block rounded-lg bg-[var(--color-foreground)] px-5 py-2 text-sm font-medium text-[var(--color-background)] transition-opacity hover:opacity-80"
                  >
                    Generate your first video
                  </button>
                </div>
              ) : (
                <p className="text-sm text-[var(--color-muted)]">
                  {search ? `No videos found for "${search}"` : "No videos yet. Generate one above!"}
                </p>
              )}
            </motion.div>
          ) : (
            <>
              <div className="grid grid-cols-1 gap-5 sm:grid-cols-2 lg:grid-cols-3">
                {videos.map((video) => (
                  <motion.div
                    key={video.id}
                    className="h-full"
                    initial={{ opacity: 0 }}
                    animate={{ opacity: 1 }}
                    transition={{ duration: 0.3 }}
                    layout
                  >
                    <VideoCard video={video} />
                  </motion.div>
                ))}

                {/* Skeleton placeholders while loading more */}
                {loadingMore && Array.from({ length: 3 }).map((_, i) => (
                  <div key={`skeleton-${i}`} className="animate-pulse overflow-hidden rounded-lg border border-[var(--color-border)] bg-[var(--color-surface)]">
                    <div className="aspect-video bg-[var(--color-surface-hover)]" />
                    <div className="space-y-2 p-3.5">
                      <div className="h-3.5 w-3/4 rounded bg-[var(--color-surface-hover)]" />
                      <div className="h-3 w-1/2 rounded bg-[var(--color-surface-hover)]" />
                    </div>
                  </div>
                ))}
              </div>

              {/* Infinite scroll trigger */}
              <div ref={loadMoreRef} className="py-6">
                {!hasMore && videos.length > PAGE_SIZE && (
                  <p className="text-center text-xs text-[var(--color-muted)]">You've seen all videos</p>
                )}
              </div>
            </>
          )}
        </div>
      </div>

      <AuthModal isOpen={authModal} onClose={() => setAuthModal(false)} initialMode={authMode} />
    </>
  );
}
