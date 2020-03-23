"""Describe a complete service"""

from dataclasses import dataclass
from typing import List

from .machine import Executable

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


@dataclass
class Service:
    name: str
    entrypoint: str
    handlers: List[Executable]
    export_methods: List[Executable]
