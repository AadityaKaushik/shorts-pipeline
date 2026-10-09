#!/bin/bash
# Extract one frame from a rendered video for visual checks.
# Usage: scripts/grab_frame.sh <job_id> <seconds> [out_name]
cd "$(dirname "$0")/.."
job="$1"; t="$2"; out="${3:-check}"
docker compose exec -T renderer python - "$job" "$t" "$out" <<'EOF'
import sys
import av
job, t, out = sys.argv[1], float(sys.argv[2]), sys.argv[3]
with av.open(f"/files/renders/{job}/final.mp4") as c:
    for f in c.decode(video=0):
        if f.time >= t:
            f.to_image().resize((405, 720)).save(f"/files/renders/{job}/{out}.png")
            print(f"saved {out}.png at t={f.time:.2f}")
            break
EOF
