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

# Named screen zones (y_min, y_max); x always spans the safe width. Placing
# content with fit_zone/show guarantees it fills its region and never strays
# into a neighbour — layout by construction, not by eyeballing coordinates.
ZONES = {
    "title": (2.95, 3.4),   # the video's title line
    "top":   (1.7, 2.75),   # persistent reference: matrix, circuit, array
    "main":  (-1.2, 1.6),   # the big working visual
    "low":   (-2.5, -1.4),  # equations, state lines, payoff
}


def zone_box(name):
    y0, y1 = ZONES[name]
    return (0.0, (y0 + y1) / 2, SAFE_WIDTH, y1 - y0)


def fit_zone(mob, name, fill=0.9, max_up=1.5):
    """Scale mob (up to `max_up`x, or down as needed) to fill `fill` of the
    zone and centre it there. The cure for both spillover and
    tiny-floating-element emptiness, without ballooning single text lines."""
    cx, cy, w, h = zone_box(name)
    scale = min(w * 0.94 / max(mob.width, 1e-6),
                h * fill / max(mob.height, 1e-6),
                max_up)
    mob.scale(scale)
    mob.move_to([cx, cy, 0])
    return mob


def fit(mob, max_width=SAFE_WIDTH):
    """Shrink a mobject to fit the safe width. Returns it for chaining."""
    if mob.width > max_width:
        mob.scale_to_fit_width(max_width)
    return mob


def cell(label, width=0.7, height=0.7, color=WHITE, text_color=WHITE,
         font_size=24, fill_color=None):
    """A box with a value inside, sized so they can never collide — the
    building block for arrays, tables, staircases and grids in dry runs.
    `label` may be a string (rendered as MathTex) or a ready mobject."""
    txt = label if isinstance(label, Mobject) else MathTex(str(label),
                                                           font_size=font_size)
    txt.set_color(text_color)
    max_w, max_h = width - 0.2, height - 0.2
    if txt.width > max_w or txt.height > max_h:
        txt.scale(min(max_w / txt.width, max_h / txt.height))
    box = Rectangle(width=width, height=height, color=color, stroke_width=2)
    if fill_color is not None:
        box.set_fill(fill_color, opacity=0.25)
    txt.move_to(box)
    return VGroup(box, txt)


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
            for m in doomed:
                for z, occ in list(getattr(self, "_zone_occupants", {}).items()):
                    if occ is m:
                        self._zone_occupants.pop(z, None)

    def show(self, zone, mob, run_time=0.8, anim=None):
        """Place mob in a zone: auto-fit to fill it, and cross-fade out
        whatever occupied the zone before — replacement is managed, so old
        and new content can never pile up or 'merge'. Returns mob."""
        if not hasattr(self, "_zone_occupants"):
            self._zone_occupants = {}
        # a mobject moving between zones leaves its old zone's record
        for z, occ in list(self._zone_occupants.items()):
            if occ is mob:
                self._zone_occupants.pop(z)
        fit_zone(mob, zone)
        old = self._zone_occupants.get(zone)
        anims = [anim if anim is not None else FadeIn(mob)]
        if old is not None and old is not mob:
            anims.append(FadeOut(old))
        self.play(*anims, run_time=run_time)
        self._zone_occupants[zone] = mob
        return mob

    def clear_zone(self, zone, run_time=0.4):
        old = getattr(self, "_zone_occupants", {}).pop(zone, None)
        if old is not None:
            self.play(FadeOut(old), run_time=run_time)

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
        """Every Text/MathTex/Tex in the scene, at ANY nesting depth —
        labels buried deep inside composed groups still deserve clear space."""
        out = []

        def walk(m):
            if isinstance(m, (Text, MathTex, Tex)):
                out.append(m)
                return  # glyph submobjects are the text itself
            for sub in m.submobjects:
                walk(sub)

        for m in self.mobjects:
            walk(m)
        return out

    def _check_overlaps(self, seg_index):
        """No other object's drawn points may intrude into a text's box.
        Catches curves through labels, text on text, labels on bars."""
        texts = self._text_mobjects()
        for text in texts:
            if not text.family_members_with_points():
                continue
            x0, x1 = text.get_left()[0] - self._TEXT_PAD, text.get_right()[0] + self._TEXT_PAD
            y0, y1 = text.get_bottom()[1] - self._TEXT_PAD, text.get_top()[1] + self._TEXT_PAD
            for other in self.mobjects:
                if other is text:
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

    def _check_fullness(self, seg_index):
        """The main zone must hold a substantial visual (segment 1 onward).
        An empty or tiny-floating-element frame fails the render."""
        if seg_index == 0:
            return  # the hook/title segment may be sparse
        _, cy, zw, zh = zone_box("main")
        y0, y1 = ZONES["main"]
        # union bounding box of everything touching the main zone — content
        # often enters as several siblings (arrows, dots, labels)
        xs, ys = [], []
        for m in self.mobjects:
            if not m.family_members_with_points():
                continue
            try:
                top, bottom = m.get_top()[1], m.get_bottom()[1]
                left, right = m.get_left()[0], m.get_right()[0]
            except Exception:
                continue
            if bottom > y1 or top < y0:
                continue  # doesn't touch the main zone
            xs += [left, right]
            ys += [bottom, top]
        best_w = (max(xs) - min(xs)) if xs else 0.0
        best_h = (max(ys) - min(ys)) if ys else 0.0
        if best_w == 0:
            self._violations.append(
                f"segment {seg_index}: the MAIN zone (y {y0} to {y1}) is empty "
                "— the working visual must live there (use fit_zone/show)")
        elif best_w < 0.45 * zw and best_h < 0.42 * zh:
            # one sparse beat (a progressive reveal) is fine; a sparse VIDEO
            # is the defect — fail only from the second undersized segment on
            self._small_segments = getattr(self, "_small_segments", [])
            self._small_segments.append(seg_index)
            if len(self._small_segments) >= 2:
                self._violations.append(
                    f"segments {self._small_segments}: the main visual stays too "
                    f"small ({best_w:.1f}x{best_h:.1f} in a {zw:.1f}x{zh:.1f} zone) "
                    "— scale the working visual up with fit_zone(mob, 'main')")

    def _run_checks(self, seg_index):
        self._check_bounds(seg_index)
        self._check_overlaps(seg_index)
        self._check_fullness(seg_index)
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
