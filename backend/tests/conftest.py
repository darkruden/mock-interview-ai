import pytest
import boto3
import os
from moto import mock_aws

@pytest.fixture(scope="function")
def aws_credentials():
    """Mocked AWS Credentials for moto."""
    os.environ["AWS_ACCESS_KEY_ID"] = "testing"
    os.environ["AWS_SECRET_ACCESS_KEY"] = "testing"
    os.environ["AWS_SECURITY_TOKEN"] = "testing"
    os.environ["AWS_SESSION_TOKEN"] = "testing"
    os.environ["AWS_DEFAULT_REGION"] = "us-east-1"
    os.environ["BUCKET_NAME"] = "mock-interview-tests-bucket"
    os.environ["TABLE_NAME"] = "MockInterviewSessions-Test"

@pytest.fixture(scope="function")
def s3_client(aws_credentials):
    with mock_aws():
        conn = boto3.client("s3", region_name="us-east-1")
        conn.create_bucket(Bucket=os.environ["BUCKET_NAME"])
        yield conn

@pytest.fixture(scope="function")
def dynamodb_resource(aws_credentials):
    with mock_aws():
        dynamodb = boto3.resource("dynamodb", region_name="us-east-1")
        # Cria a tabela exatamente como seu código espera
        dynamodb.create_table(
            TableName=os.environ["TABLE_NAME"],
            KeySchema=[{'AttributeName': 'session_id', 'KeyType': 'HASH'}],
            AttributeDefinitions=[{'AttributeName': 'session_id', 'AttributeType': 'S'}],
            ProvisionedThroughput={'ReadCapacityUnits': 1, 'WriteCapacityUnits': 1}
        )
        yield dynamodb