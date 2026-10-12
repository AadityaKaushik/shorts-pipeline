"""Minimal caption probe: 1 segment, no visuals — captions should be the only
visible thing. Renders, then extracts a frame."""
import json
import subprocess
import urllib.request

code = '''from shorts_base import *

class Main(ShortScene):
    def construct(self):
        with self.say(0) as d:
            t = Text("Probe", font_size=36, color=ACCENT)
            self.show("title", t, run_time=d * 0.4, anim=Write(t))
            eq = MathTex(r"a^2+b^2=c^2", font_size=30)
            self.show("low", eq, run_time=d * 0.4)
'''
body = json.dumps({"code": code, "scene": "Main", "job_id": "capprobe",
                   "segments": ["Testing one two three, every word must appear on screen."],
                   "post": False}).encode()
req = urllib.request.Request("http://localhost:8000/render", data=body,
                             headers={"Content-Type": "application/json"})
print(json.loads(urllib.request.urlopen(req, timeout=600).read()))
subprocess.run(["bash", "scripts/grab_frame.sh", "capprobe", "1.5"])
