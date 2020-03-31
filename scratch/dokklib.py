"""DynamoDB"""

import logging
import time

import boto3
import botocore

logging.basicConfig(level=logging.INFO)

CONFIG = botocore.config.Config(retries={"max_attempts": 0})


def get_ddb_client():
    return boto3.client(
        "dynamodb",
        aws_access_key_id="",
        aws_secret_access_key="",
        region_name="eu-west-2",
        endpoint_url="http://localhost:4569",
        config=CONFIG,
    )


def get_ddb_table(table_name: str):
    return boto3.resource(
        "dynamodb",
        aws_access_key_id="",
        aws_secret_access_key="",
        region_name="eu-west-2",
        endpoint_url="http://localhost:4569",
        config=CONFIG,
    ).Table(table_name)


# From: https://stackoverflow.com/a/56616499
def clear_dokklib_table(table_name: str):
    logging.info("Clearing table")
    table = get_ddb_table(table_name)
    scan = None

    with table.batch_writer() as batch:
        while scan is None or "LastEvaluatedKey" in scan:
            if scan is not None and "LastEvaluatedKey" in scan:
                scan = table.scan(
                    ProjectionExpression="PK,SK",
                    ExclusiveStartKey=scan["LastEvaluatedKey"],
                )
            else:
                scan = table.scan(ProjectionExpression="PK,SK")

            for item in scan["Items"]:
                batch.delete_item(Key={"PK": item["PK"], "SK": item["SK"]})


# https://github.com/dokklib/dokklib-db/blob/master/tests/integration/cloudformation.yml
# https://boto3.amazonaws.com/v1/documentation/api/latest/reference/services/dynamodb.html#client
def create_dokklib_table(table_name: str):
    client = get_ddb_client()
    logging.info("Creating table")
    client.create_table(
        TableName=table_name,
        KeySchema=[
            {"AttributeName": "PK", "KeyType": "HASH"},
            {"AttributeName": "SK", "KeyType": "RANGE"},
        ],
        AttributeDefinitions=[
            {"AttributeName": "PK", "AttributeType": "S"},
            {"AttributeName": "SK", "AttributeType": "S"},
        ],
        GlobalSecondaryIndexes=[
            # Inverse primary index for querying relational data.
            {
                "IndexName": "GSI_1",
                "KeySchema": [
                    {"AttributeName": "SK", "KeyType": "HASH"},
                    {"AttributeName": "PK", "KeyType": "RANGE"},
                ],
                "Projection": {"ProjectionType": "KEYS_ONLY"},
                "ProvisionedThroughput": {
                    "ReadCapacityUnits": 1,
                    "WriteCapacityUnits": 1,
                },
            }
        ],
        ProvisionedThroughput={"ReadCapacityUnits": 10, "WriteCapacityUnits": 10},
        # StreamSpecification={
        #     'StreamEnabled': True,
        #     'StreamViewType': 'KEYS_ONLY'
        # },
    )
    while not is_table_active(table_name):
        time.sleep(1)


def is_table_active(table_name):
    client = get_ddb_client()
    try:
        res = client.describe_table(TableName=table_name)
    except client.exceptions.ResourceNotFoundException:
        return False
    return res["Table"]["TableStatus"] == "ACTIVE"


def create_or_clear_dokklib_table(table_name: str):
    client = get_ddb_client()
    if not is_table_active(table_name):
        create_dokklib_table(table_name)
    else:
        clear_dokklib_table(table_name)


def delete_table(table_name: str):
    client = get_ddb_client()
    res = client.delete_table(TableName=table_name)
    # NOTE - could use the describe_table API to check it has finished
