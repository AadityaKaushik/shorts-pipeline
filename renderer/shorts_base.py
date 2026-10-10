"""Shared template for every Short. Generated scenes start with:
    from shorts_base import *
"""
import json
from contextlib import contextmanager
from pathlib import Path

import numpy as np
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
# y=-3.0) and the right edge, so all content stays within these bounds.
# (Captions were removed 11 Oct 2026 — narration carries the words, and the
# freed strip extends the content area downward.)
SAFE_WIDTH = 4.0
CONTENT_TOP = 3.4
CONTENT_BOTTOM = -2.6


def fit(mob, max_width=SAFE_WIDTH):
    """Shrink a mobject to fit the safe width. Returns it for chaining."""
    if mob.width > max_width:
        mob.scale_to_fit_width(max_width)
    return mob


class ShortScene(Scene):
    pad = 0.5  # breathing pause after each segment, in seconds

    # Bounds the frame-check enforces, with a small slack over the layout rules.
    _X_LIMIT = SAFE_WIDTH / 2 + 0.15
    _Y_TOP = CONTENT_TOP + 0.15
    _Y_BOTTOM = CONTENT_BOTTOM - 0.15
    # Padding around text when checking that nothing intrudes into it.
    # (LaTeX bounding boxes already carry margin, so this stays small.)
    _TEXT_PAD = 0.04

    def setup(self):
        data = json.loads(Path("narration.json").read_text(encoding="utf-8"))
        self.segments = data["segments"]
        self._violations = []

    def sweep(self, *keep, run_time=0.4):
        """FadeOut everything on stage except `keep`.

        Call at the start of a segment that lays out new visuals, so stale
        elements never linger under new ones.
        """
        keep_set = set(keep)
        doomed = [m for m in self.mobjects if m not in keep_set]
        if doomed:
            self.play(*[FadeOut(m) for m in doomed], run_time=run_time)

    # ------------------------------------------------------------- checks

    def _check_bounds(self, seg_index):
        """Record any mobject outside the content area."""
        for m in self.mobjects:
            # has_points() is False for containers (Text, MathTex, VGroup) whose
            # points live in submobjects — check the whole family instead.
            if not m.family_members_with_points():
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
                problems.append(f"bottom y={bottom:.2f} < {self._Y_BOTTOM:.2f}")
            if problems:
                self._violations.append(
                    f"segment {seg_index}: {type(m).__name__} out of frame: "
                    + "; ".join(problems))

    @staticmethod
    def _label_of(m):
        s = getattr(m, "text", None) or getattr(m, "tex_string", None) or ""
        s = str(s).replace("\n", " ")
        return f" {s[:30]!r}" if s else ""

    def _text_mobjects(self):
        """Top-level texts, plus texts nested one level down in groups (a
        common pattern: VGroup(box, label))."""
        out = []
        for m in self.mobjects:
            if isinstance(m, (Text, MathTex, Tex)):
                out.append((m, m))
            elif isinstance(m, (VGroup, Group)):
                for sub in m.submobjects:
                    if isinstance(sub, (Text, MathTex, Tex)):
                        out.append((sub, m))
        return out

    def _check_overlaps(self, seg_index):
        """No other object's drawn points may intrude into a text's box.
        Catches curves through labels, text on text, labels on bars."""
        texts = self._text_mobjects()
        for text, owner in texts:
            if not text.family_members_with_points():
                continue
            x0, x1 = text.get_left()[0] - self._TEXT_PAD, text.get_right()[0] + self._TEXT_PAD
            y0, y1 = text.get_bottom()[1] - self._TEXT_PAD, text.get_top()[1] + self._TEXT_PAD
            for other in self.mobjects:
                if other is owner or other is text:
                    continue
                text_family = set(id(t) for t in text.family_members_with_points())
                for member in other.family_members_with_points():
                    # skip the text's own glyphs
                    if id(member) in text_family:
                        continue
                    # faint background elements (grids, watermark-weight lines)
                    # under text are fine — only visually solid ink counts
                    try:
                        if (member.get_stroke_opacity() < 0.5
                                and member.get_fill_opacity() < 0.5):
                            continue
                    except Exception:
                        pass
                    pts = member.points
                    if len(pts) == 0:
                        continue
                    inside = (pts[:, 0] > x0) & (pts[:, 0] < x1) \
                             & (pts[:, 1] > y0) & (pts[:, 1] < y1)
                    if bool(np.any(inside)):
                        self._violations.append(
                            f"segment {seg_index}: {type(member).__name__} overlaps "
                            f"the text{self._label_of(text)} — move the text or "
                            "the element so they do not intersect")
                        break
                else:
                    continue
                break

    def _run_checks(self, seg_index):
        self._check_bounds(seg_index)
        self._check_overlaps(seg_index)
        Path("bounds_violations.json").write_text(
            json.dumps(self._violations), encoding="utf-8")

    # ------------------------------------------------------------- narration

    @contextmanager
    def say(self, i):
        """Play narration segment i. Yields its duration in seconds."""
        seg = self.segments[i]
        dur = seg["duration"]
        start = self.renderer.time
        self.add_sound(seg["audio"])
        try:
            yield dur
        finally:
            remaining = dur + self.pad - (self.renderer.time - start)
            if remaining > 0.02:
                self.wait(remaining)
            self._run_checks(i)
