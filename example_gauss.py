from shorts_base import *


class Main(ShortScene):
    def construct(self):
        with self.say(0) as d:
            title = Text("Gauss's Trick", font_size=44, color=ACCENT)
            title.move_to(UP * 3)
            self.play(Write(title), run_time=min(1.5, d * 0.9))

        with self.say(1) as d:
            total = fit(MathTex(r"1 + 2 + 3 + \cdots + 100", font_size=44))
            total.move_to(UP * 1.5)
            self.play(Write(total), run_time=d * 0.7)

        with self.say(2) as d:
            fwd = MathTex(r"1 + 2 + \cdots + 100", font_size=38)
            bwd = MathTex(r"100 + 99 + \cdots + 1", font_size=38, color=ACCENT_2)
            rows = fit(VGroup(fwd, bwd).arrange(DOWN, buff=0.4)).move_to(UP * 1.5)
            self.play(ReplacementTransform(total, fwd), run_time=d * 0.4)
            self.play(FadeIn(bwd, shift=UP * 0.3), run_time=d * 0.4)

        with self.say(3) as d:
            line = Line(LEFT * 1.8, RIGHT * 1.8).next_to(rows, DOWN, buff=0.3)
            sums = MathTex(r"101 + 101 + \cdots + 101", font_size=38, color=ACCENT)
            fit(sums).next_to(line, DOWN, buff=0.3)
            self.play(Create(line), run_time=d * 0.2)
            self.play(Write(sums), run_time=d * 0.6)

        with self.say(4) as d:
            self.play(FadeOut(VGroup(title, rows, line, sums)), run_time=d * 0.2)
            result = MathTex(r"\frac{100 \times 101}{2} = 5050", font_size=48)
            result.move_to(UP * 1.5)
            box = SurroundingRectangle(result, color=ACCENT_3, buff=0.2)
            self.play(Write(result), run_time=d * 0.5)
            self.play(Create(box), run_time=d * 0.2)

        with self.say(5) as d:
            general = fit(MathTex(r"1 + 2 + \cdots + n = \frac{n(n+1)}{2}",
                                  font_size=44))
            general.move_to(UP * 1.5)
            self.play(FadeOut(box), ReplacementTransform(result, general),
                      run_time=d * 0.6)