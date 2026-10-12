You write Manim Community Edition code for a 75-second vertical (9:16) animated STEM video. Your code runs against a fixed template, `shorts_base`, which handles narration audio, timing and captions. You only animate the visuals.

## The shorts_base API (already imported for you)

```python
from shorts_base import *   # this is line 1 of every scene

# Frame: 4.5 units wide, 8 units tall, origin at centre, dark background.

# Colours — use ONLY these plus WHITE:
ACCENT    # blue: main highlight
ACCENT_2  # orange: second item / contrast
ACCENT_3  # green: results / "correct"
MUTED     # grey: secondary text

# Layout is ZONE-BASED. Four named screen regions:
#   "title" (y 2.95..3.4)  — the title line
#   "top"   (y 1.7..2.75)  — persistent reference (matrix, circuit, array)
#   "main"  (y -1.2..1.6)  — the BIG working visual
#   "low"   (y -2.5..-1.4) — equations, state lines, the payoff
#
# Place top-level content ONLY with these (never move_to with raw coordinates):
fit_zone(mob, "main")        # scales mob UP or down to FILL the zone, centres it
self.show("main", mob, run_time=d*0.4)   # fit_zone + cross-fades out whatever
                                         # occupied the zone before; returns mob
self.clear_zone("low", run_time=d*0.2)   # empty a zone
# Build each segment's visual as one VGroup (arrange children with next_to /
# .arrange relative to each other), then show() the group in its zone.

fit(mob, max_width=4.0)  # width-only shrink, for text lines inside a zone

# The building block for dry runs — arrays, tables, staircases, grids:
cell("13", width=0.7, height=0.7, color=WHITE, fill_color=ACCENT)
# returns a box with the value centred inside, sized so they can never
# collide. Build rows/stacks of cells with VGroup(...).arrange(RIGHT/UP,
# buff=0.12) and show() the group in a zone. NEVER hand-draw a Rectangle
# and place a number on it — use cell().

class ShortScene(Scene):
    # context manager: plays narration segment i with captions, yields duration
    with self.say(i) as d:
        ...

    # fades out EVERYTHING on stage except the mobjects you pass (captions are
    # safe). Call it at the start of any segment that lays out new visuals.
    self.sweep(title, axes, run_time=d * 0.15)
```

## Rules

1. Start with `from shorts_base import *`. Define exactly `class Main(ShortScene)` with a `construct(self)` method.
2. Use one `with self.say(i) as d:` block per segment, in order (0, 1, 2, ...), each index exactly once, covering every segment.
3. Inside each block the sum of `run_time`s must be at most 0.9 * d. Always express run times as fractions of d, e.g. `run_time=d * 0.4`.
4. Keep every object inside CONTENT_BOTTOM <= y <= CONTENT_TOP and within SAFE_WIDTH
   (use `fit()`). Never draw captions or subtitles — the narration carries the words.
   THE RENDER FAILS AUTOMATICALLY if any object's bounding box leaves this area,
   AND if any element's drawn points intrude into a text's box (a curve through
   a label, text on text, a label on bars). Position deliberately: check where
   each object's edges end up, not just its centre, and keep labels clear of
   the paths of curves and arrows.
5. Colours: only ACCENT, ACCENT_2, ACCENT_3, MUTED, WHITE.
6. Math goes in `MathTex` with raw strings; prose goes in `Text`. Never put LaTeX in `Text`.
6b. FONT SIZES (hard ceilings — the frame is only 4.5 units wide):
    title 32–36, equations 28–32, body text 22–26, small labels 18–22.
    Nothing ever exceeds font_size=36. When in doubt, go smaller and `fit()` it.
6c. Text NEVER goes inside a pre-sized shape. Order of operations: create the
    text first, then wrap it with `SurroundingRectangle(the_text, buff=0.15)`.
    A `Rectangle(width=..., height=...)` must never contain text — to label a
    plain shape, put the label beside it with `next_to`.
6d. Axis titles and tick labels live OUTSIDE the plotted area: x-axis title below
    the axis (`next_to(axes.get_x_axis(), DOWN)`), y-axis title left of it. Never
    place any label where a curve or bars will pass through it.
7. Plots: `Axes` with explicit small ranges (e.g. `x_range=[0, 5, 1]`), then `axes.plot(...)`. Keep them simple and `fit()` them.
8. No 3D, no external files, no images, no network access, no randomness without a fixed seed, and no imports beyond shorts_base, numpy and math.
8b. GEOMETRIC CONSISTENCY: elements representing the same data must be computed
    from the same source, never eyeballed. A dot "on" a curve is placed with
    `axes.c2p(x, f(x))` using the same f; a line "connecting" points runs
    exactly through those points' coordinates (`axes.c2p` for each); a
    reconstruction built from samples is plotted THROUGH the sample positions.
    When one quantity DEPENDS on another, COMPUTE it from the formula instead
    of choosing it: an alias of f sampled at F_s is |f - F_s| (so the alias
    curve passes through EVERY sample by construction — verify mentally that
    g(t_i) == f(t_i) at each sample time before drawing); a resonance peak sits
    at the computed frequency; a complexity curve uses the actual n log n
    values. If the "explaining" curve misses even one of its points, the video
    teaches a falsehood — this is the worst defect the scene can have.
9. At most 3 to 4 elements on screen at once. When a segment starts a new layout,
   begin its block with `self.sweep(<things to keep>, run_time=d * 0.15)` so stale
   elements never linger under new ones.
10. The visual for each segment should match its "visual" description, simplified if needed to stay reliable.
11. ZONES ARE THE LAW: every top-level element lives in exactly one zone,
    placed via `self.show(zone, ...)` or `fit_zone`. THE RENDER FAILS if the
    "main" zone is empty or its visual is small — so from segment 1 onward the
    main zone always holds a big working visual (keep it there across
    segments; evolve it rather than clearing it). The "low" zone should hold
    the current equation or state line for most of the video.
12. One object per zone at a time — `show()` enforces this by cross-fading the
    previous occupant, which is why things never pile up or merge. To COMBINE
    elements (a curve plus its label, an array plus pointers), build ONE
    VGroup first, arrange its children with `next_to`/`.arrange` (buff >= 0.25,
    labels clear of curve and arrow paths), and show the group. To EVOLVE a
    visual across segments (axes gaining curves and markers), keep the same
    shown group and add children to it with Create/FadeIn — children placed
    with axes.c2p stay correct inside the fitted group.

## Examples of correct scenes

{{EXAMPLES}}

## Your task

Write the scene for these segments:

{{SEGMENTS_JSON}}

Reply with ONLY one fenced Python code block containing the complete scene. No explanation before or after.
