"use client";

import { useEffect, useState, useRef, useCallback } from "react";
import Link from "next/link";
import { Youtube, Twitter } from "lucide-react";
import type { User } from "@supabase/supabase-js";
import type { SupabaseClient } from "@supabase/supabase-js";
import AuthModal from "./AuthModal";

const FREE_GENERATIONS_PER_MONTH = 8;

interface UserVideo {
  id: string;
  title: string;
  topic: string;
  thumbnail_url: string | null;
  created_at: string;
}

export default function Navbar() {
  const [user, setUser] = useState<User | null>(null);
  const [authModal, setAuthModal] = useState(false);
  const [authMode, setAuthMode] = useState<"signin" | "signup">("signin");
  const [profileOpen, setProfileOpen] = useState(false);
  const [userVideos, setUserVideos] = useState<UserVideo[]>([]);
  const [genCount, setGenCount] = useState(0);
  const [loadingProfile, setLoadingProfile] = useState(false);
  const supabaseRef = useRef<SupabaseClient | null>(null);
  const dropdownRef = useRef<HTMLDivElement>(null);

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
        // Supabase not configured yet
      }
    }

    init();
    return () => {
      subscription?.unsubscribe();
    };
  }, []);

  // Close dropdown on outside click
  useEffect(() => {
    function handleClick(e: MouseEvent) {
      if (dropdownRef.current && !dropdownRef.current.contains(e.target as Node)) {
        setProfileOpen(false);
      }
    }
    if (profileOpen) document.addEventListener("mousedown", handleClick);
    return () => document.removeEventListener("mousedown", handleClick);
  }, [profileOpen]);

  const loadProfileData = useCallback(async () => {
    if (!supabaseRef.current || !user) return;
    setLoadingProfile(true);
    try {
      const supabase = supabaseRef.current;

      // Fetch user's videos
      const { data: videos } = await supabase
        .from("videos")
        .select("id, title, topic, thumbnail_url, created_at")
        .eq("user_id", user.id)
        .order("created_at", { ascending: false })
        .limit(5);

      setUserVideos(videos || []);

      // Count generations this month
      const now = new Date();
      const monthStart = new Date(now.getFullYear(), now.getMonth(), 1).toISOString();
      const { count } = await supabase
        .from("generation_jobs")
        .select("id", { count: "exact", head: true })
        .eq("user_id", user.id)
        .gte("created_at", monthStart);

      setGenCount(count || 0);
    } catch {
      // Supabase tables may not exist yet
    } finally {
      setLoadingProfile(false);
    }
  }, [user]);

  const toggleProfile = () => {
    const opening = !profileOpen;
    setProfileOpen(opening);
    if (opening) loadProfileData();
  };

  const handleSignOut = async () => {
    if (supabaseRef.current) {
      await supabaseRef.current.auth.signOut();
      setUser(null);
      setProfileOpen(false);
    }
  };

  const remaining = Math.max(0, FREE_GENERATIONS_PER_MONTH - genCount);

  return (
    <>
      <nav className="py-4">
        <div className="mx-auto flex max-w-6xl items-center justify-between px-6">
          <Link
            href="/"
            className="text-lg text-[var(--color-foreground)]"
            style={{ fontFamily: "var(--font-serif)" }}
          >
            Curiso
          </Link>

          <div className="flex items-center gap-4">
            <a
              href="https://youtube.com"
              target="_blank"
              rel="noopener noreferrer"
              className="text-[var(--color-muted)] transition-colors hover:text-[var(--color-foreground)]"
            >
              <Youtube size={18} />
            </a>
            <a
              href="https://x.com"
              target="_blank"
              rel="noopener noreferrer"
              className="text-[var(--color-muted)] transition-colors hover:text-[var(--color-foreground)]"
            >
              <Twitter size={16} />
            </a>

            <div className="mx-1 h-4 w-px bg-[var(--color-border)]" />

            {user ? (
              <div className="relative" ref={dropdownRef}>
                <button
                  onClick={toggleProfile}
                  className="flex h-7 w-7 items-center justify-center rounded-full bg-[var(--color-surface-hover)] text-xs font-medium text-[var(--color-muted)] transition-colors hover:bg-[var(--color-border)]"
                >
                  {user.email?.[0]?.toUpperCase() || "U"}
                </button>

                {profileOpen && (
                  <div className="absolute right-0 top-full z-50 mt-2 w-80 overflow-hidden rounded-xl border border-[var(--color-border)] bg-white shadow-lg">
                    {/* User info */}
                    <div className="border-b border-[var(--color-border)] px-4 py-3">
                      <p className="text-sm font-medium text-[var(--color-foreground)]">
                        {user.email}
                      </p>
                      <div className="mt-2 flex items-center justify-between">
                        <span className="text-xs text-[var(--color-muted)]">
                          Free generations this month
                        </span>
                        <span className="text-xs font-medium text-[var(--color-foreground)]">
                          {remaining} / {FREE_GENERATIONS_PER_MONTH}
                        </span>
                      </div>
                      <div className="mt-1.5 h-1.5 w-full overflow-hidden rounded-full bg-[var(--color-surface-hover)]">
                        <div
                          className="h-full rounded-full bg-[var(--color-foreground)] transition-all"
                          style={{ width: `${(remaining / FREE_GENERATIONS_PER_MONTH) * 100}%` }}
                        />
                      </div>
                      <p className="mt-2 text-[10px] text-[var(--color-muted)]">
                        More generations per month coming soon.
                      </p>
                    </div>

                    {/* User's videos */}
                    <div className="px-4 py-3">
                      <p className="mb-2 text-xs font-medium text-[var(--color-muted)] uppercase tracking-wide">
                        Your videos
                      </p>
                      {loadingProfile ? (
                        <div className="flex justify-center py-4">
                          <div className="h-4 w-4 animate-spin rounded-full border-2 border-[var(--color-border)] border-t-[var(--color-foreground)]" />
                        </div>
                      ) : userVideos.length === 0 ? (
                        <p className="py-3 text-center text-xs text-[var(--color-muted)]">
                          No videos yet. Generate your first one!
                        </p>
                      ) : (
                        <div className="space-y-1">
                          {userVideos.map((video) => (
                            <Link
                              key={video.id}
                              href={`/video/${video.id}`}
                              onClick={() => setProfileOpen(false)}
                              className="flex items-center gap-3 rounded-lg px-2 py-1.5 transition-colors hover:bg-[var(--color-surface-hover)]"
                            >
                              {video.thumbnail_url ? (
                                <img
                                  src={video.thumbnail_url}
                                  alt=""
                                  className="h-8 w-14 rounded object-cover"
                                />
                              ) : (
                                <div className="flex h-8 w-14 items-center justify-center rounded bg-[var(--color-surface-hover)]">
                                  <svg xmlns="http://www.w3.org/2000/svg" className="h-3 w-3 text-[var(--color-muted)]" viewBox="0 0 20 20" fill="currentColor">
                                    <path d="M6.5 5.5v9l7-4.5-7-4.5z" />
                                  </svg>
                                </div>
                              )}
                              <div className="min-w-0 flex-1">
                                <p className="truncate text-xs font-medium text-[var(--color-foreground)]">
                                  {video.title || video.topic}
                                </p>
                                <p className="text-[10px] text-[var(--color-muted)]">
                                  {new Date(video.created_at).toLocaleDateString("en-US", { month: "short", day: "numeric" })}
                                </p>
                              </div>
                            </Link>
                          ))}
                        </div>
                      )}
                    </div>

                    {/* Sign out */}
                    <div className="border-t border-[var(--color-border)] px-4 py-2">
                      <button
                        onClick={handleSignOut}
                        className="w-full rounded-lg py-1.5 text-left text-xs text-[var(--color-muted)] transition-colors hover:text-[var(--color-foreground)]"
                      >
                        Sign out
                      </button>
                    </div>
                  </div>
                )}
              </div>
            ) : (
              <>
                <button
                  onClick={() => { setAuthMode("signin"); setAuthModal(true); }}
                  className="text-sm text-[var(--color-muted)] transition-colors hover:text-[var(--color-foreground)]"
                >
                  Sign in
                </button>
                <button
                  onClick={() => { setAuthMode("signup"); setAuthModal(true); }}
                  className="rounded-lg bg-[var(--color-foreground)] px-3.5 py-1.5 text-sm font-medium text-[var(--color-background)] transition-opacity hover:opacity-80"
                >
                  Sign up
                </button>
              </>
            )}
          </div>
        </div>
      </nav>

      <AuthModal isOpen={authModal} onClose={() => setAuthModal(false)} initialMode={authMode} />
    </>
  );
}
