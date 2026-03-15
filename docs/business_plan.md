# Business Plan — AI Educational Video Generator

## Product Vision

A web platform where anyone can generate high-quality, 3Blue1Brown-style educational
videos on any topic using AI. The gallery of generated videos becomes a growing
library of visual explanations that's freely browsable by anyone.

Long-term: expand beyond Manim-style math animations into multiple video content
types (stick figure motion graphics, 3D mannequin scenes, realistic character
scenarios) — same core pipeline (AI plans → engine renders → voice + subtitles →
assemble), different rendering engines.

## Pricing Strategy — V1

### Free with daily limit (5 videos/user/day)

| Feature | Access |
|---------|--------|
| Browse & watch gallery | Everyone (no auth) |
| Search videos by topic | Everyone (no auth) |
| Generate videos | Authenticated users |
| Daily generation limit | 5 per user per day |
| Duration options | Short, Medium, Long |
| All videos public in gallery | Yes |

**Why free:** The goal is traffic and content growth. Every video generated
adds to the gallery, which drives SEO traffic, which brings more users, who
generate more videos. The flywheel only works if generation is frictionless.

**Why 5/day:** Prevents abuse while being generous enough that no legitimate
user feels limited. At ~$0.30 average cost per video, 100 daily active users
generating 3 videos each = ~$90/day = ~$2,700/month. Manageable at early scale.

### Future Paid Tiers (when demand justifies it)

| Tier | Price | Limit | Extras |
|------|-------|-------|--------|
| Free | $0 | 5/day | Public videos only |
| Pro | $9/month | 20/day | Private videos, no watermark, priority queue |
| Team | $29/month | 50/day | API access, custom branding, bulk export |

Don't launch paid tiers until free tier is clearly hitting limits and users
are asking for more. Premature monetization kills growth.

## Cost Structure

### Per-video generation cost

| Component | Short (90s) | Medium (5min) | Long (10min) |
|-----------|------------|---------------|--------------|
| Claude — planner | $0.02 | $0.04 | $0.06 |
| Claude — codegen | $0.05 | $0.10 | $0.15 |
| Claude — retries (~2) | $0.05 | $0.08 | $0.12 |
| ElevenLabs TTS | $0.03 | $0.10 | $0.18 |
| Compute (Manim render) | $0.01 | $0.02 | $0.03 |
| **Total** | **~$0.16** | **~$0.34** | **~$0.54** |

### Monthly infrastructure cost (estimated at 100 DAU)

| Item | Cost |
|------|------|
| Vercel (frontend hosting) | $0 (free tier) |
| Railway/Fly.io (backend + worker) | $20-40/month |
| Supabase (DB + auth + storage) | $0-25/month |
| Domain + SSL | ~$12/year |
| Anthropic API | ~$1,500-2,500/month (at scale) |
| ElevenLabs API | ~$500-1,000/month (at scale) |
| **Total** | **~$2,000-3,500/month at 100 DAU** |

At early stage (10-20 DAU): ~$200-500/month. Very manageable.

## Marketing & Growth Strategy

### Channel 1: Short-form video (Primary — start immediately)

**Platforms:** TikTok > Instagram Reels > YouTube Shorts

**Why this is our unfair advantage:** The tool generates the content. Most
creators spend hours per video. We type a topic, wait 5 minutes, and post.
This makes daily posting sustainable.

**Content strategy:**
- 1 video/day for first 30 days (critical for algorithm training)
- Then 3-5 videos/week
- Every video ends with a 2-second text card: "More at [site]"

**Topic selection:**
- **Trending/timely:** Generate videos on whatever is in the news that has
  an educational angle. Tariffs, new tech, science breakthroughs.
- **Evergreen search magnets:** "Why is the sky blue", "How WiFi works",
  "What is compound interest" — these get searched forever.
- **Contrarian/surprising:** "Why 0.999... equals 1", "The number that
  broke math" — these get shares because people argue in comments.
- **School/exam seasonal:** Calculus during finals, physics during AP season.

**Metrics to track:** Views, shares, profile visits, link clicks to site.

### Channel 2: Reddit (High leverage, start week 2)

**Key subreddits:**
- r/explainlikeimfive (23M members)
- r/askscience (25M)
- r/learnmath (1.2M)
- r/learnprogramming (4.5M)
- r/computerscience
- r/networking
- r/economics

**The play:** When someone asks "can someone explain X?", generate a video
and reply with it. This is genuinely helpful — not spam. People love visual
answers to text questions.

**Rules:**
- Don't post the same link in multiple subreddits
- Be a genuine community member, not a link dropper
- Only share when the video genuinely answers the question
- Engage in the comments

### Channel 3: Twitter/X (Start week 2)

**What to post:** The generated video as a native upload with a thread
explaining the concept. Tag relevant people in the field.

**The "I built this" angle:** Developers and educators will share it.
Tech Twitter loves visual explainers and builder stories.

**Example post:**
"I built a tool that generates 3Blue1Brown-style explainers on any topic.
Here's one on how public key cryptography works: [video].
Try it free: [site]"

### Channel 4: SEO (Long game, built into the product)

Every video page is an SEO page. Structure:
- Page title: "{Video Title} — Visual Explainer"
- Full narration text on the page (for Google to index)
- VideoObject schema markup
- Sitemap auto-generated from all video pages

Target searches like: "how does DNS work visual explanation",
"derivative explained visually", "public key cryptography animation"

### Channel 5: Product Hunt launch (One-time, week 6-8)

Launch when:
- Gallery has 50+ videos
- Social accounts have some traction
- App is polished and stable

Aim for Tuesday or Wednesday. "AI-generated 3Blue1Brown-style educational
videos on any topic" hits the AI + education + open-source sweet spot.

## Growth Timeline

| Week | Milestone |
|------|-----------|
| 1-2 | Build web app MVP |
| 3 | Seed gallery with 30+ videos across popular topics |
| 4 | Launch site, start daily TikTok/Reels posting |
| 5-6 | Start Reddit engagement, Twitter presence |
| 6-8 | Product Hunt launch |
| 8-12 | Iterate on product based on user feedback |
| 12+ | Evaluate paid tier demand, explore additional content types |

## Success Metrics

| Metric | 1 month | 3 months | 6 months |
|--------|---------|----------|----------|
| Gallery videos | 100 | 500 | 2,000 |
| Monthly active users | 50 | 500 | 2,000 |
| Daily video generations | 10 | 50 | 200 |
| TikTok followers | 500 | 5,000 | 20,000 |
| Monthly site visits | 1,000 | 10,000 | 50,000 |

## Future Content Types (Post-V1)

The platform architecture supports multiple rendering engines behind the
same planner → render → voice → assemble pipeline:

| Content Type | Rendering Engine | Use Case |
|-------------|-----------------|----------|
| Math/educational animations | Manim CE | Explaining concepts (current) |
| Stick figure motion graphics | Custom or Animatron API | Storytelling, scenarios, soft skills |
| 3D mannequin scenes | Blender Python API | Physical demonstrations, sports, ergonomics |
| Realistic character scenes | AI video generation (Veo/Sora) | Dramatic scenarios, history reenactments |

Each engine would be a pluggable module in `core/`. The planner determines
which engine fits the topic, or the user selects it.
