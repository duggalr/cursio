# Curiso — Product Roadmap & Priorities

## Priority 1: SEO & Analytics — DONE
- [x] Replace UUID video URLs with named slugs
- [x] Add slug column to videos table (unique, indexed)
- [x] Generate slug from title at video creation time
- [x] Dynamic meta tags per video page (title, description, og:image)
- [x] Add sitemap.xml and robots.txt
- [x] Add Google Analytics (G-EYYQZ0KEM0)
- [x] Auto-generated tags per video with tag filtering
- [x] Infinite scroll pagination
- [x] Word-level search matching
- [x] CI pipeline (27 backend tests + frontend build)

## Priority 2: Animation Quality Improvement
- [x] Establish baseline (5 topics, avg plan 8.3, avg video 6.6)
- [ ] Few-shot examples in codegen prompt (target: animation_quality from 5.8 → 7+)
- [ ] Scene-type tagging in planner → type-specific codegen guidance
- [ ] Visual quality feedback loop (render → inspect frames → regenerate if bad)
- [ ] Split scenes into individual files for independent iteration

## Priority 3: Research Paper → Video (NEXT) 
- [ ] Study Eve's CLAUDE.md approach to understand quality patterns
- [ ] PDF upload on frontend + text extraction
- [ ] Claude summarizes paper into scene plan (target 5-10 min)
- [ ] End-to-end pipeline: PDF → plan → scenes → render → assemble
- [ ] Monetization: free tier (short topic videos) vs paid tier ($20/mo for paper uploads, long videos, web search)

## Priority 4: Eve-Style Quality (Premium Tier)
- [ ] Per-scene sub-agents that render, inspect, iterate until quality passes
- [ ] One scene per file architecture
- [ ] Audio-last workflow (visuals locked before TTS)
- [ ] Could be the paid tier differentiator

## Priority 5: Small UI improvements
- [ ] Add number of views a video got and do popular ordering by that, add video preview showing on mouseover 
- [ ] Random video button (takes user to a random video)
- [ ] Search visible on both My Videos and Community tabs
- [ ] Exposing an API version of this where I add my video prompt / topic in text and call the API and it generates and returns a link to the generated video?
    - not sure how exactly this would work since video generation job is long but would be cool and useful
        - also having it accept params, having web_search as a metadata that is enabled/disabled all would be very nice

## Priority 6: Chat Interface
- [ ] V1: Text chat grounded on video narration + plan (simple Claude API call)
- [ ] V2: Agent SDK with tools (search transcript, generate follow-up animations, cite timestamps)
- [ ] Chat box on video detail page

## Priority 7: Continuous Quality
- [ ] Better voice selection (multiple ElevenLabs voices, auto-select by topic tone)
- [ ] Improve research pipeline (filter/verify Tavily results before injecting)
- [ ] Longer video support (medium/long reliability improvements)


## Baseline Eval Results (2026-03-22)
- Plan avg: 8.3/10 (plans are solid)
- Video avg: 6.6/10 (visual execution is the bottleneck)
- Worst criterion: animation_quality at 5.8
- Common issues: black frame gaps, static periods, text cut-off, lack of progressive reveals
- Research A/B: Tavily search didn't improve scores — made opt-in toggle instead
