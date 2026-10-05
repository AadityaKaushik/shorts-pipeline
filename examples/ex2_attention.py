from shorts_base import *


class Main(ShortScene):
    def construct(self):
        with self.say(0) as d:
            title = Text("Attention", font_size=36, color=ACCENT)
            title.move_to(UP * 3.1)
            sub = fit(Text("how transformers decide what matters",
                           font_size=22, color=MUTED))
            sub.next_to(title, DOWN, buff=0.25)
            self.play(Write(title), run_time=d * 0.5)
            self.play(FadeIn(sub, shift=UP * 0.2), run_time=d * 0.3)

        with self.say(1) as d:
            words = VGroup(*[Text(w, font_size=24) for w in ["the", "cat", "sat"]])
            boxes = VGroup(*[SurroundingRectangle(w, color=MUTED, buff=0.18,
                                                  corner_radius=0.08)
                             for w in words])
            items = VGroup(*[VGroup(b, w) for b, w in zip(boxes, words)])
            items.arrange(RIGHT, buff=0.45).move_to(UP * 2.2)
            vecs = VGroup()
            for item, nums in zip(items, [r"0.2 \\ 0.9", r"0.8 \\ 0.3", r"0.5 \\ 0.6"]):
                v = MathTex(r"\begin{bmatrix} " + nums + r" \end{bmatrix}",
                            font_size=22, color=MUTED)
                vecs.add(v.next_to(item, DOWN, buff=0.25))
            self.play(FadeOut(sub), FadeIn(items), run_time=d * 0.4)
            self.play(FadeIn(vecs, shift=UP * 0.2), run_time=d * 0.4)

        with self.say(2) as d:
            origin = DOWN * 0.3
            qa = Arrow(origin, origin + UP * 1.1 + RIGHT * 0.5, buff=0,
                       color=ACCENT, stroke_width=5)
            ka = Arrow(origin, origin + UP * 1.0 + RIGHT * 0.9, buff=0,
                       color=ACCENT_2, stroke_width=5)
            self.play(FadeOut(vecs), run_time=d * 0.2)
            self.play(GrowArrow(qa), GrowArrow(ka), run_time=d * 0.5)

        with self.say(3) as d:
            stray = Arrow(origin, origin + DOWN * 0.6 + LEFT * 1.3, buff=0,
                          color=MUTED, stroke_width=5)
            self.play(GrowArrow(stray), run_time=d * 0.5)

        with self.say(4) as d:
            eq = MathTex(r"q \cdot k = q_1 k_1 + q_2 k_2", font_size=30)
            eq.move_to(DOWN * 1.65)
            self.play(Write(eq), run_time=d * 0.6)

        with self.say(5) as d:
            big = MathTex("2.0", font_size=26, color=ACCENT_3)
            big.next_to(qa.get_end(), RIGHT, buff=0.2)
            small = MathTex("0.1", font_size=26, color=MUTED)
            small.next_to(stray.get_end(), DOWN, buff=0.15)
            self.play(FadeIn(big), run_time=d * 0.3)
            self.play(FadeIn(small), run_time=d * 0.3)

        with self.say(6) as d:
            scores = MathTex(
                r"\begin{bmatrix} 2 & 1 & 0 \\ 1 & 3 & 1 \\ 0 & 1 & 2 \end{bmatrix}",
                font_size=32)
            scores.move_to(UP * 0.2)
            self.sweep(title, items, run_time=d * 0.25)
            self.play(FadeIn(scores, shift=UP * 0.2), run_time=d * 0.45)

        with self.say(7) as d:
            self.play(Indicate(scores, color=ACCENT_2, scale_factor=1.05),
                      run_time=d * 0.5)

        with self.say(8) as d:
            soft = fit(MathTex(
                r"[2,\ 1,\ 0] \;\xrightarrow{\text{softmax}}\; [0.67,\ 0.24,\ 0.09]",
                font_size=26))
            soft.move_to(UP * 0.2)
            self.play(Transform(scores, soft), run_time=d * 0.6)

        with self.say(9) as d:
            note = MathTex(r"0.67 + 0.24 + 0.09 = 1", font_size=28,
                           color=MUTED)
            note.move_to(DOWN * 1.65)
            self.play(Write(note), run_time=d * 0.5)

        with self.say(10) as d:
            heights = [0.67, 0.24, 0.09]
            bars = VGroup()
            for item, h in zip(items, heights):
                bar = Rectangle(width=0.5, height=max(h * 2.0, 0.1),
                                fill_color=ACCENT, fill_opacity=0.9,
                                stroke_width=0)
                bar.next_to(item, DOWN, buff=0.3, aligned_edge=UP)
                bars.add(bar)
            self.sweep(title, items, run_time=d * 0.2)
            self.play(*[GrowFromEdge(b, UP) for b in bars], run_time=d * 0.5)

        with self.say(11) as d:
            pcts = VGroup()
            for bar, p in zip(bars, ["67\\%", "24\\%", "9\\%"]):
                t = MathTex(p, font_size=22, color=WHITE)
                pcts.add(t.next_to(bar, DOWN, buff=0.15))
            self.play(FadeIn(pcts, shift=UP * 0.1), run_time=d * 0.5)

        with self.say(12) as d:
            payoff = fit(Text("attention = learned weights",
                              font_size=24, color=ACCENT_3))
            payoff.move_to(DOWN * 1.65)
            self.play(Indicate(bars, color=ACCENT), run_time=d * 0.3)
            self.play(Write(payoff), run_time=d * 0.5)
