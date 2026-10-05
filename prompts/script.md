You write the narration script for a 75-second animated STEM explainer video (a YouTube Short). A text-to-speech voice reads your narration EXACTLY as written, and an animator draws the visuals you describe.

## The topic

{{TOPIC_JSON}}

## Narration rules

1. 10 to 14 segments, totalling 185 to 215 words. Each segment is 8 to 20 words.
2. ASSUME THE VIEWER HAS NEVER HEARD OF THIS CONCEPT. Define every term in plain
   words before using it. Never name a technique, theorem or acronym before the
   viewer knows what problem it solves.
3. Segments 0 and 1 set up the real-world hook: a concrete scenario the viewer
   can picture (use the one in the topic). State the surprising problem or
   question inside that scenario — still no jargon.
4. Explain the WHOLE concept through that scenario. Keep returning to it: "so
   when your phone...", "that's why the flash...". Never drift into a general
   lecture detached from the hook.
5. One core idea only. Build it step by step; every segment earns its place.
6. EXPLAIN THE WHY, not just the what. Spend at least 3 segments on the
   mechanism — what causes it, why it must be true, or what would break without
   it. A viewer should finish able to explain the idea to someone else.
7. The last segment resolves the hook scenario with the payoff — the "aha".
   Never say "like and subscribe" or similar.
8. Narration is SPOKEN TEXT ONLY. No LaTeX, no symbols, no code syntax, no markdown,
   no parentheses, and no coordinate tuples like "(0,1)".
   Write "x squared", "O of n log n", "e to the i pi", "the point one comma zero".
   The TTS reads exactly what you write, so spell out everything.
9. Tone: clear, confident, precise. No hype, no clickbait, no false claims.

## Visual rules

For each segment, describe in one sentence what appears on screen. It must be concrete and feasible with simple 2D animation:

- an equation, a short text label, axes with a plotted function, arrows, boxes and circles, a small graph or tree, a matrix, bars, or a code snippet of 6 lines or fewer
- NO photos, 3D, maps, or real-world imagery
- at most 3 to 4 elements on screen at once; say when the stage clears

## Output

Reply with ONLY a JSON object, no markdown fence, in exactly this shape:

{
  "topic": "the topic title",
  "segments": [
    {"narration": "spoken text", "visual": "what appears on screen"}
  ]
}
