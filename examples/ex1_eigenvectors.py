from shorts_base import *


def vec(plane, x, y, color):
    return Arrow(plane.c2p(0, 0), plane.c2p(x, y), buff=0, color=color,
                 stroke_width=5, max_tip_length_to_length_ratio=0.15)


class Main(ShortScene):
    def construct(self):
        # Matrix used throughout: A = [[2, 1], [1, 2]]
        with self.say(0) as d:
            title = Text("Eigenvectors", font_size=36, color=ACCENT)
            self.show("title", title, run_time=d * 0.5, anim=Write(title))
            hook = Text("the vectors behind PageRank", font_size=24, color=MUTED)
            self.show("top", hook, run_time=d * 0.3)

        with self.say(1) as d:
            box = Rectangle(width=1.0, height=0.8, color=ACCENT)
            box_a = MathTex("A", font_size=32).move_to(box)
            a_in = Arrow(LEFT * 1.9, box.get_left(), buff=0.1, color=MUTED)
            a_out = Arrow(box.get_right(), RIGHT * 1.9, buff=0.1, color=ACCENT_2)
            v_in = MathTex(r"\vec{v}", font_size=28, color=MUTED)
            v_in.next_to(a_in, UP, buff=0.25)
            v_out = MathTex(r"A\vec{v}", font_size=28, color=ACCENT_2)
            v_out.next_to(a_out, UP, buff=0.25)
            machine = VGroup(box, box_a, a_in, a_out, v_in, v_out)
            self.show("main", machine, run_time=d * 0.5)

        with self.say(2) as d:
            mat = MathTex(r"A = \begin{bmatrix} 2 & 1 \\ 1 & 2 \end{bmatrix}",
                          font_size=26)
            self.show("top", mat, run_time=d * 0.3)  # replaces the hook line
            plane = NumberPlane(
                x_range=[-2, 2, 1], y_range=[-2, 2, 1],
                x_length=3.2, y_length=3.2,
                background_line_style={"stroke_color": MUTED,
                                       "stroke_width": 1, "stroke_opacity": 0.4},
            )
            stage = VGroup(plane)
            # replaces the machine; the group evolves for the rest of the video
            self.show("main", stage, run_time=d * 0.5)

        with self.say(3) as d:
            v1 = vec(plane, 1, -0.5, MUTED)
            v2 = vec(plane, -0.5, 1, MUTED)
            stage.add(v1, v2)
            self.play(GrowArrow(v1), GrowArrow(v2), run_time=d * 0.3)
            # A(1,-0.5) = (1.5, 0) and A(-0.5,1) = (0, 1.5): both change direction
            self.play(Transform(v1, vec(plane, 1.5, 0, MUTED)),
                      Transform(v2, vec(plane, 0, 1.5, MUTED)),
                      run_time=d * 0.5)

        with self.say(4) as d:
            v3 = vec(plane, -1, 0.3, MUTED)
            stage.add(v3)
            self.play(GrowArrow(v3), run_time=d * 0.3)
            # A(-1,0.3) = (-1.7, -0.4)
            self.play(Transform(v3, vec(plane, -1.7, -0.4, MUTED)),
                      run_time=d * 0.5)

        with self.say(5) as d:
            axis = DashedLine(plane.c2p(-2, -2), plane.c2p(2, 2),
                              color=ACCENT, stroke_opacity=0.5)
            ev = vec(plane, 0.6, 0.6, ACCENT)
            self.play(FadeOut(v1), FadeOut(v2), FadeOut(v3), Create(axis),
                      run_time=d * 0.3)
            stage.remove(v1, v2, v3)
            stage.add(axis, ev)
            self.play(GrowArrow(ev), run_time=d * 0.2)
            # A(0.6,0.6) = (1.8,1.8): same direction, three times as long
            self.play(Transform(ev, vec(plane, 1.8, 1.8, ACCENT)), run_time=d * 0.4)

        with self.say(6) as d:
            tag = Text("eigenvector", font_size=28, color=ACCENT)
            self.show("low", tag, run_time=d * 0.5, anim=Write(tag))

        with self.say(7) as d:
            # the "push" A adds lies along the arrow's own line
            push = Arrow(plane.c2p(0.6, 0.6), plane.c2p(1.8, 1.8), buff=0,
                         color=ACCENT_2, stroke_width=7,
                         max_tip_length_to_length_ratio=0.12)
            self.play(GrowArrow(push), run_time=d * 0.5)
            self.play(FadeOut(push), run_time=d * 0.3)

        with self.say(8) as d:
            eq = MathTex(r"A\vec{v} = \lambda\,\vec{v}", font_size=32)
            self.show("low", eq, run_time=d * 0.5)  # replaces the tag

        with self.say(9) as d:
            eq3 = MathTex(r"A\vec{v} = 3\,\vec{v}", font_size=32, color=ACCENT_2)
            self.show("low", eq3, run_time=d * 0.4)
            self.play(Indicate(ev, color=ACCENT), run_time=d * 0.4)

        with self.say(10) as d:
            axis2 = DashedLine(plane.c2p(-2, 2), plane.c2p(2, -2),
                               color=ACCENT_3, stroke_opacity=0.5)
            ev2 = vec(plane, 0.9, -0.9, ACCENT_3)
            stage.add(axis2, ev2)
            self.play(Create(axis2), run_time=d * 0.3)
            # A(0.9,-0.9) = (0.9,-0.9): eigenvalue 1, nothing moves
            self.play(GrowArrow(ev2), run_time=d * 0.3)
            self.play(Indicate(ev2, color=ACCENT_3, scale_factor=1.05),
                      run_time=d * 0.3)

        with self.say(11) as d:
            eqs = MathTex(r"\lambda_1 = 3,\quad \lambda_2 = 1", font_size=32)
            self.show("low", eqs, run_time=d * 0.5)

        with self.say(12) as d:
            self.sweep(title, run_time=d * 0.3)
            payoff = Text("the directions a matrix only scales",
                          font_size=28, color=ACCENT_3)
            self.show("main", payoff, run_time=d * 0.5, anim=Write(payoff))
