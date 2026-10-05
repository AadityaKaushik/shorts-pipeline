import numpy as np

from shorts_base import *


def circuit():
    """A simple RC loop built from lines: battery left, R top, C right."""
    w, h = 2.8, 1.2
    tl, tr = LEFT * w / 2 + UP * h / 2, RIGHT * w / 2 + UP * h / 2
    bl, br = LEFT * w / 2 + DOWN * h / 2, RIGHT * w / 2 + DOWN * h / 2

    rbox = Rectangle(width=0.7, height=0.32, color=WHITE).move_to(UP * h / 2)
    top = VGroup(Line(tl, rbox.get_left()), rbox, Line(rbox.get_right(), tr))
    r_label = MathTex("R", font_size=28).next_to(rbox, UP, buff=0.12)

    # capacitor: a gap in the right edge covered by two parallel plates
    gap = 0.14
    plate = 0.4
    c_mid = RIGHT * w / 2
    plates = VGroup(
        Line(c_mid + UP * gap + LEFT * plate / 2, c_mid + UP * gap + RIGHT * plate / 2),
        Line(c_mid + DOWN * gap + LEFT * plate / 2, c_mid + DOWN * gap + RIGHT * plate / 2),
    )
    right = VGroup(Line(tr, c_mid + UP * gap), plates, Line(c_mid + DOWN * gap, br))
    c_label = MathTex("C", font_size=28).next_to(plates, RIGHT, buff=0.15)

    # battery: long and short plates in the left edge
    b_mid = LEFT * w / 2
    batt = VGroup(
        Line(b_mid + UP * 0.1 + LEFT * 0.22, b_mid + UP * 0.1 + RIGHT * 0.22),
        Line(b_mid + DOWN * 0.1 + LEFT * 0.12, b_mid + DOWN * 0.1 + RIGHT * 0.12),
    )
    left = VGroup(Line(bl, b_mid + DOWN * 0.1), batt, Line(b_mid + UP * 0.1, tl))
    v_label = MathTex("V_0", font_size=28).next_to(batt, LEFT, buff=0.15)

    bottom = Line(br, bl)
    return VGroup(top, right, bottom, left, r_label, c_label, v_label)


class Main(ShortScene):
    def construct(self):
        with self.say(0) as d:
            title = fit(Text("Charging a Capacitor", font_size=40, color=ACCENT))
            title.move_to(UP * 3.1)
            sub = Text("the RC circuit", font_size=24, color=MUTED)
            sub.next_to(title, DOWN, buff=0.25)
            self.play(Write(title), run_time=d * 0.5)
            self.play(FadeIn(sub, shift=UP * 0.2), run_time=d * 0.3)

        with self.say(1) as d:
            circ = fit(circuit())
            circ.move_to(UP * 2.0)
            self.play(FadeOut(sub), run_time=d * 0.15)
            self.play(Create(circ), run_time=d * 0.7)

        with self.say(2) as d:
            axes = Axes(
                x_range=[0, 5.5, 1], y_range=[0, 1.25, 0.5],
                x_length=3.4, y_length=2.1,
                tips=False,
                axis_config={"stroke_color": MUTED, "font_size": 20},
            )
            axes.move_to(UP * 0.1)
            curve = axes.plot(lambda t: 1 - np.exp(-t), x_range=[0, 5.5],
                              color=ACCENT)
            self.play(Create(axes), run_time=d * 0.3)
            self.play(Create(curve), run_time=d * 0.6, rate_func=linear)

        with self.say(3) as d:
            eq = fit(MathTex(r"V(t) = V_0\left(1 - e^{-t/RC}\right)",
                             font_size=36))
            eq.move_to(DOWN * 1.15)
            self.play(Write(eq), run_time=d * 0.6)

        with self.say(4) as d:
            v_tau = 1 - np.exp(-1)
            tau_line = DashedLine(axes.c2p(1, 0), axes.c2p(1, v_tau),
                                  color=ACCENT_2)
            tau_label = MathTex(r"\tau = RC", font_size=28, color=ACCENT_2)
            tau_label.next_to(axes.c2p(1, 0), DOWN, buff=0.12)
            self.play(Create(tau_line), FadeIn(tau_label), run_time=d * 0.5)

        with self.say(5) as d:
            pct_line = DashedLine(axes.c2p(0, v_tau), axes.c2p(1, v_tau),
                                  color=ACCENT_3)
            pct = MathTex(r"63\%", font_size=26, color=ACCENT_3)
            pct.next_to(axes.c2p(0, v_tau), LEFT, buff=0.12)
            self.play(Create(pct_line), FadeIn(pct), run_time=d * 0.5)

        with self.say(6) as d:
            dot = Dot(axes.c2p(5, 1 - np.exp(-5)), color=ACCENT_3, radius=0.06)
            payoff = fit(Text("tau sets the speed", font_size=28, color=ACCENT_3))
            payoff.move_to(DOWN * 1.15)
            self.play(FadeIn(dot, scale=2), run_time=d * 0.2)
            self.play(FadeOut(eq), run_time=d * 0.15)
            self.play(Write(payoff), run_time=d * 0.4)
