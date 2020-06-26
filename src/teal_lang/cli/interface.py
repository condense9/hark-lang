"""CLI UI related functions"""

import contextlib
import logging
import sys
import urllib.parse
from operator import itemgetter

import colorful as cf
from yaspin import yaspin
from yaspin.spinners import Spinners

TICK = "✔"
CROSS = "✘"

# TODO light/dark versions
UI_COLORS = {
    # --
    "teal": "#027777",
    "grey": "#777777",
    "magenta": "#9510ED",
    "red": "#991010",
}


def init(args):
    """Initialise the UI, including logging"""

    if args["--vverbose"]:
        level = "DEBUG"
    elif args["--verbose"]:
        level = "INFO"
    else:
        level = None

    root_logger = logging.getLogger("teal_lang")

    if not args["--no-colours"]:
        import coloredlogs

        cf.use_true_colors()
        cf.use_palette(UI_COLORS)
        cf.update_palette(UI_COLORS)
        if level:
            coloredlogs.install(
                fmt="%(name)-25s %(message)s", level=level, logger=root_logger,
            )
    else:
        cf.disable()
        if level:
            root_logger.basicConfig(level=level)


def dim(string):
    return cf.grey(string)


def good(string):
    return cf.bold_teal(string)


def bad(string):
    return cf.bold_red(string)


def primary(string):
    return cf.teal(string)


def secondary(string):
    return cf.magenta(string)


def neutral(string):
    return cf.bold(string)


def let_us_know(error_msg=None, traceback=None):
    """Print helpful information for bug reporting"""
    # TODO sadface ascii art
    print("If this persists, please let us know:")
    if error_msg:
        params = "?" + urllib.parse.urlencode(dict(title=error_msg))
    else:
        params = ""
    print(f"https://github.com/condense9/teal-lang/issues/new{params}")
    print("")


def exit_fail(err, traceback=None):
    """Something broke while running"""
    print(bad(str(err)))
    if traceback:
        print("\n" + "".join(traceback))
    sys.exit(1)


class DummySpinner:
    """Something that quacks like yaspin, but does nothing"""

    text = ""

    def write(*args):
        pass

    def ok(*args):
        pass

    def fail(*args):
        pass


def spin(args, text):
    if args["--quiet"] or args["--verbose"] or args["--vverbose"]:
        return contextlib.nullcontext(DummySpinner())
    else:
        return yaspin(Spinners.dots, text=str(text))


# TODO types for these interfaces - they're outputs from awslambda.py


def print_outputs(success_result: dict):
    errors = success_result["errors"]
    output = success_result["output"]

    for o in output:
        sys.stdout.write(o["text"])

    for idx, item in enumerate(errors):
        if item:
            print(bad(f"\nException in Thread {idx}"))
            print(item)


def print_events_by_machine(success_result: dict):
    """Print the results of `getevents`, grouped by machine"""
    elist = success_result["events"]
    lowest_time = min(float(event["time"]) for event in elist)

    for event in sorted(elist, key=itemgetter("thread")):
        offset_time = float(event["time"]) - lowest_time
        time = dim("{:.3f}".format(offset_time))
        name = event["event"]
        thread = event["thread"]
        name = event["event"]
        data = event["data"] if len(event["data"]) else ""
        print(f"[{thread}] {time}  {name} {data}")


def print_events_unified(success_result: dict):
    """Print the results of `getevents`, in one table"""
    elist = success_result["events"]
    lowest_time = min(float(event["time"]) for event in elist)

    for event in elist:
        offset_time = float(event["time"]) - lowest_time
        event["offset_time"] = offset_time

    print(cf.bold("{:>8}  {}  {}".format("Time", "Thread", "Event")))
    for event in sorted(elist, key=itemgetter("offset_time")):
        time = dim("{:8.3f}".format(event["offset_time"]))
        name = event["event"]
        thread = event["thread"]
        data = event["data"] if len(event["data"]) else ""
        print(f"{time:^}  {thread:^7}  {name} {data}")
