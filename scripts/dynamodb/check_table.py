
import boto3
ddb = boto3.client('dynamodb')


def exists(table):
    try:
        response = ddb.describe_table(TableName=table)
        return True	
    except Exception as e:
        return False

def not_exists(table):
    return not exists(table)
        




