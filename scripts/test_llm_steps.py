"""Quick smoke test of the harness LLM steps (no render): topic -> script -> factcheck."""
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
import pipeline_test as p

topic = p.step_topic({"topics": []}, None, None)
print("TOPIC:", json.dumps(topic, indent=2))

script = p.step_script(topic)
words = sum(len(s["narration"].split()) for s in script["segments"])
print(f"SCRIPT: {len(script['segments'])} segments, {words} words")
for s in script["segments"]:
    print("  -", s["narration"])

fc = p.step_factcheck(topic, script)
print("FACTCHECK ok:", fc.get("ok"), "| issues:", fc.get("issues"))

meta = p.step_metadata(topic, fc.get("segments") or script["segments"])
print("METADATA:", json.dumps(meta, indent=2))
