"""Describe a complete service"""

from dataclasses import dataclass
from pathlib import Path
from typing import List, Tuple, Union

from .lang import Func

from .synthesiser import slcomponents as slc
from .synthesiser import terraform as tf

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

SLC_PIPELINE = [slc.functions, slc.buckets, slc.dynamodbs, slc.api, slc.finalise]

# Pipeline order matters!
TF_PIPELINE_AWS = [
    tf.c9_layer,
    tf.functions,
    tf.api,
    tf.buckets,
    tf.dynamodbs,
    tf.provider_aws,
    tf.roles,
    tf.finalise,
]
TF_PIPELINE_LOCAL = [
    tf.functions,
    # tf.api, TODO Not supported yet https://github.com/spulec/moto/issues/2730
    tf.buckets,
    tf.dynamodbs,
    tf.provider_localstack,
    tf.finalise,
]

DEFAULT_PIPELINE_PROD = TF_PIPELINE_AWS
DEFAULT_PIPELINE_DEV = TF_PIPELINE_LOCAL


class Service:
    def __init__(
        self,
        name: str,
        *,
        handlers: List[Union[Func, Tuple[str, Func]]],
        dev_pipeline: list = None,
        prod_pipeline: list = None,
    ):
        # outputs: TODO
        # export_methods: List[Func] TODO
        self.name = name
        self.handlers = []
        self.prod_pipeline = prod_pipeline if prod_pipeline else DEFAULT_PIPELINE_PROD
        self.dev_pipeline = dev_pipeline if dev_pipeline else DEFAULT_PIPELINE_DEV
        # handler names can be specified or not
        for h in handlers:
            if isinstance(h, Func):
                self.handlers.append((h.__name__, h))
            else:
                if not isinstance(h, tuple):
                    raise ValueError(h)
                self.handlers.append(h)


# TODO - if a Quote thing implements to_json, it can be returned from a lambda
