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

    Radians = float
    Degrees = float

    draw: ImageDraw
    pos_x: int = 0
    pos_y: int = 0
    angle: Radians = 0
    colour: tuple = (10, 170, 170)
    width: int = 1

    def forward(self, dist):
        """Move forward by dist, drawing a line in the process"""
        start = (self.pos_x, self.pos_y)
        self.pos_x += dist * math.cos(self.angle)
        self.pos_y += dist * math.sin(self.angle)
        end = (self.pos_x, self.pos_y)
        self.draw.line([start, end], fill=self.colour, width=self.width)

    def right(self, angle: Radians):
        """Turn left by ANGLE radians"""
        self.angle = (self.angle + angle) % (2 * math.pi)

    def left(self, angle: Radians):
        """Turn left by ANGLE radians"""
        self.angle = self.angle - angle
        if self.angle < 0:
            self.angle += 2 * math.pi


def create_l_system(iters, axiom, rules):
    """Build the complete L-System sequence"""
    if iters == 0:
        return axiom

    end_string = ""
    start_string = axiom

    for _ in range(iters):
        end_string = "".join(rules[i] if i in rules else i for i in start_string)
        start_string = end_string

    return end_string


def draw_l_system(draw, instructions, angle, distance):
    """Draw the L-System"""
    for cmd in instructions:
        if cmd == "F":
            t.forward(distance)
        elif cmd == "+":
            t.right(angle)
        elif cmd == "-":
            t.left(angle)


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
    t.right(math.radians(45))
    t.forward(100)
    t.left(math.radians(45))
    t.forward(100)
    t.left(math.radians(90))
    t.forward(50)
    im.save(sys.stdout.buffer, "PNG")


def main(
    iterations,
    axiom,
    rules,
    angle,
    length=8,
    size=2,
    y_offset=0,
    x_offset=0,
    offset_angle=0,
    width=450,
    height=450,
):
    inst = create_l_system(iterations, axiom, rules)
    t = turtle.Turtle()
    wn = turtle.Screen()
    wn.setup(width, height)
    t.up()
    t.backward(-x_offset)
    t.left(90)
    t.backward(-y_offset)
    t.left(offset_angle)
    t.down()
    t.speed(0)
    t.pensize(size)
    draw_l_system(t, inst, angle, length)
    t.hideturtle()


def main():
    test_turtle()


if __name__ == "__main__":
    main()
