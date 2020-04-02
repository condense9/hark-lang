"""Test the AWS test utilities - these may become core libraries eventually"""

import os
import os.path
from os.path import join

import pytest

import c9.lambda_utils as lambda_utils

pytestmark = pytest.mark.skipif(
    "RUNNING_IN_GITLAB" in os.environ, reason="Gitlab not supported yet"
)


TABLE_NAME = "TestAwsSingleTable"
THIS_DIR = os.path.dirname(__file__)
LAMBDAS_DIR = join(THIS_DIR, "lambdas")


def setup_module(module):
    lambda_utils.create_lambda(join(LAMBDAS_DIR, "basic"))


def teardown_module(module):
    lambda_utils.delete_lambda("basic")
    # NOT deleting the table - slow


def test_that_lambda_returns_correct_message():
    response = lambda_utils.invoke("basic")
    assert response["message"] == "Hello pytest!"
