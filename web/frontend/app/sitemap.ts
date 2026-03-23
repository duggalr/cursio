import type { MetadataRoute } from "next";

const API_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

export default async function sitemap(): Promise<MetadataRoute.Sitemap> {
  const entries: MetadataRoute.Sitemap = [
    {
      url: "https://curiso.app",
      lastModified: new Date(),
      changeFrequency: "daily",
      priority: 1,
    },
    {
      url: "https://curiso.app/about",
      lastModified: new Date(),
      changeFrequency: "monthly",
      priority: 0.5,
    },
  ];

  try {
    const res = await fetch(`${API_URL}/api/videos?limit=100`, { next: { revalidate: 3600 } });
    if (res.ok) {
      const data = await res.json();
      for (const video of data.videos || []) {
        entries.push({
          url: `https://curiso.app/video/${video.slug || video.id}`,
          lastModified: new Date(video.created_at),
          changeFrequency: "monthly",
          priority: 0.8,
        });
      }
    }
  } catch {
    // fail silently
  }

  return entries;
}
