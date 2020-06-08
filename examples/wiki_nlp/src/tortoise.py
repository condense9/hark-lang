"""The Tortoise (similar to a Turle) class"""

import math
import sys
from dataclasses import dataclass

from PIL import Image, ImageDraw


@dataclass
class Tortoise:
    """A minimal Turtle-like plotting interface"""

    Degrees = float

    draw: ImageDraw
    colour: tuple
    pos_x: int = 0
    pos_y: int = 0
    angle: Degrees = 0
    width: int = 1
    pen_down: bool = True
    max_x: int = 0
    max_y: int = 0
    min_x: int = 0
    min_y: int = 0

    def _update_limits(self):
        """Update the max and min positions with the current state"""
        if self.pos_x > self.max_x:
            self.max_x = self.pos_x
        if self.pos_y > self.max_y:
            self.max_y = self.pos_y
        if self.pos_x < self.min_x:
            self.min_x = self.pos_x
        if self.pos_y < self.min_y:
            self.min_y = self.pos_y

    def forward(self, dist):
        """Move forward by dist, drawing a line in the process"""
        start = (self.pos_x, self.pos_y)
        self.pos_x += dist * math.cos(math.radians(self.angle))
        self.pos_y += dist * math.sin(math.radians(self.angle))
        self._update_limits()
        end = (self.pos_x, self.pos_y)
        if self.pen_down:
            self.draw.line([start, end], fill=self.colour, width=self.width)

    def right(self, angle: Degrees):
        """Turn left by ANGLE degrees"""
        prev = self.angle
        self.angle = (self.angle + angle) % 360.0

    def left(self, angle: Degrees):
        """Turn left by ANGLE degrees"""
        prev = self.angle
        self.angle = self.angle - angle
        if self.angle < 0:
            self.angle += 360.0


def test_tortoise(width=200, height=200):
    """Draw some things"""
    im = Image.new("RGB", (width, height), (0, 0, 0))
    draw = ImageDraw.Draw(im)
    t = Tortoise(draw, colour=(10, 240, 240))
    t.right(45)
    t.forward(100)
    t.left(45)
    t.forward(100)
    t.left(90)
    t.forward(50)
    im.save(sys.stdout.buffer, "PNG")
