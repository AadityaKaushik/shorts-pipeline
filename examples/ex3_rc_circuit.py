import numpy as np

from shorts_base import *


def circuit():
    """A simple RC loop built from lines: battery left, R top, C right."""
    w, h = 2.8, 1.1
    tl, tr = LEFT * w / 2 + UP * h / 2, RIGHT * w / 2 + UP * h / 2
    bl, br = LEFT * w / 2 + DOWN * h / 2, RIGHT * w / 2 + DOWN * h / 2

    rbox = Rectangle(width=0.7, height=0.32, color=WHITE).move_to(UP * h / 2)
    top = VGroup(Line(tl, rbox.get_left()), rbox, Line(rbox.get_right(), tr))
    r_label = MathTex("R", font_size=24).next_to(rbox, UP, buff=0.12)

    # capacitor: a gap in the right edge covered by two parallel plates
    gap, plate = 0.14, 0.4
    c_mid = RIGHT * w / 2
    plates = VGroup(
        Line(c_mid + UP * gap + LEFT * plate / 2, c_mid + UP * gap + RIGHT * plate / 2),
        Line(c_mid + DOWN * gap + LEFT * plate / 2, c_mid + DOWN * gap + RIGHT * plate / 2),
    )
    right = VGroup(Line(tr, c_mid + UP * gap), plates, Line(c_mid + DOWN * gap, br))
    c_label = MathTex("C", font_size=24).next_to(plates, RIGHT, buff=0.15)

    # battery: long and short plates in the left edge
    b_mid = LEFT * w / 2
    batt = VGroup(
        Line(b_mid + UP * 0.1 + LEFT * 0.22, b_mid + UP * 0.1 + RIGHT * 0.22),
        Line(b_mid + DOWN * 0.1 + LEFT * 0.12, b_mid + DOWN * 0.1 + RIGHT * 0.12),
    )
    left = VGroup(Line(bl, b_mid + DOWN * 0.1), batt, Line(b_mid + UP * 0.1, tl))
    v_label = MathTex("V_0", font_size=24).next_to(batt, LEFT, buff=0.15)

    bottom = Line(br, bl)
    loop = VGroup(top, right, bottom, left, r_label, c_label, v_label)
    loop.plates, loop.rbox = plates, rbox
    return loop


