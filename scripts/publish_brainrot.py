"""Publish today's freshly generated Trevor video to Instagram as a Reel.

    python3 scripts/publish_brainrot.py JOB_ID          # post for real
    python3 scripts/publish_brainrot.py JOB_ID --dry    # everything except the HTTP posts

No queue: the video is generated minutes earlier in the same workflow run.
Routing: posts 1-10 of the calendar month via Upload-Post, 11-30 via
bundle.social (the *_BR accounts), beyond that skip the day.
Graceful fallback: if the selected provider raises an HTTP quota/limit error
(402, 429) or signals exhaustion in the response body, the script automatically
retries with the other provider before giving up.
Override: set UPLOAD_POST_DISABLED_BR=true in .env to force bundle.social.
Posted-today guard makes duplicate triggers harmless. Exit 0 posted/skipped, 1 failure.
"""
import argparse
import json
import sys
import urllib.error
import urllib.request
from datetime import date, datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))
from publish_daily import load_env, multipart, _is_quota_error, _call_provider  # noqa: E402

LOG = ROOT / "data" / "state" / "br_publish_log.json"
UPLOAD_POST_LIMIT = 10
BUNDLE_LIMIT = 20
UA = {"User-Agent": "shorts-pipeline/0.1"}


def caption(meta):
    tags = " ".join(meta.get("hashtags", [])[:6])
    text = f"{meta.get('title', '')}\n\n{meta.get('description', '')}\n\n{tags}".strip()
    return text[:2100]


def post_upload_post(env, video, meta, dry):
    fields = [("user", env["UPLOAD_POST_PROFILE_BR"]),
              ("platform[]", "instagram"),
              ("media_type", "REELS"),
              ("title", caption(meta))]
    if dry:
        print(f"  [dry] would POST {video.stat().st_size // 1024} KB via upload-post (instagram/reel)")
        return {"ok": True, "dry": True}
    body, ctype = multipart(fields, "video", video)
    req = urllib.request.Request(
        "https://api.upload-post.com/api/upload", data=body,
        headers={"Authorization": f"Apikey {env['UPLOAD_POST_API_KEY_BR']}",
                 "Content-Type": ctype, **UA})
    with urllib.request.urlopen(req, timeout=900) as r:
        resp = json.loads(r.read())
    print(f"  upload-post response: {json.dumps(resp)[:400]}")
    ok = bool(resp.get("success", resp.get("ok", False))) or "error" not in resp
    return {"ok": ok, "response": resp}


def post_bundle_social(env, video, meta, dry):
    key, team = env["BUNDLE_SOCIAL_API_KEY_BR"], env["BUNDLE_SOCIAL_TEAM_ID_BR"]
    if dry:
        print(f"  [dry] would upload {video.stat().st_size // 1024} KB via bundle.social (instagram/reel)")
        return {"ok": True, "dry": True}
    body, ctype = multipart([("teamId", team)], "file", video)
    req = urllib.request.Request("https://api.bundle.social/api/v1/upload", data=body,
                                 headers={"x-api-key": key, "Content-Type": ctype, **UA})
    with urllib.request.urlopen(req, timeout=900) as r:
        up = json.loads(r.read())
    upload_id = up.get("id") or up.get("uploadId")
    if not upload_id:
        return {"ok": False, "error": f"no upload id: {json.dumps(up)[:300]}"}
    post = {
        "teamId": team,
        "status": "SCHEDULED",
        "postDate": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
        "socialAccountTypes": ["INSTAGRAM"],
        "data": {"INSTAGRAM": {"type": "REEL", "text": caption(meta),
                               "uploadIds": [upload_id]}},
    }
    req = urllib.request.Request("https://api.bundle.social/api/v1/post",
                                 data=json.dumps(post).encode(),
                                 headers={"x-api-key": key,
                                          "Content-Type": "application/json", **UA})
    with urllib.request.urlopen(req, timeout=300) as r:
        resp = json.loads(r.read())
    print(f"  bundle.social response: {json.dumps(resp)[:400]}")
    return {"ok": True, "response": resp}


