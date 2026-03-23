import type { Metadata } from "next";

const API_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

export async function generateMetadata({ params }: { params: Promise<{ slug: string }> }): Promise<Metadata> {
  const { slug } = await params;

  try {
    const res = await fetch(`${API_URL}/api/videos/${slug}`, { next: { revalidate: 3600 } });
    if (!res.ok) return { title: "Video — Curiso" };

    const video = await res.json();
    const description = video.narration_text
      ? video.narration_text.slice(0, 160) + (video.narration_text.length > 160 ? "..." : "")
      : `Watch "${video.title}" — an AI-generated educational video on Curiso`;

    return {
      title: `${video.title} — Curiso`,
      description,
      openGraph: {
        title: video.title,
        description,
        type: "video.other",
        images: video.thumbnail_url ? [{ url: video.thumbnail_url }] : [],
        url: `https://curiso.app/video/${slug}`,
      },
      twitter: {
        card: "summary_large_image",
        title: video.title,
        description,
        images: video.thumbnail_url ? [video.thumbnail_url] : [],
      },
    };
  } catch {
    return { title: "Video — Curiso" };
  }
}

export default function VideoLayout({ children }: { children: React.ReactNode }) {
  return children;
}
