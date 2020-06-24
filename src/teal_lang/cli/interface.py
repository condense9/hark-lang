"""CLI UI related functions"""

import logging
import sys
from operator import itemgetter

import colorful as cf

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

    # enabled_loggers = [
    #     logger
    #     for name, logger in logging.root.manager.loggerDict.items()
    #     if name.startswith("teal_lang") and isinstance(logger, logging.Logger)
    # ]

    root_logger = logging.getLogger("teal_lang")

    if not args["--no-colours"]:
        import coloredlogs

        cf.use_true_colors()
        cf.use_palette(UI_COLORS)
        cf.update_palette(UI_COLORS)
        if level:
            coloredlogs.install(
                fmt="%(name)s[%(process)d] %(message)s",
                level=level,
                logger=root_logger,
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


def let_us_know():
    """Print helpful information for bug reporting"""
    # TODO sadface ascii art
    print("If this persists, please let us know:")
    print("https://github.com/condense9/teal-lang/issues/new")


def exit_fail(err, traceback=None):
    """Something broke while running"""
    print("\n\n" + bad(str(err)))
    if traceback:
        print("\n" + "".join(traceback))
    sys.exit(1)


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
    lowest_time = min(float(event["time"]) for machines in elist for event in machines)

    for i, machine in enumerate(elist):
        print(cf.bold(f"Thread {i}:"))
        for event in machine:
            offset_time = float(event["time"]) - lowest_time
            time = dim("{:.3f}".format(offset_time))
            name = event["event"]
            data = event["data"] if len(event["data"]) else ""
            print(f"{time}  {name} {data}")


def print_events_unified(success_result: dict):
    """Print the results of `getevents`, in one table"""
    elist = success_result["events"]
    lowest_time = min(float(event["time"]) for machines in elist for event in machines)

    all_events = []
    for i, machine in enumerate(elist):
        for event in machine:
            offset_time = float(event["time"]) - lowest_time
            event["machine"] = i
            event["offset_time"] = offset_time
            event["insert_idx"] = len(all_events)
            all_events.append(event)

    print(cf.bold("{:>8}  {}  {}".format("Time", "Thread", "Event")))
    for event in sorted(all_events, key=itemgetter("offset_time", "insert_idx")):
        time = dim("{:8.3f}".format(event["offset_time"]))
        name = event["event"]
        machine = event["machine"]
        data = event["data"] if len(event["data"]) else ""
        print(f"{time:^}  {machine:^7}  {name} {data}")