def _provider_sequence(counts, env):
    """Return the ordered list of (provider_name, poster_fn) to try.

    - If UPLOAD_POST_DISABLED_BR=true in the environment, upload-post is skipped
      entirely (the free quota is known to be exhausted for this month).
    - Otherwise the normal monthly-count gate applies: upload-post first until
      its limit is reached, then bundle.social.
    - Each entry is tried in turn; on a quota/limit error the next is attempted.
    """
    disabled = env.get("UPLOAD_POST_DISABLED_BR", "").lower() in ("1", "true", "yes")

    sequence = []
    if not disabled and counts["upload_post"] < UPLOAD_POST_LIMIT:
        sequence.append(("upload_post", post_upload_post))
    if counts["bundle_social"] < BUNDLE_LIMIT:
        sequence.append(("bundle_social", post_bundle_social))
    # Reverse-fallback: if bundle.social is primary but hits a quota error,
    # add upload-post as a last resort (unless it is disabled).
    if not disabled and sequence and sequence[0][0] == "bundle_social":
        if counts["upload_post"] < UPLOAD_POST_LIMIT:
            sequence.append(("upload_post", post_upload_post))
    return sequence


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("job_id")
    ap.add_argument("--dry", action="store_true")
    args = ap.parse_args()
    env = load_env()

    log = json.loads(LOG.read_text(encoding="utf-8")) if LOG.exists() else {"posts": []}
    today = date.today().isoformat()
    if any(p.get("ok") and p.get("date") == today for p in log["posts"]):
        print(f"already posted today ({today}), nothing to do")
        return 0

    folder = ROOT / "data" / "brainrot" / args.job_id
    video = folder / "final.mp4"
    meta = json.loads((folder / "metadata.json").read_text(encoding="utf-8"))
    print(f"publishing: {meta.get('title')!r}")

    month = today[:7]
    counts = {"upload_post": 0, "bundle_social": 0}
    for p in log["posts"]:
        if p.get("ok") and p.get("date", "").startswith(month):
            counts[p["provider"]] += 1

    sequence = _provider_sequence(counts, env)

    if not sequence:
        print(f"SKIP: both monthly free quotas used ({counts})")
        return 0

    print(f"provider sequence: {[p for p, _ in sequence]} (this month so far: {counts})")
    print(f"caption:\n{caption(meta)}\n")

    if args.dry:
        provider, poster = sequence[0]
        print(f"provider: {provider}")
        _call_provider(provider, poster, env, video, meta, dry=True)
        return 0

    result = None
    provider = None
    for attempt_provider, attempt_poster in sequence:
        print(f"  trying provider: {attempt_provider}")
        attempt_result, quota_hit = _call_provider(
            attempt_provider, attempt_poster, env, video, meta, dry=False)
        if attempt_result.get("ok"):
            result = attempt_result
            provider = attempt_provider
            break
        # Log the failed attempt for visibility.
        log["posts"].append({
            "date": today,
            "time": datetime.now().isoformat(timespec="seconds"),
            "provider": attempt_provider,
            "job": args.job_id,
            "title": meta.get("title"),
            "ok": False,
            "detail": {k: v for k, v in attempt_result.items() if k != "ok"},
        })
        if quota_hit:
            print(f"  {attempt_provider} quota exhausted — falling back to next provider")
            continue
        # Non-quota failure: stop immediately, do not waste the fallback.
        print(f"  {attempt_provider} failed with a non-quota error — not falling back")
        result = attempt_result
        provider = attempt_provider
        break

    if result is None:
        print("all providers exhausted")
        result = {"ok": False, "error": "all providers exhausted"}
        provider = "none"

    log["posts"].append({"date": today, "time": datetime.now().isoformat(timespec="seconds"),
                         "provider": provider, "job": args.job_id,
                         "title": meta.get("title"), "ok": result.get("ok", False),
                         "detail": {k: v for k, v in result.items() if k != "ok"}})
    LOG.parent.mkdir(parents=True, exist_ok=True)
    LOG.write_text(json.dumps(log, indent=2), encoding="utf-8")
    return 0 if result.get("ok") else 1


if __name__ == "__main__":
    sys.exit(main())
