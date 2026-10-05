from shorts_base import *


class Main(ShortScene):
    def construct(self):
        with self.say(0) as d:
            title = Text("Attention", font_size=44, color=ACCENT)
            title.move_to(UP * 3.1)
            sub = fit(Text("how transformers decide what matters",
                           font_size=24, color=MUTED))
            sub.next_to(title, DOWN, buff=0.25)
            self.play(Write(title), run_time=d * 0.5)
            self.play(FadeIn(sub, shift=UP * 0.2), run_time=d * 0.3)

        with self.say(1) as d:
            words = VGroup(*[Text(w, font_size=28) for w in ["the", "cat", "sat"]])
            boxes = VGroup()
            for w in words:
                boxes.add(SurroundingRectangle(w, color=MUTED, buff=0.18,
                                               corner_radius=0.08))
            items = VGroup(*[VGroup(b, w) for b, w in zip(boxes, words)])
            items.arrange(RIGHT, buff=0.45).move_to(UP * 2.1)
            vecs = VGroup()
            for item, nums in zip(items, [r"0.2 \\ 0.9", r"0.8 \\ 0.3", r"0.5 \\ 0.6"]):
                v = MathTex(r"\begin{bmatrix} " + nums + r" \end{bmatrix}",
                            font_size=24, color=MUTED)
                vecs.add(v.next_to(item, DOWN, buff=0.25))
            self.play(FadeOut(sub), FadeIn(items), run_time=d * 0.4)
            self.play(FadeIn(vecs, shift=UP * 0.2), run_time=d * 0.4)

        with self.say(2) as d:
            a1 = Arrow(items[1].get_top(), items[0].get_top() + UP * 0.02,
                       buff=0.1, color=ACCENT_2, stroke_width=4, path_arc=-1.2)
            a2 = Arrow(items[1].get_top(), items[2].get_top() + UP * 0.02,
                       buff=0.1, color=ACCENT_2, stroke_width=4, path_arc=1.2)
            eq = MathTex(r"\text{score} = q \cdot k", font_size=36)
            eq.move_to(UP * 0.4)
            self.play(Create(a1), Create(a2), run_time=d * 0.3)
            self.play(FadeOut(vecs), Write(eq), run_time=d * 0.5)

        with self.say(3) as d:
            scores = MathTex(
                r"\begin{bmatrix} 2 & 1 & 0 \\ 1 & 3 & 1 \\ 0 & 1 & 2 \end{bmatrix}",
                font_size=36)
            label = Text("scores", font_size=24, color=MUTED)
            grp = VGroup(scores, label.next_to(scores, DOWN, buff=0.2))
            grp.move_to(DOWN * 0.3)
            self.play(FadeOut(a1), FadeOut(a2), FadeOut(eq), run_time=d * 0.2)
            self.play(FadeIn(grp, shift=UP * 0.2), run_time=d * 0.5)

        with self.say(4) as d:
            soft = fit(MathTex(
                r"[2,\ 1,\ 0] \;\xrightarrow{\text{softmax}}\; [0.67,\ 0.24,\ 0.09]",
                font_size=30))
            soft.move_to(DOWN * 0.3)
            self.play(Transform(grp, soft), run_time=d * 0.6)

        with self.say(5) as d:
            heights = [0.67, 0.24, 0.09]
            bars = VGroup()
            for item, h in zip(items, heights):
                bar = Rectangle(width=0.5, height=h * 1.6,
                                fill_color=ACCENT, fill_opacity=0.9,
                                stroke_width=0)
                bar.next_to(item, DOWN, buff=0.25, aligned_edge=UP)
                bars.add(bar)
            self.play(FadeOut(grp), run_time=d * 0.2)
            self.play(*[GrowFromEdge(b, DOWN) for b in bars], run_time=d * 0.5)

        with self.say(6) as d:
            payoff = fit(Text("attention = learned weights",
                              font_size=28, color=ACCENT_3))
            payoff.move_to(DOWN * 0.9)
            self.play(Indicate(bars, color=ACCENT), run_time=d * 0.3)
            self.play(Write(payoff), run_time=d * 0.5)
