"""Outputs retrieval

Each synthesiser is responsible for writing the outputs file as part of its
deployment process.

The outputs file is a JSON dict mapping {infrastructure name -> properties}.

"""

import json
import logging
import os
import os.path

from ..constants import OUTPUTS_FILENAME

# Cache
OUTPUTS = None


def load_infra_outputs(inf_name: str) -> dict:
    """Load the outputs for the given infrastructure"""
    global OUTPUTS
    if not OUTPUTS:
        filename = os.path.join(os.getcwd(), OUTPUTS_FILENAME)
        logging.info(f"Loading outputs from {filename}")
        with open(filename, "r") as f:
            OUTPUTS = json.load(f)

    return OUTPUTS[inf_name]
