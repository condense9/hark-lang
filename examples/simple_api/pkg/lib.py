# https://github.com/serverless/examples/blob/master/aws-python-rest-api-with-dynamodb/todos/create.py

import json
import logging
import os
import time
import uuid

import boto3

from c9.lang import Foreign

dynamodb = boto3.resource("dynamodb")


@Foreign
def create_todo(db_props, event, context):
    data = json.loads(event["body"])
    if "text" not in data:
        logging.error("Validation Failed")
        raise Exception("Couldn't create the todo item.")

    timestamp = str(time.time())

    table = dynamodb.Table(db_props["id"])

    item = {
        "id": str(uuid.uuid1()),
        "text": data["text"],
        "checked": False,
        "createdAt": timestamp,
        "updatedAt": timestamp,
    }

    # write the todo to the database
    table.put_item(Item=item)

    return item


@Foreign
def list_todos(db_props, event, context):
    print(db_props)
    table = dynamodb.Table(db_props["id"])

    # fetch all todos from the database
    result = table.scan()

    return result["Items"]
