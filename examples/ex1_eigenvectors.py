from shorts_base import *


def vec(plane, x, y, color):
    return Arrow(plane.c2p(0, 0), plane.c2p(x, y), buff=0, color=color,
                 stroke_width=5, max_tip_length_to_length_ratio=0.15)


class Main(ShortScene):
    def construct(self):
        with self.say(0) as d:
            title = Text("Eigenvectors", font_size=44, color=ACCENT)
            title.move_to(UP * 3.1)
            hook = Text("the arrows a matrix can't turn", font_size=24, color=MUTED)
            hook.next_to(title, DOWN, buff=0.25)
            self.play(Write(title), run_time=d * 0.5)
            self.play(FadeIn(hook, shift=UP * 0.2), run_time=d * 0.3)

        with self.say(1) as d:
            mat = fit(MathTex(r"A = \begin{bmatrix} 2 & 1 \\ 1 & 2 \end{bmatrix}",
                              font_size=34))
            mat.move_to(UP * 2.3)
            plane = NumberPlane(
                x_range=[-2, 2, 1], y_range=[-2, 2, 1],
                x_length=3.0, y_length=3.0,
                background_line_style={"stroke_color": MUTED,
                                       "stroke_width": 1, "stroke_opacity": 0.4},
            )
            plane.move_to(UP * 0.4)
            self.play(FadeOut(hook), FadeIn(mat), run_time=d * 0.3)
            self.play(Create(plane), run_time=d * 0.5)

        with self.say(2) as d:
            v1 = vec(plane, 1, -0.5, MUTED)
            v2 = vec(plane, -0.5, 1, MUTED)
            self.play(GrowArrow(v1), GrowArrow(v2), run_time=d * 0.3)
            # A(1,-0.5) = (1.5, 0) and A(-0.5,1) = (0, 1.5): both change direction
            self.play(Transform(v1, vec(plane, 1.5, 0, MUTED)),
                      Transform(v2, vec(plane, 0, 1.5, MUTED)),
                      run_time=d * 0.5)

        with self.say(3) as d:
            axis = DashedLine(plane.c2p(-2, -2), plane.c2p(2, 2),
                              color=ACCENT, stroke_opacity=0.5)
            ev = vec(plane, 0.6, 0.6, ACCENT)
            self.play(FadeOut(v1), FadeOut(v2), Create(axis), run_time=d * 0.3)
            self.play(GrowArrow(ev), run_time=d * 0.2)
            # A(0.6,0.6) = (1.8,1.8): same direction, three times as long
            self.play(Transform(ev, vec(plane, 1.8, 1.8, ACCENT)), run_time=d * 0.4)

        with self.say(4) as d:
            eq = MathTex(r"A\vec{v} = \lambda\,\vec{v}", font_size=40)
            eq.move_to(DOWN * 1.2)
            self.play(Write(eq), run_time=d * 0.5)

        with self.say(5) as d:
            eq3 = MathTex(r"A\vec{v} = 3\,\vec{v}", font_size=40, color=ACCENT_2)
            eq3.move_to(DOWN * 1.2)
            self.play(Transform(eq, eq3), run_time=d * 0.4)
            self.play(Indicate(ev, color=ACCENT), run_time=d * 0.4)

        with self.say(6) as d:
            payoff = fit(Text("the directions a matrix only scales",
                              font_size=28, color=ACCENT_3))
            payoff.move_to(UP * 0.8)
            self.play(FadeOut(plane), FadeOut(ev), FadeOut(axis),
                      FadeOut(eq), FadeOut(mat), run_time=d * 0.3)
            self.play(Write(payoff), run_time=d * 0.5)
