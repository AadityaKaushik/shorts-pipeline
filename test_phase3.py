import json, time, urllib.request

segments = [
    "Here's a trick a ten-year-old supposedly used to stun his teacher.",
    "Add up every number from one to a hundred.",
    "Write the list forwards, then write it again backwards underneath.",
    "Each column adds up to one hundred and one, and there are a hundred columns.",
    "That counts everything twice, so halve it: five thousand and fifty.",
    "And it works for any n: n times n plus one, all over two.",
]
body = json.dumps({
    "code": open("example_gauss.py", encoding="utf-8").read(),
    "scene": "Main",
    "job_id": "gauss",
    "segments": segments,
}).encode()
req = urllib.request.Request("http://localhost:8000/render", data=body,
                             headers={"Content-Type": "application/json"})
start = time.time()
print(json.dumps(json.loads(urllib.request.urlopen(req, timeout=1200).read()), indent=2))
print(f"took {time.time() - start:.1f}s")