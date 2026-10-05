"""Shared template for every Short. Generated scenes start with:
    from shorts_base import *
"""
import json
from contextlib import contextmanager
from pathlib import Path

from manim import *

# 9:16 frame: 4.5 units wide, 8 units tall, origin at the centre
config.frame_height = 8
config.frame_width = 4.5
config.background_color = "#0f1117"

# Palette
ACCENT = "#4fc3f7"    # blue: main highlight
ACCENT_2 = "#ffb74d"  # orange: second item / contrast
ACCENT_3 = "#81c784"  # green: results / "correct"
MUTED = "#9e9e9e"     # grey: secondary text

# Layout. YouTube's own buttons and title cover the bottom edge (below about
# y=-3.0) and the right edge, so content and captions stay above/inside that.
# Content gets the band CONTENT_BOTTOM..CONTENT_TOP; captions sit alone at
# CAPTION_Y, between the content and YouTube's bottom overlay.
SAFE_WIDTH = 4.0
CONTENT_TOP = 3.4
CONTENT_BOTTOM = -2.1
CAPTION_Y = -2.75
MAX_CAPTION_CHARS = 20
MAX_CAPTION_WORDS = 4


def fit(mob, max_width=SAFE_WIDTH):
    """Shrink a mobject to fit the safe width. Returns it for chaining."""
    if mob.width > max_width:
        mob.scale_to_fit_width(max_width)
    return mob


def _estimate_words(seg):
    words = seg["text"].split()
    total = sum(len(w) for w in words) or 1
    out, acc = [], 0
    for w in words:
        s = seg["duration"] * acc / total
        acc += len(w)
        out.append({"w": w, "s": s, "e": seg["duration"] * acc / total})
    return out


def _caption_chunks(seg):
    words = seg.get("words") or _estimate_words(seg)
    chunks, cur = [], []
    for w in words:
        candidate = " ".join(x["w"] for x in cur + [w])
        if cur and (len(candidate) > MAX_CAPTION_CHARS or len(cur) >= MAX_CAPTION_WORDS):
            chunks.append(cur)
            cur = []
        cur.append(w)
        if w["w"] and w["w"][-1] in ".,!?;:":
            chunks.append(cur)
            cur = []
    if cur:
        chunks.append(cur)
    return [(" ".join(x["w"] for x in c), c[0]["s"]) for c in chunks] or [("", 0.0)]


def _caption(text):
    cap = Text(text, font_size=26, weight=BOLD, color=WHITE)
    cap.set_stroke(BLACK, width=5, background=True)
    fit(cap)
    return cap.move_to(UP * CAPTION_Y)


class ShortScene(Scene):
    pad = 0.25  # short pause after each segment, in seconds

    # Bounds the frame-check enforces, with a small slack over the layout rules.
    _X_LIMIT = SAFE_WIDTH / 2 + 0.15
    _Y_TOP = CONTENT_TOP + 0.15
    _Y_BOTTOM = CONTENT_BOTTOM - 0.15

    def setup(self):
        data = json.loads(Path("narration.json").read_text(encoding="utf-8"))
        self.segments = data["segments"]
        self._violations = []

    def sweep(self, *keep, run_time=0.4):
        """FadeOut everything on stage except `keep` (captions are safe).

        Call at the start of a segment that lays out new visuals, so stale
        elements never linger under new ones.
        """
        keep_set = set(keep)
        doomed = [m for m in self.mobjects
                  if m not in keep_set and not getattr(m, "_is_caption", False)]
        if doomed:
            self.play(*[FadeOut(m) for m in doomed], run_time=run_time)

    def _check_bounds(self, seg_index):
        """Record any mobject outside the content area; the renderer fails the
        job on violations so the repair loop gets a precise, fixable error."""
        for m in self.mobjects:
            if getattr(m, "_is_caption", False) or not m.has_points():
                continue
            try:
                left, right = m.get_left()[0], m.get_right()[0]
                bottom, top = m.get_bottom()[1], m.get_top()[1]
            except Exception:
                continue
            problems = []
            if right > self._X_LIMIT:
                problems.append(f"right edge x={right:.2f} > {self._X_LIMIT:.2f}")
            if left < -self._X_LIMIT:
                problems.append(f"left edge x={left:.2f} < {-self._X_LIMIT:.2f}")
            if top > self._Y_TOP:
                problems.append(f"top y={top:.2f} > {self._Y_TOP:.2f}")
            if bottom < self._Y_BOTTOM:
                problems.append(f"bottom y={bottom:.2f} < {self._Y_BOTTOM:.2f} "
                                "(the caption area — content must stay above it)")
            if problems:
                self._violations.append(
                    f"segment {seg_index}: {type(m).__name__} out of frame: "
                    + "; ".join(problems))
        Path("bounds_violations.json").write_text(
            json.dumps(self._violations), encoding="utf-8")

    @contextmanager
    def say(self, i):
        """Play narration segment i with captions. Yields its duration."""
        seg = self.segments[i]
        dur = seg["duration"]
        start = self.renderer.time
        self.add_sound(seg["audio"])

        chunks = _caption_chunks(seg)
        starts = [s for _, s in chunks]
        off_screen = UP * 50
        caps = [_caption(text) for text, _ in chunks]
        for c in caps[1:]:
            c.move_to(off_screen)
        state = {"idx": 0}
        holder = VGroup(*caps)
        holder._is_caption = True

        def update(m):
            t = self.renderer.time - start
            idx = 0
            for k, s in enumerate(starts):
                if s <= t:
                    idx = k
            if idx != state["idx"]:
                caps[state["idx"]].move_to(off_screen)
                caps[idx].move_to(UP * CAPTION_Y)
                state["idx"] = idx

        holder.add_updater(update)
        self.add(holder)
        try:
            yield dur
        finally:
            remaining = dur + self.pad - (self.renderer.time - start)
            if remaining > 0.02:
                self.wait(remaining)
            holder.clear_updaters()
            self.remove(holder)
            self._check_bounds(i)