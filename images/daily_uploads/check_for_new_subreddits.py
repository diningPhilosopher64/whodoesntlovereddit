import boto3, pprint, logging, sys, os
from datetime import datetime

pp = pprint.PrettyPrinter(indent=2, compact=True, width=80)

# Initialize logger and its config.
logger = logging.getLogger()
logger.setLevel(logging.INFO)

# Added the below 2 lines to let python discover files other than the handler
# ie. enabled relative imports with the below 2 lines.
# sys.path.append(os.path.join(os.path.dirname(__file__)))
sys.path.append("./")

from helpers import ddb as ddb_helpers
from helpers import sqs as sqs_helpers

# from subredditList import subreddits as all_subreddits
from daily_uploads.subredditList import subreddits as all_subreddits

sqs = boto3.client("sqs")
DAILY_UPLOADS_GATHER_POSTS_FOR_A_SUBREDDIT_QUEUE_URL = os.getenv(
    "DAILY_UPLOADS_GATHER_POSTS_FOR_A_SUBREDDIT_QUEUE_URL"
)
DAILY_UPLOADS_TABLE = os.getenv("DAILY_UPLOADS_TABLE_NAME")

# TODO: Uncomment above 2 lines and comment below 2 lines
# DAILY_UPLOADS_GATHER_POSTS_FOR_A_SUBREDDIT_QUEUE_URL = 'https://sqs.ap-south-1.amazonaws.com/127014180769/GatherPostsForASubreddit'
# DAILY_UPLOADS_TABLE = 'DailyUploadsTable-dev'

ddb = boto3.client("dynamodb", region_name="ap-south-1")

from subreddit_groups import subreddit_groups


def push_subreddits_to_queue(logger):
    """Push subreddits to queue with a delay of 10 seconds.
    Delay is added to re-run the code in a warm container.


    Args:
        logger (logger): Logger instance.
    """
    delay_seconds = 0
    params = {
        "QueueUrl": DAILY_UPLOADS_GATHER_POSTS_FOR_A_SUBREDDIT_QUEUE_URL,
        "MessageBody": None,
        "DelaySeconds": delay_seconds,
    }

    for idx, subreddit in enumerate(all_subreddits):
        params["MessageBody"] = subreddit
        delay_seconds = 0 if idx <= len(all_subreddits) / 2 else 15
        params["DelaySeconds"] = delay_seconds
        res = sqs_helpers.send_message(sqs, logger, **params)


def run(event, context):

    todays_date = str(datetime.today().date())
    total_subreddit_count = str(len(all_subreddits))

    total_subreddit_groups_count = str(len(subreddit_groups))
    params = {
        "TransactItems": [
            {
                "Put": {
                    "TableName": DAILY_UPLOADS_TABLE,
                    "Item": {
                        "PK": {"S": todays_date},
                        "SK": {"S": "total_subreddits_count"},
                        "count": {"N": total_subreddit_count},
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
                        "last_processed_subreddit": {"S": "None"},
                    },
                }
            },
        ]
    }
    resp = ddb_helpers.transact_write_items(ddb, logger, **params)

    resp["status_code"] = 200 if "error" not in resp else 500

    push_subreddits_to_queue(logger)

    return resp
