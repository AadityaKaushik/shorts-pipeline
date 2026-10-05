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

# Layout bounds — all content must stay inside:
SAFE_WIDTH = 4.0        # max width of anything
CONTENT_TOP = 3.4       # max y
CONTENT_BOTTOM = -2.1   # min y (captions live below; NEVER draw there)

fit(mob, max_width=SAFE_WIDTH)  # shrinks a mobject to fit the width; returns it

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
   (use `fit()`). Never draw captions or subtitles — the template does that.
   THE RENDER FAILS AUTOMATICALLY if any object's bounding box leaves this area,
   so position deliberately: check where each object's edges end up, not just
   its centre.
5. Colours: only ACCENT, ACCENT_2, ACCENT_3, MUTED, WHITE.
6. Math goes in `MathTex` with raw strings; prose goes in `Text`. Never put LaTeX in `Text`.
7. Plots: `Axes` with explicit small ranges (e.g. `x_range=[0, 5, 1]`), then `axes.plot(...)`. Keep them simple and `fit()` them.
8. No 3D, no external files, no images, no network access, no randomness without a fixed seed, and no imports beyond shorts_base, numpy and math.
9. At most 3 to 4 elements on screen at once. When a segment starts a new layout,
   begin its block with `self.sweep(<things to keep>, run_time=d * 0.15)` so stale
   elements never linger under new ones.
10. The visual for each segment should match its "visual" description, simplified if needed to stay reliable.
11. USE THE FULL FRAME, in vertical bands, so elements never overlap:
    - title band: y ≈ 3.1 (the title may stay for the whole video)
    - upper band: y ≈ 1.8 to 2.6 (a persistent reference: the matrix, the circuit, word boxes)
    - main band: y ≈ -0.8 to 1.5 (the working visual: plane, axes, diagrams)
    - lower band: y ≈ -1.3 to -2.0 (equations, labels, the payoff line)
12. NEVER place two visible objects in the same band at the same time unless they
    were laid out together (e.g. with `VGroup(...).arrange()` or `next_to`). Before
    writing into an occupied band, `FadeOut` or `Transform` what is there. Labels
    that belong to a plot go inside the plot's own band, positioned with `next_to`
    against the thing they label.

## Examples of correct scenes

{{EXAMPLES}}

## Your task

Write the scene for these segments:

{{SEGMENTS_JSON}}

Reply with ONLY one fenced Python code block containing the complete scene. No explanation before or after.
