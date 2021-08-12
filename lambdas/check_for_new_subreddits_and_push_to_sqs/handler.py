import json, boto3, asyncio, concurrent.futures
from timeit import default_timer as timer

# Added the below 2 lines to let python discover files other than the handler
# ie. enabled relative imports with the below 2 lines.
import sys, os
from datetime import datetime

sys.path.append(os.path.join(os.path.dirname(__file__)))

from subredditList import subreddits as all_subreddits

sqs = boto3.client("sqs")
queue_url = os.getenv("INITIAL_SUBREDDIT_QUEUE_URL")
ddb = boto3.client("dynamodb", region_name="ap-south-1")
DAILY_UPLOADS_TABLE = os.getenv("DAILY_UPLOADS_TABLE_NAME")


def push_subreddits_to_queue():
    for subreddit in all_subreddits:
        res = sqs.send_message(QueueUrl=queue_url, MessageBody=subreddit)


def check(event, context):
    try:
        start = timer()
        push_subreddits_to_queue()
        end = timer()
        response = {"statusCode": 200, "time_taken": end - start}

        res = ddb.put_item(
            TableName=DAILY_UPLOADS_TABLE,
            Item={
                "pk": {"s": str(datetime.today().date())},
                "sk": {"s": "total_subreddits_count"},
                "count": {"N": str(len(all_subreddits))},
            },
        )

        todays_date = str(datetime.today().date())
        res = ddb.transact_write_items(
            TransactItems=[
                {
                    "Put": {
                        "TableName": DAILY_UPLOADS_TABLE,
                        "Item": {
                            "PK": {"S": todays_date},
                            "SK": {"S": "total_subreddits_count"},
                            "count": {"N": str(len(all_subreddits))},
                        },
                    }
                },
                {
                    "Put": {
                        "TableName": DAILY_UPLOADS_TABLE,
                        "Item": {
                            "PK": {"S": todays_date},
                            "SK": {"S": "todays_subreddits_count"},
                            "count": {"N": "0"},
                        },
                    }
                },
            ]
        )

    except Exception as e:
        response = {"statusCode": 500, "error": f"Failed with error: {e}"}

    return response
