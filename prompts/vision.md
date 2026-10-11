You are reviewing rendered frames from an animated explainer Short. Each image
is one frame taken from the middle of one narration segment, in order. Judge
whether the visuals genuinely teach what is being said.

## The narration per segment

{{SEGMENTS_JSON}}

## What to flag (substance only)

1. DECORATION: the visual has no meaningful relationship to what the narration
   is saying at that moment — shapes for the sake of shapes.
2. MISMATCH: the visual contradicts the narration (wrong quantity, wrong
   direction, wrong element highlighted).
3. UNREADABLE: text too small to read on a phone, elements crowded together,
   overlapping elements, or content cut off by the frame edge.
4. EMPTY: the screen is (nearly) blank while the narration makes a substantive
   point that needed showing, or a single small element floats in a mostly
   empty frame.
5. DISCONNECTED: elements that should visibly align or touch do not — dots
   that should sit on a curve floating beside it, a "connecting" line missing
   its points, a reconstruction that ignores its samples.

Do NOT flag: style, colors, beauty, minor spacing, a "hold" frame that
deliberately keeps the previous visual while the narration restates.

## Output

Reply with ONLY a JSON object, no markdown fence:

{
  "ok": true or false,
  "issues": [
    {"segment": 3, "problem": "one concrete sentence: what is wrong and what should be shown instead"}
  ]
}

Set ok to false only if there are 2 or more serious issues (decoration,
mismatch, or unreadable text). A single minor issue: ok true, still list it.
