"""Define the Executable class"""

from dataclasses import dataclass


@dataclass
class Executable:
    locations: dict
    code: list
    name: str
