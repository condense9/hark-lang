"""Fun with Fractals!"""

import math
import sys
from dataclasses import dataclass

from PIL import Image, ImageDraw


@dataclass
class Params:
    axiom: str
    rules: dict
    iterations: int
    angle: int


# From https://elc.github.io/posts/plotting-fractals-step-by-step-with-python/#code
class Fractals:
    three_dragon = Params(
        # --
        axiom="FX+FX+FX",
        rules={"X": "X+YF+", "Y": "-FX-Y"},
        iterations=7,
        angle=90,
    )

    twin_dragon = Params(
        # --
        axiom="FX+FX",
        rules={"X": "X+YF+", "Y": "-FX-Y"},
        iterations=6,
        angle=90,
    )

    koch = Params(
        # --
        axiom="F--F--F",
        rules={"F": "F+F--F+F"},
        iterations=4,
        angle=60,
    )


@dataclass
class Turtle:
    """A minimal turtle-like drawing interface"""

    Degrees = float

    draw: ImageDraw
    pos_x: int = 0
    pos_y: int = 0
    angle: Degrees = 0
    colour: tuple = (10, 240, 240)
    width: int = 1
    pen_down: bool = True

    def forward(self, dist):
        """Move forward by dist, drawing a line in the process"""
        start = (self.pos_x, self.pos_y)
        self.pos_x += dist * math.cos(math.radians(self.angle))
        self.pos_y += dist * math.sin(math.radians(self.angle))
        end = (self.pos_x, self.pos_y)
        if self.pen_down:
            self.draw.line([start, end], fill=self.colour, width=self.width)

    def right(self, angle: Degrees):
        """Turn left by ANGLE degrees"""
        prev = self.angle
        self.angle = (self.angle + angle) % 360.0
        # print(f"RIGHT | {prev} + {angle} = {self.angle}")

    def left(self, angle: Degrees):
        """Turn left by ANGLE degrees"""
        prev = self.angle
        self.angle = self.angle - angle
        if self.angle < 0:
            self.angle += 360.0
        # print(f"LEFT  | {prev} - {angle} = {self.angle}")


# https://pillow.readthedocs.io/en/stable/reference/ImageDraw.html
def test_pillow(width=200, height=200):
    """Draw an X on a gray background and print to stdout"""
    # Modes: https://pillow.readthedocs.io/en/stable/handbook/concepts.html#concept-modes
    im = Image.new("RGBA", (width, height), (128, 128, 128))
    draw = ImageDraw.Draw(im)

    teal_colour = (10, 100, 100)
    draw.line((0, 0) + im.size, fill=teal_colour)
    draw.line((0, im.size[1], im.size[0], 0), fill=teal_colour)

    # https://github.com/lincolnloop/python-qrcode/issues/66
    im.save(sys.stdout.buffer, "PNG")


def test_turtle(width=200, height=200):
    """Draw a bit"""
    im = Image.new("RGB", (width, height), (0, 0, 0))
    draw = ImageDraw.Draw(im)
    t = Turtle(draw)
    t.right(45)
    t.forward(100)
    t.left(45)
    t.forward(100)
    t.left(90)
    t.forward(50)
    im.save(sys.stdout.buffer, "PNG")


def create_l_system(iters, axiom, rules) -> str:
    """Build the complete L-System sequence"""
    if iters == 0:
        return axiom

    end_string = ""
    start_string = axiom

    for _ in range(iters):
        end_string = "".join(rules[i] if i in rules else i for i in start_string)
        start_string = end_string

    return end_string


def draw_l_system(t: Turtle, instructions: str, angle: Turtle.Degrees, distance: float):
    """Draw the L-System"""
    for cmd in instructions:
        if cmd == "F":
            t.forward(distance)
        elif cmd == "+":
            t.right(angle)
        elif cmd == "-":
            t.left(angle)


def draw_fractal(fractal, linewidth=5, width=400, height=400, size=8):
    # Oversample to reduce anti-aliasing and make things look nicer
    oversampling = 10
    original_width = width
    original_height = height
    width = int(width * oversampling)
    height = int(height * oversampling)

    im = Image.new("RGB", (width, height), (0, 0, 0))
    draw = ImageDraw.Draw(im)
    t = Turtle(
        draw, pos_x=int(width / 2), pos_y=int(height / 2), angle=0, width=linewidth,
    )

    descr = create_l_system(fractal.iterations, fractal.axiom, fractal.rules)
    draw_l_system(t, descr, fractal.angle, size * oversampling)

    # Scale back down
    im = im.resize((original_width, original_height), resample=Image.BILINEAR)
    im.save(sys.stdout.buffer, "PNG")


def test_fracal():
    draw_fractal(Fractals.koch)


def main():
    # test_turtle()
    test_fracal()


if __name__ == "__main__":
    main()
