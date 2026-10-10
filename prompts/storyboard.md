You are the visual director for a 75-second animated explainer Short. The
narration is FINAL — you design what appears on screen so that the visuals
genuinely TEACH, never decorate. A separate animator will implement your
storyboard literally in simple 2D animation.

## The topic

{{TOPIC_JSON}}

## The final narration (one segment = one spoken line)

{{SEGMENTS_JSON}}

## Step 1: choose the teaching strategy

Pick the ONE strategy that fits this concept best (or a named combination):

- **dry_run** — walk ONE concrete example through the structure step by step.
  The natural choice for algorithms, data structures, databases, networking,
  compilers: an actual array being binary-searched, an actual packet hopping
  routers, an actual string being parsed. The SAME example persists across
  segments; each segment advances it one step.
- **mechanism** — a cause-and-effect chain the viewer watches happen: current
  flowing, a gradient descending, a signal being sampled. Arrows and quantities
  that visibly change, each change caused by the previous one.
- **diagram_evolution** — one diagram/plot that BUILDS across segments: axes
  gain a curve, the curve gains a marker, the marker gains meaning. Never a
  new unrelated picture per segment.

## Step 2: storyboard every segment

For each narration segment, specify:

- "visual": a LITERAL layout instruction the animator can follow exactly —
  what elements, where (top band y≈1.8–2.6 for the persistent reference,
  main band y≈-0.8–1.5 for the working visual, lower band y≈-1.5–-2.4 for
  equations/labels), and what CHANGES this segment (one change at a time).
- "teaches": what the viewer understands from SEEING this that the narration
  alone cannot give. If your honest answer is "nothing", REDESIGN the visual —
  or mark it "hold" (see below). Never submit a visual that exists for its own sake.

## Hard rules

1. Vocabulary — the animator can ONLY draw: equations; short text labels; axes
   with plotted curves; arrows; circles, dots, rectangles (labelled); bars of
   given heights; small matrices/tables; small graphs or trees of labelled
   nodes; code snippets of 6 lines or fewer. NO icons, pictures or objects —
   a coin is a circle labelled H, a server is a rectangle labelled "server".
2. Continuity beats novelty: prefer the SAME structure evolving across many
   segments over new pictures. Specify explicitly what stays from the previous
   segment and what changes.
3. HOLD segments: for anchor/restate narration lines, say "hold" — keep the
   current visual, at most a highlight or pulse of the element being restated.
   Holds are valuable; use at least 2.
4. At most 3 to 4 elements visible at once; say explicitly when the stage
   clears and what survives.
5. Elements must NEVER overlap: labels sit beside or above what they label,
   never on a curve's path, never on other text. Positions you specify must
   respect this.
6. Numbers in dry runs must be real and consistent: if segment 3 searches
   index 4 of [2,5,8,11,14,17,20], segment 4 continues from exactly that state.

## Output

Reply with ONLY a JSON object, no markdown fence:

{
  "strategy": "dry_run | mechanism | diagram_evolution | <combination>",
  "running_example": "the single concrete example used throughout, if any",
  "segments": [
    {"narration": "copy the narration unchanged",
     "visual": "literal layout instruction with positions and the one change",
     "teaches": "what seeing this adds, or 'hold'"}
  ]
}
The segments array must have exactly the same number of entries as the narration.
