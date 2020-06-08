"""Fractal definitions

Credit: https://elc.github.io/posts/plotting-fractals-step-by-step-with-python
"""
from dataclasses import dataclass


@dataclass
class Params:
    """Holds Fractal definitions suitable for L-System construction"""

    axiom: str
    rules: dict
    iterations: int
    angle: int
    size: int = 10


class Fractals:
    """A collection of Fractal parameters"""

    dragon = Params(
        # --
        axiom="FX",
        rules={"X": "X+YF+", "Y": "-FX-Y"},
        iterations=8,  # TOP: 16
        angle=90,
    )
    three_dragon = Params(
        # --
        axiom="FX+FX+FX",
        rules={"X": "X+YF+", "Y": "-FX-Y"},
        iterations=9,
        angle=90,
    )

    twin_dragon = Params(
        # --
        axiom="FX+FX",
        rules={"X": "X+YF+", "Y": "-FX-Y"},
        iterations=12,
        angle=90,
    )

    ter_dragon = Params(
        # --
        axiom="F",
        rules={"F": "F-F+F"},
        iterations=8,  # TOP: 10
        angle=120,
        size=10,
    )

    koch_snowflake = Params(
        # --
        axiom="F--F--F",
        rules={"F": "F+F--F+F"},
        iterations=5,
        angle=60,
    )

    koch_island = Params(
        # --
        axiom="F+F+F+F",
        rules={"F": "F-F+F+FFF-F-F+F"},
        iterations=2,  # TOP: 4
        angle=90,
    )

    triangle = Params(
        # --
        axiom="F+F+F",
        rules={"F": "F-F+F"},
        iterations=6,
        angle=120,
        size=14,
    )

    crystal = Params(
        # --
        axiom="F+F+F+F",
        rules={"F": "FF+F++F+F"},
        iterations=3,
        angle=90,  # TOP: 6
    )

    box = Params(
        # --
        axiom="F-F-F-F",
        rules={"F": "F-F+F+F-F"},
        iterations=4,  # TOP: 6
        angle=90,
    )

    levy_c = Params(
        # --
        axiom="F",
        rules={"F": "+F--F+"},
        iterations=10,  # TOP: 16
        angle=45,
    )

    sierpinski = Params(
        # --
        axiom="F+XF+F+XF",
        rules={"X": "XF-F+F-XF+F+XF-F+F-X"},
        iterations=4,  # TOP: 8
        angle=90,
    )

    sierpinski_arrowhead = Params(
        # --
        axiom="YF",
        rules={"X": "YF+XF+Y", "Y": "XF-YF-X"},
        iterations=4,  # TOP: 10
        angle=60,
    )

    # NOTE: this one is slooow
    sierpinski_sieve = Params(
        # --
        axiom="FXF--FF--FF",
        rules={"F": "FF", "X": "--FXF++FXF++FXF--"},
        iterations=7,  # TOP: 8
        angle=60,
    )

    board = Params(
        # --
        axiom="F+F+F+F",
        rules={"F": "FF+F+F+F+FF"},
        iterations=3,  # TOP: 5
        angle=90,
    )

    tiles = Params(
        # --
        axiom="F+F+F+F",
        rules={"F": "FF+F-F+F+FF"},
        iterations=3,  # TOP: 4
        angle=90,
    )

    rings = Params(
        # --
        axiom="F+F+F+F",
        rules={"F": "FF+F+F+F+F+F-F"},
        iterations=2,  # TOP: 4
        angle=90,
    )

    cross = Params(
        # --
        axiom="F+F+F+F",
        rules={"F": "F+FF++F+F"},
        iterations=3,  # TOP: 6
        angle=90,
    )

    cross2 = Params(
        # --
        axiom="F+F+F+F",
        rules={"F": "F+F-F+F+F"},
        iterations=3,  # TOP: 6
        angle=90,
    )

    pentaplexity = Params(
        # --
        axiom="F++F++F++F++F",
        rules={"F": "F++F++F+++++F-F++F"},
        iterations=1,  # TOP: 5
        angle=36,
    )

    # NOTE: this one is slooooow
    segment_curve = Params(
        # --
        axiom="F+F+F+F",
        rules={"F": "-F+F-F-F+F+FF-F+F+FF+F-F-FF+FF-FF+F+F-FF-F-F+FF-F-F+F+F-F+"},
        iterations=2,  # TOP: 3
        angle=90,
    )

    peano_gosper = Params(
        # --
        axiom="FX",
        rules={"X": "X+YF++YF-FX--FXFX-YF+", "Y": "-FX+YFYF++YF+FX--FX-Y"},
        iterations=4,  # TOP: 6
        angle=60,
    )

    krishna_anklets = Params(
        # --
        axiom=" -X--X",
        rules={"X": "XFX--XFX"},
        iterations=3,  # TOP: 9
        angle=45,
    )

    quad_gosper = Params(
        # --
        axiom="YF",
        rules={
            "X": "XFX-YF-YF+FX+FX-YF-YFFX+YF+FXFXYF-FX+YF+FXFX+YF-FXYF-YF-FX+FX+YFYF-",
            "Y": "+FXFX-YF-YF+FX+FXYF+FX-YFYF-FX-YF+FXYFYF-FX-YFFX+FX+YF-YF-FX+FX+YFY",
        },
        iterations=2,  # TOP: 3
        angle=90,
    )

    moore = Params(
        # --
        axiom="LFL-F-LFL",
        rules={"L": "+RF-LFL-FR+", "R": "-LF+RFR+FL-"},
        iterations=0,  # TOP: 8
        angle=90,
    )

    hilberts = Params(
        # --
        axiom="L",
        rules={"L": "+RF-LFL-FR+", "R": "-LF+RFR+FL-"},
        iterations=8,  # TOP: 9
        angle=90,
    )

    hilbert2 = Params(
        # --
        axiom="X",
        rules={"X": "XFYFX+F+YFXFY-F-XFYFX", "Y": "YFXFY-F-XFYFX+F+YFXFY"},
        iterations=4,  # TOP: 6
        angle=90,
    )

    peano = Params(
        # --
        axiom="F",
        rules={"F": "F+F-F-F-F+F+F+F-F"},
        iterations=4,  # TOP: 5
        angle=90,
    )
