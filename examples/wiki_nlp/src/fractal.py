"""Fun with Fractals!"""


import sys
from PIL import Image, ImageDraw


# https://elc.github.io/posts/plotting-fractals-step-by-step-with-python/#code


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


def test_pillow(width=200, height=200, alpha=100):
    """Draw an X on a gray background and print to stdout"""
    # Modes: https://pillow.readthedocs.io/en/stable/handbook/concepts.html#concept-modes
    im = Image.new("RGBA", (width, height), (128, 128, 128, alpha))
    draw = ImageDraw.Draw(im)

    teal_colour = (10, 100, 100)
    draw.line((0, 0) + im.size, fill=teal_colour)
    draw.line((0, im.size[1], im.size[0], 0), fill=teal_colour)

    # https://github.com/lincolnloop/python-qrcode/issues/66
    im.save(sys.stdout.buffer, "PNG")


# def main(
#     iterations,
#     axiom,
#     rules,
#     angle,
#     length=8,
#     size=2,
#     y_offset=0,
#     x_offset=0,
#     offset_angle=0,
#     width=450,
#     height=450,
# ):
#     inst = create_l_system(iterations, axiom, rules)
#     t = turtle.Turtle()
#     wn = turtle.Screen()
#     wn.setup(width, height)
#     t.up()
#     t.backward(-x_offset)
#     t.left(90)
#     t.backward(-y_offset)
#     t.left(offset_angle)
#     t.down()
#     t.speed(0)
#     t.pensize(size)
#     draw_l_system(t, inst, angle, length)
#     t.hideturtle()


def main():
    test_pillow()


if __name__ == "__main__":
    main()
