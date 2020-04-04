"""Describe a complete service"""

from dataclasses import dataclass
from pathlib import Path
from typing import List, Tuple

from .lang import Func

from .synthesiser import slcomponents as slc

# A service is essentially a collection of handlers
#
# A handler is an Executable. So there is be one Machine per handler. Many
# handlers may only be one function - that's ok, there's very little overhead.
#
# A service may "export" (ie make public) some methods. Those exports are also
# Executables.
#
# When deployed, a service may list some properties about the deployment. These
# are available with a special method... TBD. Basically remote state.


DEFAULT_PIPELINE = [slc.functions, slc.buckets, slc.dynamodbs, slc.api, slc.finalise]


class Service:
    def __init__(
        self,
        name: str,
        handlers: List[Tuple[str, Func]],
        include=List[Path],
        pipeline: list = None,
    ):
        # outputs: TODO
        # export_methods: List[Func] TODO
        self.name = name
        self.handlers = handlers
        self.pipeline = pipeline if pipeline else DEFAULT_PIPELINE
        self.include = include


# TODO - if a Quote thing implements to_json, it can be returned from a lambda
