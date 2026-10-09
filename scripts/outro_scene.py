"""The channel outro: a ~5.5s end card rendered once and stitched onto every
video. Plain Scene (not ShortScene — no captions wanted): voiceover comes from
voice.wav in the job dir (made by render_outro.py), pure black background so
the logo's own black square blends in. Render via scripts/render_outro.py."""
import json as _json
from pathlib import Path as _Path

from manim import *

config.frame_height = 8
config.frame_width = 4.5
config.background_color = "#000000"

BRAND_BLUE = "#2e7bff"   # the play-triangle blue from the logo
YT_RED = "#e62117"
MUTED = "#9e9e9e"


class Outro(Scene):
    def construct(self):
        logo = ImageMobject("/assets/Logo/Logo_1.png")
        logo.scale_to_fit_width(2.1).move_to(UP * 2.2)

        hook = Text("Liked this one?", font_size=34, weight=BOLD, color=WHITE)
        hook.move_to(UP * 0.7)

        keep = Text("keep learning with", font_size=24, color=MUTED)
        name = Text("TheComputeClub", font_size=38, weight=BOLD,
                    color=BRAND_BLUE)
        if name.width > 3.7:
            name.scale_to_fit_width(3.7)
        channel = VGroup(keep, name).arrange(DOWN, buff=0.18).move_to(DOWN * 0.35)

        like = Text("LIKE", font_size=26, weight=BOLD, color=WHITE)
        like_pill = RoundedRectangle(corner_radius=0.3, width=1.6, height=0.62,
                                     color=WHITE, stroke_width=3)
        like_btn = VGroup(like_pill, like)

        sub = Text("SUBSCRIBE", font_size=26, weight=BOLD, color=WHITE)
        sub_pill = RoundedRectangle(corner_radius=0.3, width=2.3, height=0.62,
                                    fill_color=YT_RED, fill_opacity=1,
                                    stroke_width=0)
        sub_btn = VGroup(sub_pill, sub)
        for btn, label in ((like_btn, like), (sub_btn, sub)):
            label.move_to(btn[0])
        buttons = VGroup(like_btn, sub_btn).arrange(RIGHT, buff=0.35)
        buttons.move_to(DOWN * 1.8)

        # Voiceover: "Liked this one? Keep learning with The Compute Club —
        # hit like and subscribe!" Beats below are timed to that read.
        voice_dur = 5.0
        meta = _Path("voice.json")
        if meta.exists():
            voice_dur = _json.loads(meta.read_text())["duration"]
        if _Path("voice.wav").exists():
            self.add_sound("voice.wav")

        # 0.0-0.6  logo lands
        self.play(FadeIn(logo, scale=1.4), run_time=0.6, rate_func=smooth)
        # 0.6-1.3  "Liked this one?" writes while the voice asks it
        self.play(Write(hook), run_time=0.7)
        # 1.4-2.2  channel name during "keep learning with The Compute Club"
        self.wait(0.15)
        self.play(FadeIn(channel, shift=UP * 0.25), run_time=0.75)
        # 2.6-3.2  buttons pop in
        self.wait(0.35)
        self.play(GrowFromCenter(like_btn), GrowFromCenter(sub_btn),
                  run_time=0.6)
        # 3.4-4.1  the "click" lands on "hit like and subscribe"
        self.wait(0.2)
        ring = Circle(radius=0.2, color=YT_RED, stroke_width=5)
        ring.move_to(sub_btn)
        self.play(
            sub_btn.animate(rate_func=there_and_back).scale(0.88),
            ring.animate(rate_func=rush_from).scale(4.5).set_stroke(opacity=0),
            run_time=0.7,
        )
        self.remove(ring)
        # 4.1-4.6  LIKE flashes too
        self.play(like_pill.animate(rate_func=there_and_back)
                  .set_fill(BRAND_BLUE, opacity=1), run_time=0.5)
        # hold until the voice finishes, plus a beat
        elapsed = 4.6
        self.wait(max(voice_dur - elapsed, 0) + 0.4)
