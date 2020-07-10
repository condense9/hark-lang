"""Top level Teal exceptions"""


class TealError(Exception):
    """Base for all Teal errors"""


class UserResolvableError(TealError):
    """An error which the user can probably solve"""

    def __init__(self, msg, suggested_fix):
        self.msg = msg
        self.suggested_fix = suggested_fix

    def __str__(self):
        if type(self) == UserResolvableError:
            return f"{self.msg}\n\n{self.suggested_fix}"
        else:
            return f"{self.__doc__}: {self.msg}\n\n{self.suggested_fix}"


class UnexpectedError(TealError):
    """An error which is unexpected and with no obvious solution"""

    def __init__(self, msg):
        self.msg = msg

    def __str__(self):
        if type(self) == UnexpectedError:
            return self.msg
        else:
            return f"{self.__doc__}:\n{self.msg}"
