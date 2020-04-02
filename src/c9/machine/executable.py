"""Define the Executable class"""

from dataclasses import dataclass


@dataclass
class Executable:
    locations: dict
    code: list
    modules: dict
    name: str
