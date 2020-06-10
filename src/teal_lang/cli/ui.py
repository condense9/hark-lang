"""CLI user-interface utilities and configuration"""

import logging

import coloredlogs


def configure_logging(verbose=False, very_verbose=False):
    """Configure the logging module."""
    if very_verbose:
        level = "DEBUG"
    elif verbose:
        level = "INFO"
    else:
        return  # no logs

    for name, logger in logging.root.manager.loggerDict.items():
        if name.startswith("teal_lang") and isinstance(logger, logging.Logger):
            coloredlogs.install(
                fmt="%(name)s[%(process)d] %(message)s", level=level, logger=logger,
            )
