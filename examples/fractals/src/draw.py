"""Fun with Fractals!

Credit: https://elc.github.io/posts/plotting-fractals-step-by-step-with-python
"""

import itertools
import math
import random
import sys

from PIL import Image, ImageDraw, ImageFilter
from . import store
from .fractals import Fractals
from .tortoise import Tortoise


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


# Generate some colours
SAT = 256
VAL = 256
NUM_COLOURS = 10
COLOURS_HSV = list((x, SAT, VAL) for x in range(0, 360, int(360 / NUM_COLOURS)))


def draw_l_system(
    t: Tortoise, instructions: str, angle: Tortoise.Degrees, distance: float
):
    """Draw the L-System"""
    colours = itertools.cycle(COLOURS_HSV)
    colour_period = math.ceil(len(instructions) / NUM_COLOURS)

    for step, cmd in enumerate(instructions):
        # cycle through colours
        if (step % colour_period) == 0:
            t.colour = next(colours)

        if cmd == "F":
            t.forward(distance)
        elif cmd == "+":
            t.right(angle)
        elif cmd == "-":
            t.left(angle)


def draw_fractal(fractal, linewidth=2, margin=20) -> Image:
    """Draw a Fractal"""
    descr = create_l_system(fractal.iterations, fractal.axiom, fractal.rules)

    # Walk the fractal once without drawing it, so we can get dimensions
    t = Tortoise(None, None, angle=0)
    t.pen_down = False
    draw_l_system(t, descr, fractal.angle, fractal.size)

    # Calculate the required image dimensions and pen offset
    final_width = int((abs(t.max_x) + abs(t.min_x)) + margin)
    final_height = int((abs(t.max_y) + abs(t.min_y)) + margin)
    start_x = abs(t.min_x) + margin / 2
    start_y = abs(t.min_y) + margin / 2

    # Oversample to reduce anti-aliasing and make things look nicer
    oversampling = 10
    width = int(final_width * oversampling)
    height = int(final_height * oversampling)

    # Create output image
    im = Image.new("HSV", (width, height), (0, 0, 0))

    # And draw it!
    t = Tortoise(
        ImageDraw.Draw(im),
        COLOURS_HSV[0],
        pos_x=start_x * oversampling,
        pos_y=start_y * oversampling,
        angle=0,
        width=linewidth * oversampling,
    )
    draw_l_system(t, descr, fractal.angle, fractal.size * oversampling)

    # Scale back down
    # Filters: https://pillow.readthedocs.io/en/stable/handbook/concepts.html#filters
    im = im.resize((final_width, final_height), resample=Image.LANCZOS)
    im = im.filter(ImageFilter.SMOOTH)
    im = im.convert("RGB")
    return im


def test_fractal():
    """Create a single fractal and output it on stdout"""
    name = random_fractals(1)[0][0]
    fractal = getattr(Fractals, name)
    im = draw_fractal(fractal)
    sys.stderr.write(name + "\n")

    im.save(sys.stdout.buffer, "PNG")


def save_fractal_to_file(fractal_name: str, size, dirname=".") -> str:
    """Create a fractal and save it.

    Arguments:
        fractal_name (str): Name of a Fractals class member
        dest (str): Filename to save
        size (int): Modify the Fractal's size parameter

    Returns path of saved file
    """
    dest = f"{fractal_name}_{size}.png"
    fractal = getattr(Fractals, fractal_name)
    fractal.size = size
    im = draw_fractal(fractal)
    full_dest = dirname + "/" + dest
    im.save(full_dest)
    return full_dest


def random_fractals(num) -> list:
    """Create a list of random fractals to generate"""
    fractals = [getattr(Fractals, x) for x in dir(Fractals) if not x.startswith("_")]
    return [
        [fractal.name, random.randint(fractal.min_iter + 2, fractal.max_iter + 2)]
        for fractal in random.choices(fractals, k=num)
    ]


def test_store():
    """Create a random fractal and save it in S3"""
    args = random_fractals(1)
    output = save_fractal_to_file(*args[0])
    store.upload_to_bucket(output)


# TODO make a Fractal collage with https://github.com/secnot/rectpack

if __name__ == "__main__":
    # test_fractal()
    args = random_fractals(1)
    print(args)
    save_fractal_to_file(*args[0])
    # im = draw_fractal(Fractals.segment_curve)
    # im = draw_fractal(Fractals.ter_dragon)
    # im.save(sys.stdout.buffer, "PNG")
