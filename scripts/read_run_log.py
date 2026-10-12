"""Print the tail of the Generate step from the downloaded run-log zip."""
import sys
import zipfile

z = zipfile.ZipFile("/tmp/runlog/logs.zip")
print("all files:", z.namelist())
pick = sys.argv[1] if len(sys.argv) > 1 else None
if pick:
    data = z.read(pick).decode(errors="replace")
    keys = ("topic:", "fail", "FAILED", "attempt", "storyboard", "vision",
            "Error", "error", "Traceback", "gave up", "queued:")
    hits = [ln for ln in data.splitlines()
            if any(k in ln for k in keys) and "git" not in ln and "INFO:" not in ln]
    print("\n".join(hits[-40:]))
