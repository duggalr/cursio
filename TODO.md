# Curiso — Product Roadmap & Priorities

## Priority 1: SEO & Analytics (current branch)
- [ ] Replace UUID video URLs with named slugs (`/video/the-hidden-reason-oil-and-water-dont-mix`)
- [ ] Add `slug` column to videos table (unique, indexed)
- [ ] Generate slug from title at video creation time
- [ ] Dynamic meta tags per video page (title, description, og:image)
- [ ] Add sitemap.xml and robots.txt
- [ ] Add Google Analytics via @next/third-parties

## Priority 2: Animation Quality Improvement
- [x] Establish baseline (5 topics, avg plan 8.3, avg video 6.6)
- [ ] Few-shot examples in codegen prompt (target: animation_quality from 5.8 → 7+)
- [ ] Scene-type tagging in planner → type-specific codegen guidance
- [ ] Visual quality feedback loop (render → inspect frames → regenerate if bad)
- [ ] Split scenes into individual files for independent iteration

## Priority 3: Research Paper → Video
- [ ] PDF upload on frontend + text extraction
- [ ] Claude summarizes paper into scene plan (target 5-10 min)
- [ ] End-to-end pipeline: PDF → plan → scenes → render → assemble
- [ ] Monetization: free tier (short topic videos) vs paid tier ($20/mo for paper uploads, long videos, web search)

## Priority 4: Eve-Style Quality (Premium Tier)
- [ ] Study Eve's CLAUDE.md approach (Claude Code as director, not API)
- [ ] Per-scene sub-agents that render, inspect, iterate until quality passes
- [ ] One scene per file architecture
- [ ] Audio-last workflow (visuals locked before TTS)
- [ ] Could be the paid tier differentiator

## Priority 5: Chat Interface
- [ ] V1: Text chat grounded on video narration + plan (simple Claude API call)
- [ ] V2: Agent SDK with tools (search transcript, generate follow-up animations, cite timestamps)
- [ ] Chat box on video detail page

## Priority 6: Continuous Quality
- [ ] Better voice selection (multiple ElevenLabs voices, auto-select by topic tone)
- [ ] Improve research pipeline (filter/verify Tavily results before injecting)
- [ ] Longer video support (medium/long reliability improvements)

## Baseline Eval Results (2026-03-22)
- Plan avg: 8.3/10 (plans are solid)
- Video avg: 6.6/10 (visual execution is the bottleneck)
- Worst criterion: animation_quality at 5.8
- Common issues: black frame gaps, static periods, text cut-off, lack of progressive reveals
- Research A/B: Tavily search didn't improve scores — made opt-in toggle instead
