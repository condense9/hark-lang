"""CLI UI related functions"""

import contextlib
import datetime
import logging
import sys
import urllib.parse
from operator import itemgetter
from traceback import format_exception, format_tb, format_stack

import colorful as cf
from PyInquirer import prompt
from texttable import Texttable
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


# Flags that modify interface displays
QUIET = False
VERBOSE = False


def init(args):
    """Initialise the UI, including logging"""

    if args["--vverbose"]:
        level = "DEBUG"
    elif args["--verbose"]:
        level = "INFO"
    else:
        level = None

    global QUIET
    global VERBOSE
    QUIET = args["--quiet"]
    VERBOSE = args["--verbose"] or args["--vverbose"]

    root_logger = logging.getLogger("teal_lang")

    if not args["--no-colours"]:
        import coloredlogs

        cf.use_true_colors()
        cf.use_palette(UI_COLORS)
        cf.update_palette(UI_COLORS)
        if level:
            coloredlogs.install(
                fmt="[%(asctime)s.%(msecs)03d] %(name)-25s %(message)s",
                datefmt="%H:%M:%S",
                level=level,
                logger=root_logger,
            )
    else:
        cf.disable()
        # FIXME Logger doesn't have basicConfig
        if level:
            root_logger.basicConfig(level=level)


## String colour modifiers


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


## And printing messages


def info(msg):
    if not QUIET:
        print(msg)


## graceful exits


def exit_problem(problem: str, suggested_fix: str):
    """Exit because of a user-correctable problem"""
    print("\n" + bad(problem))
    if suggested_fix:
        print(suggested_fix)
    if not suggested_fix.endswith("\n"):
        print("")
    sys.exit(1)


def exit_bug(msg, *, data=None, traceback=None):
    """Something broke unexpectedly while running"""
    print(bad("\nUnexpected error 💔.\n" + str(msg)))  # absolutely heartbreaking

    source = "".join(format_stack(limit=4))

    exc_type, exc_value, exc_traceback = sys.exc_info()

    if exc_type:
        traceback = format_exception(exc_type, exc_value, exc_traceback)
        traceback_tail = "".join(format_tb(exc_traceback, limit=4))
    elif traceback:
        traceback_tail = "...\n" + "".join(traceback[-4:])
    else:
        traceback_tail = "No traceback"

    if traceback:
        print("\n" + "".join(traceback))

    if data:
        print(f"Associated Data:\n{data}")

    print("\n.·´¯`(>▂<)´¯`·. ")

    # TODO sadface ascii art
    print("\nIf this persists, please let us know:")
    params = urllib.parse.urlencode(
        dict(labels="Type: Bug", template="bug_report.md", title=str(msg),)
    )
    print(dim(f"https://github.com/condense9/teal-lang/issues/new?{params}\n"))

    sys.exit(1)


## UI elements


class DummySpinner:
    """Something that quacks like yaspin, but does nothing"""

    text = ""

    def write(*args):
        pass

    def ok(*args):
        pass

    def fail(*args):
        pass


def spin(text):
    if QUIET or VERBOSE:
        return contextlib.nullcontext(DummySpinner())
    else:
        return yaspin(Spinners.dots, text=str(text))


def check(question: str, default=False) -> bool:
    """Check whether the user wants to proceed"""
    answers = prompt(
        {"type": "confirm", "name": "check", "message": question, "default": default}
    )
    return answers["check"]


def select(question: str, options: list) -> str:
    """Choose one from a list"""
    answers = prompt(
        {"type": "list", "name": "select", "message": question, "choices": options},
    )
    return answers.get("select")


def get_input(question: str) -> str:
    answers = prompt({"type": "input", "name": "input", "message": question})
    return answers.get("input")


# TODO types for these interfaces - they're outputs from awslambda.py


def print_outputs(success_result: dict):
    errors = success_result["errors"]
    output = success_result["output"]

    if output:
        table = Texttable(max_width=100)
        alignment = ["r", "l", "l"]
        table.set_cols_align(alignment)
        table.set_header_align(alignment)
        table.header(["Thread", "Time", ""])
        table.set_deco(Texttable.HEADER)
        start = datetime.datetime.fromisoformat(output[0]["time"])
        for o in output:
            offset = datetime.datetime.fromisoformat(o["time"]) - start
            table.add_row([o["thread"], "+" + str(offset), o["text"].strip()])

        print("\n" + table.draw() + "\n")

    for idx, item in enumerate(errors):
        if item:
            print(bad(f"\nException in Thread {idx}"))
            print(item)


def print_events_by_machine(success_result: dict):
    """Print the results of `getevents`, grouped by machine"""
    elist = success_result["events"]
    for event in elist:
        event["time"] = datetime.datetime.fromisoformat(event["time"])

    lowest_time = min(event["time"] for event in elist)

    for event in sorted(elist, key=itemgetter("thread")):
        offset_time = event["time"] - lowest_time
        time = dim("{:>16}".format(str(offset_time)))
        name = event["event"]
        thread = event["thread"]
        name = event["event"]
        data = event["data"] if len(event["data"]) else ""
        print(f"[{thread}] {time}  {name} {data}")


def print_events_unified(success_result: dict):
    """Print the results of `getevents`, in one table"""
    elist = success_result["events"]
    for event in elist:
        event["time"] = datetime.datetime.fromisoformat(event["time"])

    lowest_time = min(event["time"] for event in elist)

    for event in elist:
        offset_time = event["time"] - lowest_time
        event["offset_time"] = offset_time

    print(cf.bold("{:>14}  {}  {}".format("Time", "Thread", "Event")))
    for event in sorted(elist, key=itemgetter("offset_time")):
        time = dim(str(event["offset_time"]))
        name = event["event"]
        thread = event["thread"]
        data = event["data"] if len(event["data"]) else ""
        print(f"{time:>16}  {thread:^7}  {name} {data}")


def format_source_problem(
    source_filename, source_lineno, source_line, source_column,
):
    if any(
        x is None for x in (source_filename, source_lineno, source_line, source_column)
    ):
        return "<unknown>"

    return (
        f"{source_filename}:{source_lineno}\n...\n{source_lineno}: {source_line}\n"
        + " " * (source_column + len(str(source_lineno)) + 1)
        + "^\n"
    )


def print_traceback(controller, stream=sys.stdout):
    """Print the traceback for a controller"""
    for failure in controller.get_failures():
        # TODO - print a separator when the thread changes, to make it easier to
        # see where contexts change.
        stream.write(str(bad(f"\nError [Thread {failure.thread}]\n")))
        stream.write("Traceback:\n")
        for idx, item in enumerate(failure.stacktrace):
            instr = controller.executable.code[item.caller_ip]
            filename, lineno, line, column = instr.source

            # Indicate call flow direction
            if idx == 0:
                idx = "↓ 0"

            # Get rid of the "#" pointer prefix. FIXME magic here.
            fn = "".join(item.caller_fn.split(":")[1:])
            stream.write(
                f"{idx:>3}: [Thread={item.caller_thread}, IP={item.caller_ip}] in {fn}: {line.strip()}\n"
            )
            stream.write(f"     at {filename}:{lineno}\n")
        stream.write("\n")

        # Print the code at the last one
        instr = controller.executable.code[failure.stacktrace[-1].caller_ip]
        stream.write(format_source_problem(*instr.source))
        stream.write(str(bad(failure.error_msg.strip())) + "\n\n")
