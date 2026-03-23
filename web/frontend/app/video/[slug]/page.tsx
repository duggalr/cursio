"use client";

import { useEffect, useState } from "react";
import { useParams } from "next/navigation";
import Link from "next/link";
import { motion } from "motion/react";
import { fetchVideo, likeVideo, unlikeVideo, checkIfLiked, type Video } from "@/lib/api";
import AuthModal from "@/components/AuthModal";

function parseTags(tags: unknown): string[] {
  if (Array.isArray(tags)) return tags;
  if (typeof tags === "string") {
    try { return JSON.parse(tags); } catch { return []; }
  }
  return [];
}

export default function VideoPage() {
  const params = useParams();
  const slug = params.slug as string;

  const [video, setVideo] = useState<Video | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [narrationOpen, setNarrationOpen] = useState(false);
  const [copied, setCopied] = useState(false);

  const [liked, setLiked] = useState(false);
  const [likeCount, setLikeCount] = useState(0);
  const [likeLoading, setLikeLoading] = useState(false);
  const [authModal, setAuthModal] = useState(false);

  useEffect(() => {
    async function load() {
      try {
        const data = await fetchVideo(slug);
        setVideo(data);
        setLikeCount(data.like_count || 0);

        const { createClient } = await import("@/lib/supabase");
        const supabase = createClient();
        const { data: { session } } = await supabase.auth.getSession();
        if (session?.access_token) {
          const isLiked = await checkIfLiked(data.id, session.access_token);
          setLiked(isLiked);
        }
      } catch (err) {
        setError(err instanceof Error ? err.message : "Failed to load video");
      } finally {
        setLoading(false);
      }
    }
    load();
  }, [slug]);

  const handleLike = async () => {
    if (!video) return;
    const { createClient } = await import("@/lib/supabase");
    const supabase = createClient();
    const { data: { session } } = await supabase.auth.getSession();

    if (!session?.access_token) {
      setAuthModal(true);
      return;
    }

    setLikeLoading(true);
    try {
      if (liked) {
        await unlikeVideo(video.id, session.access_token);
        setLiked(false);
        setLikeCount((c) => Math.max(0, c - 1));
      } else {
        await likeVideo(video.id, session.access_token);
        setLiked(true);
        setLikeCount((c) => c + 1);
      }
    } catch {
      // silently handle
    } finally {
      setLikeLoading(false);
    }
  };

  const handleShare = async () => {
    const url = window.location.href;
    try {
      await navigator.clipboard.writeText(url);
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
    } catch {
      const input = document.createElement("input");
      input.value = url;
      document.body.appendChild(input);
      input.select();
      document.execCommand("copy");
      document.body.removeChild(input);
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
    }
  };

  if (loading) {
    return (
      <div className="flex min-h-[60vh] items-center justify-center">
        <motion.div
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          transition={{ duration: 0.3 }}
          className="flex flex-col items-center gap-3"
        >
          <div className="h-6 w-6 animate-spin rounded-full border-2 border-[var(--color-border)] border-t-[var(--color-foreground)]" />
          <span className="text-xs text-[var(--color-muted)]">Loading video...</span>
        </motion.div>
      </div>
    );
  }

  if (error || !video) {
    return (
      <div className="flex min-h-[60vh] flex-col items-center justify-center px-6 text-center">
        <h2 className="mb-2 text-lg font-medium text-[var(--color-foreground)]">Video not found</h2>
        <p className="mb-6 text-sm text-[var(--color-muted)]">{error || "This video doesn't exist or has been removed."}</p>
        <Link href="/" className="text-sm text-[var(--color-foreground)] underline">
          Back to gallery
        </Link>
      </div>
    );
  }

  return (
    <div className="mx-auto max-w-4xl px-6 py-8">
      <Link href="/" className="mb-4 inline-flex items-center text-sm text-[var(--color-muted)] hover:text-[var(--color-foreground)]">
        &larr; Back to gallery
      </Link>

      {/* Video Player */}
      <motion.div
        className="overflow-hidden rounded-lg bg-black"
        initial={{ opacity: 0, y: 12 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.5, ease: "easeOut" }}
      >
        {video.video_url ? (
          <video
            controls
            className="aspect-video w-full"
            poster={video.thumbnail_url || undefined}
          >
            <source src={video.video_url} type="video/mp4" />
          </video>
        ) : (
          <div className="flex aspect-video items-center justify-center bg-[var(--color-surface-hover)]">
            <p className="text-sm text-[var(--color-muted)]">Video processing...</p>
          </div>
        )}
      </motion.div>

      {/* Video Info */}
      <motion.div
        className="mt-6"
        initial={{ opacity: 0, y: 12 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ delay: 0.2, duration: 0.5, ease: "easeOut" }}
      >
        <h1
          className="text-xl font-normal text-[var(--color-foreground)] sm:text-2xl"
          style={{ fontFamily: "var(--font-serif)" }}
        >
          {video.title}
        </h1>
        <p className="mt-1 text-sm text-[var(--color-muted)]">{video.topic}</p>

        {parseTags(video.tags).length > 0 && (
          <div className="mt-2 flex flex-wrap gap-1.5">
            {parseTags(video.tags).map((tag) => (
              <Link
                key={tag}
                href={`/?tag=${encodeURIComponent(tag)}`}
                className="rounded-full border border-[var(--color-border)] px-2.5 py-0.5 text-xs text-[var(--color-muted)] transition-colors hover:border-[var(--color-muted)] hover:text-[var(--color-foreground)]"
              >
                {tag}
              </Link>
            ))}
          </div>
        )}

        <div className="mt-4 flex items-center gap-4">
          <button
            onClick={handleLike}
            disabled={likeLoading}
            className={`flex items-center gap-1.5 rounded-md px-3 py-1.5 text-sm transition-colors ${
              liked
                ? "text-red-600"
                : "text-[var(--color-muted)] hover:text-[var(--color-foreground)]"
            }`}
          >
            <svg xmlns="http://www.w3.org/2000/svg" className="h-4 w-4" fill={liked ? "currentColor" : "none"} viewBox="0 0 24 24" stroke="currentColor" strokeWidth="2">
              <path strokeLinecap="round" strokeLinejoin="round" d="M4.318 6.318a4.5 4.5 0 000 6.364L12 20.364l7.682-7.682a4.5 4.5 0 00-6.364-6.364L12 7.636l-1.318-1.318a4.5 4.5 0 00-6.364 0z" />
            </svg>
            {likeCount > 0 && likeCount.toLocaleString()}
          </button>

          <button
            onClick={handleShare}
            className="flex items-center gap-1.5 text-sm text-[var(--color-muted)] transition-colors hover:text-[var(--color-foreground)]"
          >
            {copied ? "Copied!" : "Share"}
          </button>

          {video.vertical_video_url && (
            <a
              href={video.vertical_video_url}
              className="flex items-center gap-1.5 text-sm text-[var(--color-muted)] transition-colors hover:text-[var(--color-foreground)]"
              download
              target="_blank"
              rel="noopener noreferrer"
            >
              <svg xmlns="http://www.w3.org/2000/svg" className="h-4 w-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth="2">
                <path strokeLinecap="round" strokeLinejoin="round" d="M12 18.75V3m0 15.75l-4.5-4.5m4.5 4.5l4.5-4.5M3.75 21h16.5" />
              </svg>
              Download for Reels
            </a>
          )}

          <span className="text-xs text-[var(--color-muted)]">
            {new Date(video.created_at).toLocaleDateString("en-US", {
              year: "numeric",
              month: "long",
              day: "numeric",
            })}
          </span>
        </div>

        {/* Sources / Citations */}
        {video.sources && video.sources.length > 0 && (
          <div className="mt-6 rounded-lg border border-[var(--color-border)] bg-[var(--color-surface)]">
            <div className="flex items-center gap-2 px-4 py-3">
              <svg xmlns="http://www.w3.org/2000/svg" className="h-4 w-4 text-[var(--color-muted)]" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth="2">
                <path strokeLinecap="round" strokeLinejoin="round" d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z" />
              </svg>
              <span className="text-sm font-medium text-[var(--color-foreground)]">
                Sources ({video.sources.length})
              </span>
            </div>
            <div className="border-t border-[var(--color-border)] px-4 py-3">
              <ul className="space-y-2">
                {video.sources.map((source, i) => (
                  <li key={i} className="flex items-start gap-2">
                    <span className="mt-0.5 shrink-0 text-xs text-[var(--color-muted)]">[{i + 1}]</span>
                    <a
                      href={source.url}
                      target="_blank"
                      rel="noopener noreferrer"
                      className="text-sm text-[var(--color-foreground)] underline decoration-[var(--color-border)] underline-offset-2 transition-colors hover:decoration-[var(--color-foreground)]"
                    >
                      {source.title}
                    </a>
                  </li>
                ))}
              </ul>
            </div>
          </div>
        )}

        {/* Narration */}
        {video.narration_text && (
          <div className="mt-4 rounded-lg border border-[var(--color-border)]">
            <button
              onClick={() => setNarrationOpen(!narrationOpen)}
              className="flex w-full items-center justify-between px-4 py-3 text-left text-sm font-medium text-[var(--color-foreground)]"
            >
              Narration Script
              <svg
                xmlns="http://www.w3.org/2000/svg"
                className={`h-4 w-4 text-[var(--color-muted)] transition-transform ${narrationOpen ? "rotate-180" : ""}`}
                fill="none"
                viewBox="0 0 24 24"
                stroke="currentColor"
                strokeWidth="2"
              >
                <path strokeLinecap="round" strokeLinejoin="round" d="M19 9l-7 7-7-7" />
              </svg>
            </button>
            {narrationOpen && (
              <div className="border-t border-[var(--color-border)] px-4 py-4">
                <p className="whitespace-pre-wrap text-sm leading-relaxed text-[var(--color-foreground)]">
                  {video.narration_text}
                </p>
              </div>
            )}
          </div>
        )}

      </motion.div>

      <AuthModal isOpen={authModal} onClose={() => setAuthModal(false)} />
    </div>
  );
}