class Main(ShortScene):
    def construct(self):
        V = lambda t: 1 - np.exp(-t)

        with self.say(0) as d:
            title = fit(Text("Charging a Capacitor", font_size=32, color=ACCENT))
            title.move_to(UP * 3.1)
            sub = Text("the RC circuit", font_size=22, color=MUTED)
            sub.next_to(title, DOWN, buff=0.25)
            self.play(Write(title), run_time=d * 0.5)
            self.play(FadeIn(sub, shift=UP * 0.2), run_time=d * 0.3)

        with self.say(1) as d:
            circ = fit(circuit())
            circ.move_to(UP * 2.15)
            self.play(FadeOut(sub), run_time=d * 0.15)
            self.play(Create(circ), run_time=d * 0.7)

        with self.say(2) as d:
            stores = Text("stores", font_size=20, color=ACCENT_3)
            stores.next_to(circ.plates, DOWN, buff=0.18)
            throttles = Text("throttles", font_size=20, color=ACCENT_2)
            throttles.next_to(circ.rbox, LEFT, buff=0.25)
            self.play(Indicate(circ.plates, color=ACCENT_3), FadeIn(stores),
                      run_time=d * 0.4)
            self.play(Indicate(circ.rbox, color=ACCENT_2), FadeIn(throttles),
                      run_time=d * 0.4)

        with self.say(3) as d:
            axes = Axes(
                x_range=[0, 5.5, 1], y_range=[0, 1.25, 0.5],
                x_length=3.6, y_length=2.4,
                tips=False,
                axis_config={"stroke_color": MUTED, "font_size": 20},
            )
            axes.move_to(UP * 0.2)
            curve1 = axes.plot(V, x_range=[0, 1.2], color=ACCENT)
            self.play(FadeOut(stores), FadeOut(throttles), Create(axes),
                      run_time=d * 0.4)
            self.play(Create(curve1), run_time=d * 0.4, rate_func=linear)

        with self.say(4) as d:
            curve2 = axes.plot(V, x_range=[1.2, 5.5], color=ACCENT)
            self.play(Create(curve2), run_time=d * 0.7, rate_func=linear)

        with self.say(5) as d:
            v0_line = DashedLine(axes.c2p(0, 1), axes.c2p(5.5, 1), color=MUTED)
            v0_label = MathTex("V_0", font_size=22, color=MUTED)
            v0_label.next_to(axes.c2p(5.5, 1), UP, buff=0.1).shift(LEFT * 0.2)
            i_eq = MathTex(r"I = \frac{V_0 - V_C}{R}", font_size=30)
            i_eq.move_to(DOWN * 1.6)
            self.play(Create(v0_line), FadeIn(v0_label), run_time=d * 0.35)
            self.play(Write(i_eq), run_time=d * 0.5)

        with self.say(6) as d:
            t = 0.35
            gap = Arrow(axes.c2p(t, V(t)), axes.c2p(t, 1), buff=0,
                        color=ACCENT_2, stroke_width=5,
                        max_tip_length_to_length_ratio=0.2)
            self.play(GrowArrow(gap), run_time=d * 0.5)

        with self.say(7) as d:
            t2 = 2.6
            gap2 = Arrow(axes.c2p(t2, V(t2)), axes.c2p(t2, 1), buff=0,
                         color=ACCENT_2, stroke_width=5,
                         max_tip_length_to_length_ratio=0.35)
            self.play(Transform(gap, gap2), run_time=d * 0.7)

        with self.say(8) as d:
            v_eq = fit(MathTex(r"V(t) = V_0\left(1 - e^{-t/RC}\right)",
                               font_size=30))
            v_eq.move_to(DOWN * 1.6)
            self.play(FadeOut(gap), ReplacementTransform(i_eq, v_eq),
                      run_time=d * 0.6)

        with self.say(9) as d:
            v_tau = V(1)
            tau_line = DashedLine(axes.c2p(1, 0), axes.c2p(1, v_tau),
                                  color=ACCENT_2)
            tau_label = MathTex(r"\tau", font_size=24, color=ACCENT_2)
            tau_label.next_to(axes.c2p(1, 0), DOWN, buff=0.1)
            pct_line = DashedLine(axes.c2p(0, v_tau), axes.c2p(1, v_tau),
                                  color=ACCENT_3)
            pct = MathTex(r"63\%", font_size=22, color=ACCENT_3)
            pct.next_to(pct_line, UP, buff=0.08)
            self.play(Create(tau_line), FadeIn(tau_label), run_time=d * 0.4)
            self.play(Create(pct_line), FadeIn(pct), run_time=d * 0.4)

        with self.say(10) as d:
            marks = VGroup()
            for t_m, lbl in [(2, "86\\%"), (3, "95\\%")]:
                dot = Dot(axes.c2p(t_m, V(t_m)), color=ACCENT_2, radius=0.05)
                tag = MathTex(lbl, font_size=20, color=MUTED)
                tag.next_to(dot, UP, buff=0.12)
                marks.add(VGroup(dot, tag))
            self.play(FadeIn(marks[0]), run_time=d * 0.3)
            self.play(FadeIn(marks[1]), run_time=d * 0.3)

        with self.say(11) as d:
            end = Dot(axes.c2p(5, V(5)), color=ACCENT_3, radius=0.07)
            payoff = fit(Text("tau = RC sets the wait", font_size=24,
                              color=ACCENT_3))
            payoff.move_to(DOWN * 1.6)
            self.play(FadeIn(end, scale=2), run_time=d * 0.2)
            self.play(ReplacementTransform(v_eq, payoff), run_time=d * 0.5)
