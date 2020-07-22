"""Fractal definitions

Credit: https://elc.github.io/posts/plotting-fractals-step-by-step-with-python
"""
from dataclasses import dataclass


@dataclass
class Params:
    """Holds Fractal definitions suitable for L-System construction"""

    name: str
    axiom: str
    rules: dict
    iterations: int
    angle: int
    size: int = 10
    min_iter: int = 8
    max_iter: int = 12


class Fractals:
    """A collection of Fractal parameters"""

    dragon = Params(
        # --
        name="dragon",
        axiom="FX",
        rules={"X": "X+YF+", "Y": "-FX-Y"},
        iterations=8,
        angle=90,
        max_iter=15,
    )
    three_dragon = Params(
        # --
        name="three_dragon",
        axiom="FX+FX+FX",
        rules={"X": "X+YF+", "Y": "-FX-Y"},
        iterations=9,
        angle=90,
    )

    twin_dragon = Params(
        # --
        name="twin_dragon",
        axiom="FX+FX",
        rules={"X": "X+YF+", "Y": "-FX-Y"},
        iterations=9,
        angle=90,
        max_iter=10,
    )

    ter_dragon = Params(
        # --
        name="ter_dragon",
        axiom="F",
        rules={"F": "F-F+F"},
        iterations=8,
        angle=120,
        size=10,
        max_iter=10,
    )

    koch_snowflake = Params(
        # --
        name="koch_snowflake",
        axiom="F--F--F",
        rules={"F": "F+F--F+F"},
        iterations=4,
        angle=60,
        min_iter=3,
        max_iter=5,
    )

    koch_island = Params(
        # --
        name="koch_island",
        axiom="F+F+F+F",
        rules={"F": "F-F+F+FFF-F-F+F"},
        iterations=2,
        angle=90,
        min_iter=2,
        max_iter=4,
    )

    triangle = Params(
        # --
        name="triangle",
        axiom="F+F+F",
        rules={"F": "F-F+F"},
        iterations=6,
        angle=120,
        size=14,
    )

    crystal = Params(
        # --
        name="crystal",
        axiom="F+F+F+F",
        rules={"F": "FF+F++F+F"},
        iterations=3,
        angle=90,
        min_iter=3,
        max_iter=6,
    )

    box = Params(
        # --
        name="box",
        axiom="F-F-F-F",
        rules={"F": "F-F+F+F-F"},
        iterations=4,  # TOP: 6
        angle=90,
        min_iter=3,
        max_iter=6,
    )

    levy_c = Params(
        # --
        name="levy_c",
        axiom="F",
        rules={"F": "+F--F+"},
        iterations=10,
        angle=45,
        max_iter=16,
    )

    sierpinski = Params(
        # --
        name="sierpinski",
        axiom="F+XF+F+XF",
        rules={"X": "XF-F+F-XF+F+XF-F+F-X"},
        iterations=4,
        angle=90,
        min_iter=3,
        max_iter=8,
    )

    sierpinski_arrowhead = Params(
        # --
        name="sierpinski_arrowhead",
        axiom="YF",
        rules={"X": "YF+XF+Y", "Y": "XF-YF-X"},
        iterations=4,
        angle=60,
        min_iter=3,
        max_iter=10,
    )

    # NOTE: this one is slooow
    sierpinski_sieve = Params(
        # --
        name="sierpinski_sieve",
        axiom="FXF--FF--FF",
        rules={"F": "FF", "X": "--FXF++FXF++FXF--"},
        iterations=5,
        angle=60,
        min_iter=3,
        max_iter=7,
    )

    board = Params(
        # --
        name="board",
        axiom="F+F+F+F",
        rules={"F": "FF+F+F+F+FF"},
        iterations=3,
        angle=90,
        min_iter=3,
        max_iter=5,
    )

    tiles = Params(
        # --
        name="tiles",
        axiom="F+F+F+F",
        rules={"F": "FF+F-F+F+FF"},
        iterations=3,
        angle=90,
        min_iter=2,
        max_iter=4,
    )

    rings = Params(
        # --
        name="rings",
        axiom="F+F+F+F",
        rules={"F": "FF+F+F+F+F+F-F"},
        iterations=2,
        angle=90,
        min_iter=2,
        max_iter=4,
    )

    cross = Params(
        # --
        name="cross",
        axiom="F+F+F+F",
        rules={"F": "F+FF++F+F"},
        iterations=3,
        angle=90,
        min_iter=2,
        max_iter=6,
    )

    cross2 = Params(
        # --
        name="cross2",
        axiom="F+F+F+F",
        rules={"F": "F+F-F+F+F"},
        iterations=3,
        angle=90,
        min_iter=2,
        max_iter=6,
    )

    pentaplexity = Params(
        # --
        name="pentaplexity",
        axiom="F++F++F++F++F",
        rules={"F": "F++F++F+++++F-F++F"},
        iterations=1,
        angle=36,
        min_iter=2,
        max_iter=5,
    )

    # NOTE: this one is slooooow
    segment_curve = Params(
        # --
        name="segment_curve",
        axiom="F+F+F+F",
        rules={"F": "-F+F-F-F+F+FF-F+F+FF+F-F-FF+FF-FF+F+F-FF-F-F+FF-F-F+F+F-F+"},
        iterations=2,
        angle=90,
        min_iter=2,
        max_iter=3,
    )

    peano_gosper = Params(
        # --
        name="peano_gosper",
        axiom="FX",
        rules={"X": "X+YF++YF-FX--FXFX-YF+", "Y": "-FX+YFYF++YF+FX--FX-Y"},
        iterations=4,
        angle=60,
        min_iter=2,
        max_iter=5,
    )

    krishna_anklets = Params(
        # --
        name="krishna_anklets",
        axiom=" -X--X",
        rules={"X": "XFX--XFX"},
        iterations=3,
        angle=45,
        min_iter=2,
        max_iter=9,
    )

    # quad_gosper = Params(
    #     # --
    #     name="quad_gosper",
    #     axiom="YF",
    #     rules={
    #         "X": "XFX-YF-YF+FX+FX-YF-YFFX+YF+FXFXYF-FX+YF+FXFX+YF-FXYF-YF-FX+FX+YFYF-",
    #         "Y": "+FXFX-YF-YF+FX+FXYF+FX-YFYF-FX-YF+FXYFYF-FX-YFFX+FX+YF-YF-FX+FX+YFY",
    #     },
    #     iterations=2,
    #     angle=90,
    #     min_iter=2,
    #     max_iter=3,
    # )

    moore = Params(
        # --
        name="moore",
        axiom="LFL-F-LFL",
        rules={"L": "+RF-LFL-FR+", "R": "-LF+RFR+FL-"},
        iterations=2,
        angle=90,
        min_iter=2,
        max_iter=8,
    )

    hilberts = Params(
        # --
        name="hilberts",
        axiom="L",
        rules={"L": "+RF-LFL-FR+", "R": "-LF+RFR+FL-"},
        iterations=4,
        angle=90,
        min_iter=2,
        max_iter=7,
    )

    hilbert2 = Params(
        # --
        name="hilbert2",
        axiom="X",
        rules={"X": "XFYFX+F+YFXFY-F-XFYFX", "Y": "YFXFY-F-XFYFX+F+YFXFY"},
        iterations=4,
        angle=90,
        min_iter=2,
        max_iter=6,
    )

    peano = Params(
        # --
        name="peano",
        axiom="F",
        rules={"F": "F+F-F-F-F+F+F+F-F"},
        iterations=4,
        angle=90,
        min_iter=3,
        max_iter=5,
    )
