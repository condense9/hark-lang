"""Defines the Executable class"""

from dataclasses import dataclass

# TODO validation of the code?? Versions..


@dataclass
class Executable:
    locations: dict
    code: list
    modules: dict
    name: str
