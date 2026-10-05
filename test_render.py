import json, time, urllib.request

code = open("test_scene.py", encoding="utf-8").read()
body = json.dumps({"code": code, "scene": "Main", "job_id": "test1"}).encode()
req = urllib.request.Request(
    "http://localhost:8000/render",
    data=body,
    headers={"Content-Type": "application/json"},
)
start = time.time()
print(urllib.request.urlopen(req, timeout=1000).read().decode())
print(f"took {time.time() - start:.1f}s")