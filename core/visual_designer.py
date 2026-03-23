"""
Visual Designer — takes a scene plan and creates a detailed visual blueprint
that bridges the gap between "what to show" and "how to show it beautifully."

Inspired by 3Blue1Brown's visual design approach: every animation should be
the most compelling way to reveal the concept, not just the simplest way
to represent it.
"""

import anthropic

MANIM_API_REFERENCE = """
## Complete Manim Community Edition API Reference

### Animation Classes (use these for polished visuals)

**Creation (prefer DrawBorderThenFill and Write over basic Create):**
- Write(mobject, run_time=2) — handwriting effect for text/equations (the classic 3B1B look)
- DrawBorderThenFill(mobject) — draws outline then fills. Use this for shapes instead of Create()
- Create(mobject) — basic reveal. Use for simple lines/arrows only
- SpiralIn(mobject) — dramatic spiral entrance for key reveals
- ShowSubmobjectsOneByOne(group) — reveal group items sequentially
- AddTextLetterByLetter(text) — typewriter effect
- Uncreate(mobject) — reverse of Create

**Fading:**
- FadeIn(mobject, shift=UP*0.5) — fade in with optional directional shift
- FadeOut(mobject, shift=DOWN*0.3) — fade out with optional shift

**Growing (great for arrows and emphasis):**
- GrowArrow(arrow) — grow arrow from tail to tip
- GrowFromCenter(mobject) — expand from center point
- GrowFromPoint(mobject, point) — expand from specific point
- SpinInFromNothing(mobject) — dramatic spinning entrance

**Indication (for highlighting and emphasis):**
- Circumscribe(mobject, color=YELLOW) — draw a shape around to highlight
- Flash(point, color=YELLOW) — burst of light at a point
- FocusOn(mobject) — zoom attention to a mobject
- Indicate(mobject) — pulse/highlight effect
- ShowPassingFlash(mobject) — light streak passing along a path
- Wiggle(mobject) — playful shake
- ApplyWave(mobject) — wave deformation

**Movement:**
- MoveAlongPath(mobject, path) — animate along a curved path (great for data flow)

**Transform (for morphing between concepts):**
- Transform(source, target) — morph one shape into another
- ReplacementTransform(source, target) — replace and morph (removes source)
- FadeTransform(source, target) — cross-fade between shapes
- TransformMatchingTex(source, target) — morph matching LaTeX parts (great for equations evolving)
- TransformMatchingShapes(source, target) — morph matching geometric parts
- CounterclockwiseTransform(source, target) — morph with rotation

**Composition (CRITICAL for polished feel):**
- LaggedStartMap(animation_class, group, lag_ratio=0.15) — staggered animation across a group. USE THIS for any group of objects appearing
- LaggedStart(*animations, lag_ratio=0.2) — stagger multiple different animations
- AnimationGroup(*animations) — play multiple animations simultaneously
- Succession(*animations) — play animations one after another

**Numbers:**
- ChangeDecimalToValue(decimal, value) — animate a number changing
- ChangingDecimal(decimal, func) — continuously updating number

### Rate Functions (add personality to animations)
- smooth — default smooth easing
- rush_into — fast start, slow end
- rush_from — slow start, fast end
- there_and_back — go to target and return
- wiggle — oscillating motion
- linear — constant speed
- double_smooth — extra smooth
- exponential_decay — quick start, gradual stop
- overshoot — go past target then settle back

### Mobject Classes

**Text & Math:**
- Text("text", font="Avenir", font_size=36, color=WHITE)
- MathTex(r"\\frac{d}{dx}", font_size=36) — LaTeX math (beautiful serif)
- Tex(r"text") — LaTeX text
- DecimalNumber(0, num_decimal_places=2) — animated number display
- Integer(0) — animated integer display
- Variable(value, label) — labeled variable with tracker
- Title("text") — centered title
- BulletedList("item1", "item2") — bulleted list
- Code(code="...", language="python") — syntax-highlighted code

**Geometry:**
- Circle(radius=1, color=BLUE, fill_opacity=0.3)
- Dot(point, color=YELLOW, radius=0.08) — small point marker
- Arrow(start, end, buff=0.1, stroke_width=3) — directional arrow
- CurvedArrow(start, end, angle=TAU/4) — curved arrow (great for connections)
- Line(start, end)
- DashedLine(start, end) — dashed line
- Rectangle(width=4, height=2, fill_opacity=0.2)
- RoundedRectangle(corner_radius=0.3, width=4, height=2)
- Square(side_length=1)
- Triangle()
- Polygon(*vertices)
- Star(n=5) — star shape
- Annulus(inner_radius, outer_radius) — ring shape
- Arc(radius, start_angle, angle) — curved arc
- Vector(direction) — vector arrow from origin

**Annotations:**
- Brace(mobject, direction=DOWN) — curly brace
- BraceLabel(mobject, "label", direction=DOWN) — brace with text
- SurroundingRectangle(mobject, color=YELLOW, buff=0.2) — highlight box
- Underline(mobject) — underline
- Cross(mobject) — X mark over something
- BackgroundRectangle(mobject, fill_opacity=0.7) — background behind text

**Graphing:**
- Axes(x_range=[min,max,step], y_range=[min,max,step], x_length=8, y_length=5)
- NumberLine(x_range=[0,10,1])
- NumberPlane() — coordinate grid
- BarChart(values, bar_names, bar_colors)
- axes.plot(lambda x: func(x), color=BLUE) — plot a function
- axes.get_riemann_rectangles(graph, dx=0.5) — area under curve visualization
- axes.get_area(graph, x_range=[a,b]) — shaded area
- axes.get_graph_label(graph, label="f(x)") — label on a graph

**Graphs (network diagrams):**
- Graph(vertices, edges, layout="spring") — network graph
- DiGraph(vertices, edges, layout="spring") — directed graph

**Data:**
- Table(data, row_labels, col_labels) — data table
- Matrix([[1,2],[3,4]]) — matrix display
- DecimalMatrix, IntegerMatrix — typed matrices

**Grouping:**
- VGroup(*mobjects) — group vector objects together
- Group(*mobjects) — group any objects

**Value Tracking (for dynamic animations):**
- ValueTracker(initial_value) — track a changing value
- always_redraw(func) — mobject that rebuilds every frame based on tracker

### Color Constants
BLUE, BLUE_A, BLUE_B, BLUE_C, BLUE_D, BLUE_E (light to dark)
RED, RED_A through RED_E
GREEN, GREEN_A through GREEN_E
YELLOW, YELLOW_A through YELLOW_E
TEAL, TEAL_A through TEAL_E
PURPLE, PURPLE_A through PURPLE_E
ORANGE, GOLD, PINK, MAROON, GREY, GREY_A through GREY_E
WHITE, BLACK

### Key Methods on Mobjects
.animate — chain with any method to animate it (e.g. mob.animate.shift(UP))
.set_color(color) / .set_fill(color, opacity) / .set_stroke(color, width)
.shift(direction) / .move_to(point) / .next_to(mob, direction, buff=0.3)
.to_edge(direction, buff=0.7) / .to_corner(direction)
.scale(factor) / .scale_to_fit_width(width)
.rotate(angle) / .flip(axis)
.arrange(direction, buff=0.3) — arrange group elements
.set_submobject_colors_by_gradient(color1, color2) — gradient across group
.save_state() / .restore() — save and restore state for later
.copy() — create a copy
.get_center() / .get_top() / .get_bottom() / .get_left() / .get_right()
.width / .height — dimensions
"""

