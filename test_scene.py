from manim import *

config.frame_height = 8
config.frame_width = 4.5

class Main(Scene):
    def construct(self):
        title = Text("Pipeline test", font_size=40)
        eq = MathTex(r"e^{i\pi} + 1 = 0", font_size=56)
        VGroup(title, eq).arrange(DOWN, buff=0.8)
        self.play(Write(title))
        self.play(Write(eq))
        self.wait(1)