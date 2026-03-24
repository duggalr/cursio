"use client";

import { useState, useRef } from "react";
import Link from "next/link";
import type { Video } from "@/lib/api";

interface VideoCardProps {
  video: Video;
}

function parseTags(tags: unknown): string[] {
  if (Array.isArray(tags)) return tags;
  if (typeof tags === "string") {
    try { return JSON.parse(tags); } catch { return []; }
  }
  return [];
}

export default function VideoCard({ video }: VideoCardProps) {
  const tags = parseTags(video.tags);
  const [hovering, setHovering] = useState(false);
  const videoRef = useRef<HTMLVideoElement>(null);
  const hoverTimeout = useRef<ReturnType<typeof setTimeout> | null>(null);

  const handleMouseEnter = () => {
    if (!video.video_url) return;
    // Small delay to avoid flickering on quick mouse passes
    hoverTimeout.current = setTimeout(() => {
      setHovering(true);
      videoRef.current?.play().catch(() => {});
    }, 400);
  };

  const handleMouseLeave = () => {
    if (hoverTimeout.current) clearTimeout(hoverTimeout.current);
    setHovering(false);
    if (videoRef.current) {
      videoRef.current.pause();
      videoRef.current.currentTime = 0;
    }
  };

  return (
    <Link href={`/video/${video.slug || video.id}`}>
      <article
        className="group flex h-full flex-col overflow-hidden rounded-lg border border-[var(--color-border)] bg-[var(--color-surface)] transition-shadow hover:shadow-sm"
        onMouseEnter={handleMouseEnter}
        onMouseLeave={handleMouseLeave}
      >
        <div className="relative aspect-video w-full overflow-hidden">
          {video.thumbnail_url ? (
            <img
              src={video.thumbnail_url}
              alt={video.title}
              className={`h-full w-full object-cover transition-opacity duration-300 ${hovering ? "opacity-0" : "opacity-100"}`}
            />
          ) : (
            <div className="flex h-full w-full items-center justify-center bg-[var(--color-surface-hover)]">
              <svg xmlns="http://www.w3.org/2000/svg" className="h-8 w-8 text-[var(--color-muted)]" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth="1.5" opacity="0.4">
                <path strokeLinecap="round" strokeLinejoin="round" d="M14.752 11.168l-3.197-2.132A1 1 0 0010 9.87v4.263a1 1 0 001.555.832l3.197-2.132a1 1 0 000-1.664z" />
                <path strokeLinecap="round" strokeLinejoin="round" d="M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
              </svg>
            </div>
          )}
          {/* Video preview on hover */}
          {video.video_url && (
            <video
              ref={videoRef}
              src={video.video_url}
              muted
              loop
              playsInline
              preload="none"
              className={`absolute inset-0 h-full w-full object-cover transition-opacity duration-300 ${hovering ? "opacity-100" : "opacity-0"}`}
            />
          )}
        </div>

        <div className="flex flex-1 flex-col p-3.5">
          <h3 className="mb-0.5 text-sm font-medium text-[var(--color-foreground)] line-clamp-2 group-hover:underline">
            {video.title}
          </h3>
          <p className="mb-2 text-xs text-[var(--color-muted)] line-clamp-1">
            {video.topic}
          </p>
          {tags.length > 0 && (
            <div className="mb-2 flex flex-wrap gap-1">
              {tags.slice(0, 3).map((tag) => (
                <span
                  key={tag}
                  className="rounded-full bg-[var(--color-surface-hover)] px-2 py-0.5 text-[10px] text-[var(--color-muted)]"
                >
                  {tag}
                </span>
              ))}
            </div>
          )}
          <div className="mt-auto flex items-center justify-between text-xs text-[var(--color-muted)]">
            <span className="flex items-center gap-1">
              <svg xmlns="http://www.w3.org/2000/svg" className="h-3 w-3" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth="2">
                <path strokeLinecap="round" strokeLinejoin="round" d="M15 12a3 3 0 11-6 0 3 3 0 016 0z" />
                <path strokeLinecap="round" strokeLinejoin="round" d="M2.458 12C3.732 7.943 7.523 5 12 5c4.478 0 8.268 2.943 9.542 7-1.274 4.057-5.064 7-9.542 7-4.477 0-8.268-2.943-9.542-7z" />
              </svg>
              {(video.view_count || 0).toLocaleString()} views
            </span>
            <span>
              {new Date(video.created_at).toLocaleDateString("en-US", {
                month: "short",
                day: "numeric",
              })}
            </span>
          </div>
        </div>
      </article>
    </Link>
  );
}