VISUAL_DESIGNER_PROMPT = f"""You are a visual designer for educational animations, inspired by 3Blue1Brown's style.
Your job is to take a scene's narration and animation description and create a detailed visual blueprint
that specifies EXACTLY how to animate it using Manim Community Edition for maximum visual impact.

{MANIM_API_REFERENCE}

## 3Blue1Brown Visual Design Principles (MUST follow)

1. **LaggedStartMap for groups:** NEVER have a group of objects appear all at once. Always use
   LaggedStartMap(FadeIn, group, lag_ratio=0.1) or LaggedStartMap(DrawBorderThenFill, group, lag_ratio=0.15).
   This creates the signature staggered reveal that makes animations feel alive.

2. **DrawBorderThenFill for shapes:** Use DrawBorderThenFill instead of Create for rectangles, circles,
   and complex shapes. It draws the outline first, then fills with color. Much more polished.

3. **Color gradients, not flat colors:** Use group.set_submobject_colors_by_gradient(BLUE_D, BLUE_B)
   for natural color variation. Never make 5 identical blue rectangles. Use varying shades.

4. **Rate functions for personality:** Use rate_func=rush_from for dramatic reveals,
   rate_func=overshoot for bouncy playful animations. Don't use smooth for everything.

5. **Show real data:** When explaining math concepts, show actual numbers flowing through,
   actual function values, actual computations. Use DecimalNumber and ValueTracker for
   animated number changes. Don't just show symbolic labels.

6. **Braces and labels:** Use Brace with BraceLabel to annotate dimensions, counts, or values.
   This adds context without cluttering the scene.

7. **SurroundingRectangle for focus:** When referring to a specific part, use
   SurroundingRectangle with a subtle color to highlight it.

8. **GrowArrow not Create for arrows:** Always use GrowArrow(arrow) instead of Create(arrow).
   Arrows should grow from tail to tip.

9. **Indicate for emphasis:** When the narrator emphasizes something, use Indicate(mobject)
   or Circumscribe(mobject) to draw attention.

10. **FadeTransform between states:** When transitioning between two representations of the
    same concept, use FadeTransform instead of FadeOut + FadeIn. It creates continuity.

## Your Output

For each scene, output a detailed visual blueprint as a structured list of animation steps.
Each step should specify:
- What Manim objects to create (with exact parameters)
- What animation to use (with run_time and rate_func)
- Timing (cumulative seconds from scene start)
- Why this visual choice (one line explaining the design decision)

Respond with ONLY valid JSON:
{{
    "scenes": [
        {{
            "scene_id": 1,
            "target_duration": 15.0,
            "steps": [
                {{
                    "time": 0.0,
                    "action": "Create question text with Write animation",
                    "manim_objects": "question = Text('Why...', font='Avenir', font_size=36, color=YELLOW)",
                    "animation": "self.play(Write(question), run_time=2.5)",
                    "design_reason": "Hook text appears with handwriting effect for engagement"
                }},
                {{
                    "time": 4.0,
                    "action": "Build neural network diagram with staggered reveal",
                    "manim_objects": "layers = VGroup(*[VGroup(*[Circle(0.2, color=c) for _ in range(n)]).arrange(DOWN, buff=0.3) for n, c in [(3, BLUE_D), (5, BLUE_C), (4, BLUE_B), (2, TEAL)]]).arrange(RIGHT, buff=1.5)",
                    "animation": "self.play(LaggedStartMap(DrawBorderThenFill, layers, lag_ratio=0.05), run_time=2)",
                    "design_reason": "Network nodes appear in a wave from left to right, giving a sense of data flow direction"
                }}
            ]
        }}
    ]
}}"""


