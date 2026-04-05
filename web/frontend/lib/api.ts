const API_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

export interface VideoSource {
  title: string;
  url: string;
}

export interface Video {
  id: string;
  slug: string;
  title: string;
  topic: string;
  duration: "short" | "medium" | "long";
  thumbnail_url: string | null;
  video_url: string | null;
  vertical_video_url: string | null;
  narration_text: string | null;
  like_count: number;
  view_count: number;
  is_featured: boolean;
  source_url: string | null;
  sources: VideoSource[] | null;
  tags: string[] | null;
  created_at: string;
}

export interface VideoListResponse {
  videos: Video[];
  total: number;
  page: number;
  limit: number;
}

export interface Job {
  id: string;
  video_id: string | null;
  status: "pending" | "planning" | "generating" | "rendering" | "voiceover" | "assembling" | "completed" | "failed";
  current_step: string;
  error: string | null;
  created_at: string;
  updated_at: string;
}

export async function fetchVideos(params?: {
  search?: string;
  sort?: string;
  page?: number;
  limit?: number;
  tag?: string;
  featured?: boolean;
}): Promise<VideoListResponse> {
  const searchParams = new URLSearchParams();
  if (params?.search) searchParams.set("search", params.search);
  if (params?.sort) searchParams.set("sort", params.sort);
  if (params?.page) searchParams.set("page", String(params.page));
  if (params?.limit) searchParams.set("limit", String(params.limit));
  if (params?.tag) searchParams.set("tag", params.tag);
  if (params?.featured) searchParams.set("featured", "true");

  const query = searchParams.toString();
  const url = `${API_URL}/api/videos${query ? `?${query}` : ""}`;

  const res = await fetch(url);
  if (!res.ok) {
    throw new Error(`Failed to fetch videos: ${res.statusText}`);
  }
  return res.json();
}

export interface TagWithCount {
  tag: string;
  count: number;
}

export async function fetchTags(): Promise<TagWithCount[]> {
  const res = await fetch(`${API_URL}/api/tags`);
  if (!res.ok) return [];
  const data = await res.json();
  return data.tags || [];
}

export async function fetchVideo(slug: string): Promise<Video> {
  const res = await fetch(`${API_URL}/api/videos/${slug}`);
  if (!res.ok) {
    throw new Error(`Failed to fetch video: ${res.statusText}`);
  }
  return res.json();
}

export async function generateVideo(
  topic: string,
  duration: string,
  token: string,
  useResearch: boolean = false,
  qualityMode: boolean = false,
): Promise<{ job_id: string }> {
  const res = await fetch(`${API_URL}/api/generate`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
      Authorization: `Bearer ${token}`,
    },
    body: JSON.stringify({ topic, duration, use_research: useResearch, quality_mode: qualityMode }),
  });
  if (!res.ok) {
    const data = await res.json().catch(() => ({}));
    throw new Error(data.detail || `Failed to generate video: ${res.statusText}`);
  }
  return res.json();
}

export async function fetchJobStatus(jobId: string): Promise<Job> {
  const res = await fetch(`${API_URL}/api/jobs/${jobId}`);
  if (!res.ok) {
    throw new Error(`Failed to fetch job status: ${res.statusText}`);
  }
  return res.json();
}

export async function likeVideo(videoId: string, token: string): Promise<void> {
  const res = await fetch(`${API_URL}/api/videos/${videoId}/like`, {
    method: "POST",
    headers: { Authorization: `Bearer ${token}` },
  });
  if (!res.ok) {
    throw new Error(`Failed to like video: ${res.statusText}`);
  }
}

export async function unlikeVideo(videoId: string, token: string): Promise<void> {
  const res = await fetch(`${API_URL}/api/videos/${videoId}/like`, {
    method: "DELETE",
    headers: { Authorization: `Bearer ${token}` },
  });
  if (!res.ok) {
    throw new Error(`Failed to unlike video: ${res.statusText}`);
  }
}

export async function generateFromPaper(
  file: File,
  duration: string,
  token: string,
): Promise<{ job_id: string }> {
  const formData = new FormData();
  formData.append("file", file);
  formData.append("duration", duration);

  const res = await fetch(`${API_URL}/api/generate-from-paper`, {
    method: "POST",
    headers: {
      Authorization: `Bearer ${token}`,
    },
    body: formData,
  });
  if (!res.ok) {
    const data = await res.json().catch(() => ({}));
    throw new Error(data.detail || `Failed to upload paper: ${res.statusText}`);
  }
  return res.json();
}

export async function generateFromURL(
  url: string,
  duration: string,
  token: string,
): Promise<{ job_id: string }> {
  const res = await fetch(`${API_URL}/api/generate-from-url`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
      Authorization: `Bearer ${token}`,
    },
    body: JSON.stringify({ url, duration }),
  });
  if (!res.ok) {
    const data = await res.json().catch(() => ({}));
    throw new Error(data.detail || `Failed to generate from URL: ${res.statusText}`);
  }
  return res.json();
}

export async function fetchActiveJob(token: string): Promise<Job | null> {
  const res = await fetch(`${API_URL}/api/jobs/active/me`, {
    headers: { Authorization: `Bearer ${token}` },
  });
  if (!res.ok) return null;
  const data = await res.json();
  return data || null;
}

export async function recordView(videoId: string): Promise<void> {
  await fetch(`${API_URL}/api/videos/${videoId}/view`, { method: "POST" }).catch(() => {});
}

export async function checkIfLiked(videoId: string, token: string): Promise<boolean> {
  const res = await fetch(`${API_URL}/api/videos/${videoId}/like`, {
    headers: { Authorization: `Bearer ${token}` },
  });
  if (!res.ok) return false;
  const data = await res.json();
  return data.liked;
}
