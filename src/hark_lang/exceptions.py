"""Top level Hark exceptions"""


class HarkError(Exception):
    """Base for all Hark errors"""


class UserResolvableError(HarkError):
    """An error which the user can probably solve"""

    def __init__(self, msg, suggested_fix):
        self.msg = msg
        self.suggested_fix = suggested_fix

    def __str__(self):
        if type(self) == UserResolvableError:
            return f"{self.msg}\n\n{self.suggested_fix}"
        else:
            return f"{self.__doc__}: {self.msg}\n\n{self.suggested_fix}"


class UnexpectedError(HarkError):
    """An error which is unexpected and with no obvious solution"""

    def __init__(self, msg):
        self.msg = msg

    def __str__(self):
        if type(self) == UnexpectedError:
            return self.msg
        else:
            return f"{self.__doc__}:\n{self.msg}"
