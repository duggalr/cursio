"use client";

import { useEffect, useState, useCallback, useRef } from "react";
import { useRouter } from "next/navigation";
import { motion } from "motion/react";
import VideoCard from "@/components/VideoCard";
import AuthModal from "@/components/AuthModal";
import { Dice5 } from "lucide-react";
import { fetchVideos, fetchTags, type Video, type TagWithCount } from "@/lib/api";
import type { User, SupabaseClient } from "@supabase/supabase-js";

export default function HomePage() {
  const [mounted, setMounted] = useState(false);
  const router = useRouter();
  const [videos, setVideos] = useState<Video[]>([]);
  const [myVideoCount, setMyVideoCount] = useState<number | null>(null);
  const [communityTotal, setCommunityTotal] = useState<number | null>(null);
  const [initialLoad, setInitialLoad] = useState(true);
  const [loadingMore, setLoadingMore] = useState(false);
  const [hasMore, setHasMore] = useState(true);
  const [page, setPage] = useState(1);
  const [search, setSearch] = useState("");
  const loadMoreRef = useRef<HTMLDivElement | null>(null);
  const [tab, setTab] = useState<"picks" | "my_videos" | "community">("picks");
  const [picksTotal, setPicksTotal] = useState<number | null>(null);
  const [communitySort, setCommunitySort] = useState<"recent" | "most_liked">("recent");
  const [availableTags, setAvailableTags] = useState<TagWithCount[]>([]);
  const [selectedTag, setSelectedTag] = useState<string>("");
  const [tabInitialized, setTabInitialized] = useState(false);
  const debounceRef = useRef<ReturnType<typeof setTimeout> | null>(null);

  // Auth state
  const [user, setUser] = useState<User | null>(null);
  const [authModal, setAuthModal] = useState(false);
  const [authMode] = useState<"signin" | "signup">("signup");
  const supabaseRef = useRef<SupabaseClient | null>(null);

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

  // Default to "Curiso Picks" tab (always)
  useEffect(() => {
    if (tabInitialized) return;
    if (user) {
      setTab("picks");
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
          query = query.contains("tags", [selectedTag]);
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
        sort: tab === "picks" ? "most_viewed" : communitySort,
        tag: selectedTag || undefined,
        featured: tab === "picks" ? true : undefined,
        page: pageNum,
        limit: PAGE_SIZE,
      });
      if (append) {
        setVideos((prev) => [...prev, ...data.videos]);
      } else {
        setVideos(data.videos);
      }
      if (tab === "picks") {
        setPicksTotal(data.total);
      } else {
        setCommunityTotal(data.total);
      }
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

  return (
    <>
      <div className="mx-auto max-w-6xl px-6 pt-8 pb-16">
        {/* Header */}
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
                Browse animated visual explanations for any topic.
              </p>
            </motion.div>
          </div>

          <motion.div
            className="rounded-xl border border-[var(--color-border)] bg-[var(--color-surface)] px-4 py-3"
            initial={{ opacity: 0, y: 12 }}
            animate={mounted ? { opacity: 1, y: 0 } : { opacity: 0, y: 12 }}
            transition={{ delay: 0.15, duration: 0.5, ease: "easeOut" }}
          >
            <p className="text-sm text-[var(--color-foreground)]">
              Generation is temporarily paused.
            </p>
            <p className="mt-1 text-xs text-[var(--color-muted)]">
              We&apos;re working on infrastructure improvements. Explore the existing videos below in the meantime.
            </p>
          </motion.div>
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
              <button
                onClick={() => setTab("picks")}
                className={`rounded-lg px-3 py-1.5 transition-colors ${
                  tab === "picks"
                    ? "bg-[var(--color-foreground)] font-medium text-[var(--color-background)]"
                    : "text-[var(--color-muted)] hover:bg-[var(--color-surface-hover)] hover:text-[var(--color-foreground)]"
                }`}
              >
                Curiso Picks{picksTotal !== null ? ` (${picksTotal})` : ""}
              </button>
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
              {tab === "picks" && picksTotal !== null && picksTotal > 0 && (
                <span className="text-xs text-[var(--color-muted)]">
                  Vetted by the Curiso team
                </span>
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
                <p className="text-sm text-[var(--color-muted)]">
                  You haven&apos;t generated any videos yet.
                </p>
              ) : tab === "picks" ? (
                <p className="text-sm text-[var(--color-muted)]">
                  {search ? `No picks found for "${search}"` : "Curated picks coming soon!"}
                </p>
              ) : (
                <p className="text-sm text-[var(--color-muted)]">
                  {search ? `No videos found for "${search}"` : "No videos yet."}
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
                  <p className="text-center text-xs text-[var(--color-muted)]">You&apos;ve seen all videos</p>
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
