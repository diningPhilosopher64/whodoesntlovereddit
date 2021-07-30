import json,os, boto3, uuid


db = boto3.resource('dynamodb')
table = db.Table(os.getenv("VIDEOURLS_TABLE_NAME"))

def wakeup(event, context):
    result = table.put_item(Item = {
        'url': str(uuid.uuid4()),
        'bla': 'bla'
    })
    body = {
        "message": "Go Serverless v1.0! Your function executed successfully!",
        "inserted": result
    }

    response = {
        "statusCode": 200,
        "body": json.dumps(body)
    }

    return response

    # Use this code if you don't use the http event with the LAMBDA-PROXY
    # integration
    """
    return {
        "message": "Go Serverless v1.0! Your function executed successfully!",
        "event": event
    }
    """
