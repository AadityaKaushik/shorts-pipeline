You pick one concept for a 75-second animated explainer video (a YouTube Short).

## Today's subject

The channel cycles through a fixed set of college subjects. Today's subject is:

**{{SUBJECT}}**

Pick ONE concept from inside this subject.

## Rules

1. ONE concept with ONE core idea whose WHY — the mechanism behind it — can be
   properly explained in about 75 seconds to someone who has NEVER studied this
   subject. Not a survey, not a definition: a single satisfying idea.
2. Do not repeat or closely paraphrase any topic in the history below.
3. THE HOOK IS THE MOST IMPORTANT FIELD. It must be a CONCRETE real-world
   scenario in 10 to 18 words — something the viewer has personally experienced
   or can instantly picture (an app, a device, money, traffic, a game, their
   phone). NOT an abstract question about the concept. The entire video will be
   built around this scenario.
   - Good: "You type 'teh' and your phone instantly knows you meant 'the'. How?"
   - Good: "Why does your camera flash need a moment before it can fire again?"
   - Bad: "What makes an algorithm run in linear time?" (abstract, assumes the concept)
   - Bad: "Let's explore eigenvalues." (not a scenario at all)
4. The idea must be visualisable with simple 2D animation: equations, labelled
   shapes, axes with curves, arrows, small graphs or trees, tables, short code.
   No photos, 3D, maps or real-world imagery.

## Topics already covered (do not repeat)

{{HISTORY}}

## Output

Reply with ONLY a JSON object, no markdown fence, in exactly this shape:

{
  "category": "the subject name, e.g. {{SUBJECT}}",
  "level": "university | high_school",
  "topic": "short topic title",
  "key_idea": "one or two sentences stating the single core idea",
  "hook": "the concrete real-world scenario, 10 to 18 words"
}
