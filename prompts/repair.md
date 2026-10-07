You wrote Manim code for a short video and it failed. Fix it. The template (`shorts_base`) and all rules are unchanged — restated below.

## The error

```
{{ERROR}}
```

## The failing code

```python
{{CODE}}
```

## The segments it must cover

{{SEGMENTS_JSON}}

## Rules (unchanged)

1. Start with `from shorts_base import *`. Define exactly `class Main(ShortScene)` with `construct(self)`.
2. One `with self.say(i) as d:` block per segment, in order, each index exactly once, covering every segment.
3. Sum of `run_time`s inside each block at most 0.9 * d, expressed as fractions of d.
4. Everything inside CONTENT_BOTTOM (-2.1) <= y <= CONTENT_TOP (3.4) and within SAFE_WIDTH (use `fit()`). Never draw captions.
5. Colours: only ACCENT, ACCENT_2, ACCENT_3, MUTED, WHITE.
6. Math in `MathTex` (raw strings), prose in `Text`, never LaTeX in `Text`.
   Font ceilings: title 32–36, equations 28–32, body 22–26, labels 18–22; never above 36.
   Text first, then `SurroundingRectangle(text, buff=0.15)` — text never goes inside a
   pre-sized Rectangle; label plain shapes beside them with `next_to`.
   Axis titles sit outside the plotted area (below the x-axis, left of the y-axis),
   never where a curve passes.
7. Plots: `Axes` with explicit small ranges, then `axes.plot(...)`.
8. No 3D, external files, images, network, unseeded randomness, or imports beyond shorts_base, numpy and math.
9. At most 3 to 4 elements on screen at once. Start a segment that lays out new
   visuals with `self.sweep(<things to keep>, run_time=d * 0.15)`, which fades out
   everything else on stage (captions are safe).
   The render FAILS automatically if any object's bounding box leaves the content
   area, and the error names the segment and the offending edges — fix exactly those.
10. Lay the frame out in vertical bands (title y≈3.1, persistent reference y≈1.8–2.6,
    working visual y≈-0.8–1.5, equations/labels y≈-1.3–-2.0) and never put two
    visible objects in one band unless positioned together with `next_to`/`arrange`.

## How to fix

- Find the cause of the error and fix it properly; do not just delete the feature unless it breaks a rule.
- If the error is about a Manim API (wrong argument, missing method), use a simpler, more standard call.
- If the error points at a fragile construct (complex updaters, unusual mobjects), replace it with a simpler visual that still matches the segment.
- Return the COMPLETE corrected file, not a diff.

Reply with ONLY one fenced Python code block containing the complete corrected scene. No explanation.
