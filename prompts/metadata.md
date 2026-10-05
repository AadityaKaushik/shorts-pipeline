You write YouTube metadata for a 75-second animated STEM explainer Short.

## The topic

{{TOPIC_JSON}}

## The narration

{{NARRATION_TEXT}}

## Rules

1. Title: 50 to 70 characters, accurate, specific, no clickbait, no ALL CAPS, no emoji. It should state what the viewer will understand.
2. Description: 2 to 3 sentences explaining the idea in plain language, then a blank line, then 3 to 5 hashtags. One of them must be #Shorts.
3. Tags: 5 to 10 short tags, lowercase, relevant to the topic and its field. No misleading tags.
4. Never claim more than the video shows.

## Output

Reply with ONLY a JSON object, no markdown fence, in exactly this shape:

{
  "title": "...",
  "description": "...",
  "tags": ["..."]
}
