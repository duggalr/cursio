# Curiso — 3B1B Quality Improvement Roadmap

## Phase 1: Establish Baseline (current)
- [ ] Select 5 diverse short topics from eval set (incl. 1 DL topic)
- [ ] Generate all 5 videos with current pipeline (no-voice mode)
- [ ] Run plan + video evaluation on all 5
- [ ] Review frames and identify common quality issues
- [ ] Document baseline scores and patterns

## Phase 2: Few-Shot Examples in Codegen
- [ ] Pick 3 gold-standard Manim code examples (concept, math, comparison)
- [ ] Embed directly in codegen system prompt
- [ ] Re-run same 5 topics, compare scores to baseline

## Phase 3: Scene-Type Tagging
- [ ] Add scene type field to planner output (hook, comparison, derivation, process, reveal)
- [ ] Route to type-specific few-shot examples in codegen
- [ ] Re-run eval, compare to Phase 2

## Phase 4: Visual Quality Feedback Loop
- [ ] After rendering each scene, extract frames and evaluate quality
- [ ] If quality score < threshold, regenerate with specific feedback
- [ ] Add --quality-check flag to pipeline
- [ ] Re-run eval, compare to Phase 3
