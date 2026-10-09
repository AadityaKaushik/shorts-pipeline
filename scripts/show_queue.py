"""Print each queued video's title, description and tags for review."""
import json
from pathlib import Path

QUEUE = Path(__file__).resolve().parent.parent / "data" / "queue"

for folder in sorted(QUEUE.iterdir()):
    if not folder.is_dir():
        continue
    m = json.loads((folder / "metadata.json").read_text(encoding="utf-8"))
    print(f"\n=== {folder.name}")
    print(f"title: {m.get('title')}")
    print(f"desc : {m.get('description', '')[:200]}")
    print(f"tags : {', '.join(m.get('tags', []))}")
