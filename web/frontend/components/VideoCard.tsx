"use client";

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

  return (
    <Link href={`/video/${video.slug || video.id}`}>
      <article className="group flex h-full flex-col overflow-hidden rounded-lg border border-[var(--color-border)] bg-[var(--color-surface)] transition-shadow hover:shadow-sm">
        <div className="relative aspect-video w-full overflow-hidden">
          {video.thumbnail_url ? (
            <img
              src={video.thumbnail_url}
              alt={video.title}
              className="h-full w-full object-cover"
            />
          ) : (
            <div className="flex h-full w-full items-center justify-center bg-[var(--color-surface-hover)]">
              <svg xmlns="http://www.w3.org/2000/svg" className="h-8 w-8 text-[var(--color-muted)]" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth="1.5" opacity="0.4">
                <path strokeLinecap="round" strokeLinejoin="round" d="M14.752 11.168l-3.197-2.132A1 1 0 0010 9.87v4.263a1 1 0 001.555.832l3.197-2.132a1 1 0 000-1.664z" />
                <path strokeLinecap="round" strokeLinejoin="round" d="M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
              </svg>
            </div>
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
                <path strokeLinecap="round" strokeLinejoin="round" d="M4.318 6.318a4.5 4.5 0 000 6.364L12 20.364l7.682-7.682a4.5 4.5 0 00-6.364-6.364L12 7.636l-1.318-1.318a4.5 4.5 0 00-6.364 0z" />
              </svg>
              {(video.like_count || 0).toLocaleString()}
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
