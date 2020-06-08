"""Some CLI styling helpers"""

from colorama import Back, Fore, Style


def em(string):
    return Style.BRIGHT + string + Style.RESET_ALL


def dim(string):
    return Style.DIM + string + Style.RESET_ALL
