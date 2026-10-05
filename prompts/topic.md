You pick one topic for a 75-second animated STEM explainer video (a YouTube Short).

## Audience and level

- Mostly university level (about 85% of the time), occasionally high school (about 15%).
- Never trivia. The viewer should leave understanding one real idea they could meet in a course.
- Good examples: why eigenvectors only stretch, how attention weights are computed, why hash table lookups are O(1) on average, how an RC circuit charges, how TLS handshakes work.

## Rules

1. Pick ONE topic with ONE core idea whose WHY — the mechanism behind it — can be properly explained in about 75 seconds, not just stated.
2. Do not repeat or closely paraphrase any topic in the history below.
3. Do not use either of the two most recent categories: {{RECENT_CATEGORIES}}
4. The idea must be visualisable with simple 2D animation: equations, short labels, axes and plots, arrows, boxes, small graphs or trees, matrices, bars, or a code snippet of at most 6 lines. No photos, 3D, maps or real-world imagery.
5. The hook is a question of 10 words or fewer that makes the viewer curious.

## Topics already covered (do not repeat)

{{HISTORY}}

## Output

Reply with ONLY a JSON object, no markdown fence, in exactly this shape:

{
  "category": "ai_ml | math | physics | chemistry | electrical | mechanical | cs_algorithms | networking_it | web_dev | other_science",
  "level": "university | high_school",
  "topic": "short topic title",
  "key_idea": "one or two sentences stating the single core idea",
  "hook": "a question in 10 words or fewer"
}
