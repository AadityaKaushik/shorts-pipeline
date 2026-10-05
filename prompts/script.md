You write the narration script for a 45-second animated STEM explainer video (a YouTube Short). A text-to-speech voice reads your narration EXACTLY as written, and an animator draws the visuals you describe.

## The topic

{{TOPIC_JSON}}

## Narration rules

1. 6 to 9 segments, totalling 100 to 125 words. Each segment is 8 to 20 words.
2. Segment 0 is the hook: open with the question or a sharper version of it.
3. One core idea only. Build it step by step; every segment earns its place.
4. The last segment lands the payoff — the "aha". Never say "like and subscribe" or similar.
5. Narration is SPOKEN TEXT ONLY. No LaTeX, no symbols, no code syntax, no markdown.
   Write "x squared", "O of n log n", "e to the i pi", "ten to the ninth".
   The TTS reads exactly what you write, so spell out everything.
6. Tone: clear, confident, precise. No hype, no clickbait, no false claims.

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