def design_visuals(plan: dict, scene_durations: list[float] | None = None, model: str = "claude-sonnet-4-20250514") -> dict:
    """Create a detailed visual blueprint for each scene.

    Args:
        plan: The scene plan from planner.py.
        scene_durations: Audio durations per scene (from voice generation).
        model: The Claude model to use.

    Returns:
        A dict with visual blueprints for each scene.
    """
    client = anthropic.Anthropic()

    scenes_text = ""
    for i, scene in enumerate(plan["scenes"]):
        dur = scene_durations[i] if scene_durations and i < len(scene_durations) else 20.0
        scenes_text += f"\n### Scene {scene['id']} (target duration: {dur:.1f}s)\n"
        scenes_text += f"**Narration:** {scene['narration']}\n"
        scenes_text += f"**Animation description:** {scene['animation_description']}\n"

    prompt = f"""Design the visual blueprint for this educational video.

**Title:** {plan['title']}
**Topic:** {plan['topic']}

## Scenes
{scenes_text}

For each scene, think carefully about:
- What is the MOST VISUALLY COMPELLING way to reveal this concept?
- How can the visuals BUILD understanding, not just illustrate?
- Where should I use LaggedStartMap, DrawBorderThenFill, Indicate, color gradients?
- Can I show real numbers, actual computations, or data flowing?
- What would 3Blue1Brown do here?

Create a detailed visual blueprint for each scene."""

    response = client.messages.create(
        model=model,
        max_tokens=8192,
        system=VISUAL_DESIGNER_PROMPT,
        messages=[{"role": "user", "content": prompt}],
    )

    raw = response.content[0].text.strip()
    if raw.startswith("```"):
        raw = raw.split("\n", 1)[1].rsplit("```", 1)[0]

    import json
    return json.loads(raw)
