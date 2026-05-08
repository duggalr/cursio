import { createClient } from "./supabase";

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

export interface TagWithCount {
  tag: string;
  count: number;
}

type VideoRow = Omit<Video, "like_count"> & {
  likes?: { count: number }[] | null;
};

function normalizeVideo(row: VideoRow): Video {
  const likes = row.likes ?? [];
  const like_count = likes[0]?.count ?? 0;
  const { likes: _likes, ...rest } = row;
  void _likes;
  return { ...rest, like_count } as Video;
}

export async function fetchVideos(params?: {
  search?: string;
  sort?: string;
  page?: number;
  limit?: number;
  tag?: string;
  featured?: boolean;
}): Promise<VideoListResponse> {
  const supabase = createClient();
  const page = params?.page ?? 1;
  const limit = params?.limit ?? 20;
  const offset = (page - 1) * limit;

  let query = supabase
    .from("videos")
    .select("*, likes(count)", { count: "exact" });

  if (params?.featured) {
    query = query.eq("is_featured", true);
  }

  if (params?.search) {
    const words = params.search.split(/\s+/).filter(Boolean);
    if (words.length > 0) {
      const conditions = words
        .flatMap((w) => [`topic.ilike.%${w}%`, `title.ilike.%${w}%`])
        .join(",");
      query = query.or(conditions);
    }
  }

  if (params?.tag) {
    query = query.contains("tags", [params.tag]);
  }

  const sort = params?.sort ?? "recent";
  if (sort === "most_liked") {
    query = query.order("like_count", { ascending: false });
  } else if (sort === "most_viewed") {
    query = query.order("view_count", { ascending: false });
  } else {
    query = query.order("created_at", { ascending: false });
  }

  query = query.range(offset, offset + limit - 1);

  const { data, count, error } = await query;
  if (error) throw new Error(`Failed to fetch videos: ${error.message}`);

  const videos = (data ?? []).map((row: unknown) => normalizeVideo(row as VideoRow));
  return { videos, total: count ?? videos.length, page, limit };
}

export async function fetchTags(): Promise<TagWithCount[]> {
  const supabase = createClient();
  const { data, error } = await supabase
    .from("videos")
    .select("tags")
    .not("tags", "is", null);

  if (error) return [];

  const counts = new Map<string, number>();
  for (const row of data ?? []) {
    const tags = (row as { tags: unknown }).tags;
    const list = Array.isArray(tags)
      ? tags
      : typeof tags === "string"
        ? safeParseStringArray(tags)
        : [];
    for (const tag of list) {
      if (typeof tag === "string" && tag) {
        counts.set(tag, (counts.get(tag) ?? 0) + 1);
      }
    }
  }

  return [...counts.entries()]
    .map(([tag, count]) => ({ tag, count }))
    .sort((a, b) => b.count - a.count);
}

function safeParseStringArray(value: string): unknown[] {
  try {
    const parsed = JSON.parse(value);
    return Array.isArray(parsed) ? parsed : [];
  } catch {
    return [];
  }
}

export async function fetchVideo(slugOrId: string): Promise<Video> {
  const supabase = createClient();
  const isUuid = /^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$/i.test(slugOrId);
  const column = isUuid ? "id" : "slug";

  const { data, error } = await supabase
    .from("videos")
    .select("*, likes(count)")
    .eq(column, slugOrId)
    .single();

  if (error || !data) throw new Error(`Failed to fetch video: ${error?.message ?? "not found"}`);
  return normalizeVideo(data as VideoRow);
}

// Generation, job polling, and rate-limit endpoints used to live on the
// FastAPI backend. The backend is currently offline, so these throw a
// clear error if anything still calls them. The UI no longer does.
function generationDisabled(): never {
  throw new Error("Video generation is temporarily paused.");
}

export async function generateVideo(): Promise<{ job_id: string }> {
  generationDisabled();
}

export async function generateFromPaper(): Promise<{ job_id: string }> {
  generationDisabled();
}

export async function generateFromURL(): Promise<{ job_id: string }> {
  generationDisabled();
}

export async function fetchJobStatus(): Promise<Job> {
  generationDisabled();
}

export async function fetchActiveJob(): Promise<Job | null> {
  return null;
}

export async function likeVideo(videoId: string): Promise<void> {
  const supabase = createClient();
  const { data: { user } } = await supabase.auth.getUser();
  if (!user) throw new Error("Sign in required");

  const { error } = await supabase
    .from("likes")
    .insert({ video_id: videoId, user_id: user.id });

  // Ignore unique-constraint violation if the row already exists
  if (error && error.code !== "23505") {
    throw new Error(`Failed to like video: ${error.message}`);
  }
}

export async function unlikeVideo(videoId: string): Promise<void> {
  const supabase = createClient();
  const { data: { user } } = await supabase.auth.getUser();
  if (!user) throw new Error("Sign in required");

  const { error } = await supabase
    .from("likes")
    .delete()
    .eq("video_id", videoId)
    .eq("user_id", user.id);

  if (error) throw new Error(`Failed to unlike video: ${error.message}`);
}

export async function recordView(_videoId: string): Promise<void> {
  // View count increments are intentionally a no-op while the backend
  // is offline. Add a Postgres RPC + supabase.rpc(...) call here if we
  // want to track views again.
  void _videoId;
}

export async function checkIfLiked(videoId: string): Promise<boolean> {
  const supabase = createClient();
  const { data: { user } } = await supabase.auth.getUser();
  if (!user) return false;

  const { data, error } = await supabase
    .from("likes")
    .select("id")
    .eq("video_id", videoId)
    .eq("user_id", user.id)
    .maybeSingle();

  if (error) return false;
  return !!data;
}
