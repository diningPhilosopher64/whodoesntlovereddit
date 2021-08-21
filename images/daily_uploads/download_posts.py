from re import sub
import boto3, os, sys, logging, pprint
from pathlib import Path
import time
from datetime import datetime

pp = pprint.PrettyPrinter(indent=2, compact=True, width=80)

# Initialize logger and its config.
logger = logging.getLogger()
logger.setLevel(logging.INFO)

# Making the current directory in which this file is in discoverable to python
sys.path.append(os.path.join(os.path.dirname(__file__)))

from entities.GatherPosts import GatherPosts
from entities.DownloadPosts import DownloadPosts
from helpers import ddb as ddb_helpers
from helpers import sqs as sqs_helpers
from helpers import s3 as s3_helpers


ddb = boto3.client("dynamodb", region_name="ap-south-1")
s3 = boto3.client("s3")
sqs = boto3.client("sqs")


DAILY_UPLOADS_TABLE_NAME = os.getenv("DAILY_UPLOADS_TABLE_NAME")
DAILY_UPLOADS_PROCESS_POSTS_FOR_A_SUBREDDIT_QUEUE_URL = os.getenv(
    "DAILY_UPLOADS_PROCESS_POSTS_FOR_A_SUBREDDIT_QUEUE_URL"
)
DAILY_UPLOADS_PROCESS_SUBREDDIT_GROUP_QUEUE_URL = os.getenv(
    "DAILY_UPLOADS_PROCESS_SUBREDDIT_GROUP_QUEUE_URL"
)


def run(event, context):
    subreddit = str(event["Records"][0]["body"])
    logger.info(f"Received the message: {subreddit} from event.")
    bucket_name = f"whodoesntlovereddit-{str(datetime.today().date())}-{subreddit}"

    # needs_to_execute() ensures idempotency of this lambda.
    # If the bucket already exists, it means that some other function already began processing it,
    # so skip this execution.
    if not needs_to_execute(bucket_name, s3, logger):
        return {"note": f"{bucket_name} bucket already exists. Exiting."}

    gather_posts = GatherPosts(subreddit=subreddit, logger=logger)

    logger.info(
        f"Videos of Subreddit : {subreddit}, are being downloaded on {gather_posts.date}"
    )

    params = {"TableName": DAILY_UPLOADS_TABLE_NAME, "Key": gather_posts.key()}
    item = ddb_helpers.get_item(ddb, logger, **params)

    deserialized_item = GatherPosts.deserialize_from_item(item)

    download_posts = DownloadPosts(
        s3=s3,
        subreddit=subreddit,
        posts=deserialized_item["posts"],
        bucket_name=bucket_name,
        logger=logger,
    )

    download_posts.download_videos_and_push_to_s3()

    update_processed_subreddits_count(ddb, logger, gather_posts)

    if is_last_subreddit_of_today(gather_posts, ddb, logger):
        logger.info(
            f"The subreddit {gather_posts.subreddit} is the last one to download videos on {gather_posts.date}.\n"
        )

        invoke_lambda_to_group_subreddits(gather_posts.date)

        return {
            "success": f"All subreddits have been processed and uploaded videos for date {gather_posts.date}.\nInvoked the lambda to group subreddits"
        }

    return {
        "response": f"Successfully uploaded videos of subreddit: {gather_posts.subreddit} on {gather_posts.date} to s3."
    }


def update_processed_subreddits_count(ddb, logger, gather_posts):
    params = {
        "TableName": DAILY_UPLOADS_TABLE_NAME,
        "Key": {
            "PK": {"S": gather_posts.date},
            "SK": {"S": "todays_subreddits_count"},
        },
        "ConditionExpression": "attribute_exists(PK) and attribute_exists(SK)",
        "UpdateExpression": "SET #count = #count + :inc",
        "ExpressionAttributeNames": {"#count": "count"},
        "ExpressionAttributeValues": {":inc": {"N": "1"}},
        "ReturnValues": "ALL_NEW",
    }

    ddb_helpers.update_item(ddb, logger, **params)


def invoke_lambda_to_group_subreddits(todays_date):
    from subreddit_groups import subreddit_groups

    params = {
        "QueueUrl": DAILY_UPLOADS_PROCESS_SUBREDDIT_GROUP_QUEUE_URL,
        "MessageBody": None,
    }

    for group in subreddit_groups:
        group_str = "-".join(group)
        group_str = today + "-" + group_str
        params["MessageBody"] = group_str
        sqs_helpers.send_message(sqs, logger, **params)


def is_last_subreddit_of_today(gather_posts, ddb, logger):
    key = gather_posts.key()

    total_subreddits_key = gather_posts.key()
    todays_subreddits_key = gather_posts.key()

    total_subreddits_key["SK"]["S"] = "total_subreddits_count"
    todays_subreddits_key["SK"]["S"] = "todays_subreddits_count"

    params = {
        "TransactItems": [
            {
                "Get": {
                    "Key": total_subreddits_key,
                    "TableName": DAILY_UPLOADS_TABLE_NAME,
                },
            },
            {
                "Get": {
                    "Key": todays_subreddits_key,
                    "TableName": DAILY_UPLOADS_TABLE_NAME,
                },
            },
        ]
    }

    # You get items but in an array of dicts containing "Item" as the key and
    # actual item as the value.
    items = ddb_helpers.transact_get_items(ddb, logger, **params)

    # Extract actual items from items
    items = [item["Item"] for item in items]

    # Deserialize the items and extract total_subreddits_count and todays_subreddits_count items.
    total_subreddits_item_deserialized, todays_subreddit_item_deserialized = [
        GatherPosts.deserialize_PK_SK_count(item) for item in items
    ]

    return (
        total_subreddits_item_deserialized["count"]
        == todays_subreddit_item_deserialized["count"]
    )


def needs_to_execute(bucket_name, s3, logger):
    params = {"BucketName": bucket_name}
    if s3_helpers.bucket_exists(s3, logger, **params):
        logger.info("Exiting")
        return False

    else:
        logger.info(f"Going ahead with downloading videos")
        return True
