import boto3, os, sys, logging, pprint
from time import time


# Initialize logger and its config.
logger = logging.getLogger()
logger.setLevel(logging.INFO)

from entities.FilterPosts import FilterPosts
from entities.DownloadPosts import DownloadPosts
from helpers import sqs as sqs_helpers
from helpers import s3 as s3_helpers

ddb = boto3.client("dynamodb", region_name="ap-south-1")
s3 = boto3.client("s3")
sqs = boto3.client("sqs")


DAILY_UPLOADS_TABLE_NAME = os.getenv("DAILY_UPLOADS_TABLE_NAME")


def run(event, context):

    unparsed_subreddit_group = str(event["Records"][0]["body"])
    logger.info(f"Received the following item from SQS: {unparsed_subreddit_group}")
    bucket_name = unparsed_subreddit_group

    # TODO: Make this lambda idempotent.
    if not needs_to_execute(bucket_name, s3, logger):
        return {"note": f"{bucket_name} bucket already exists. Exiting."}

    parsed_subreddit_group = parse_subreddit_group(bucket_name)

    # posts_arr = get_posts_of_subreddits_from_db(ddb, parsed_subreddit_group, logger)

    filter_posts = FilterPosts(
        ddb, subreddit_group=parsed_subreddit_group, logger=logger
    )

    filter_posts.get_posts_of_subreddits_from_db(TableName=DAILY_UPLOADS_TABLE_NAME)
    filter_posts.marshall_and_sort_posts()
    filter_posts.filter_best_posts()

    posts = filter_posts.get_filtered_posts()

    download_posts = DownloadPosts(
        s3=s3, posts=posts, bucket_name=unparsed_subreddit_group, logger=logger
    )

    download_posts.download_videos()

    video_processing = VideoProcessing(
        download_path=download_posts.downloa_path, posts=posts, logger=logger
    )

    video_processing.process_each_video_in_parallel()

    video_processing.concatenate_videos()


# def push_subreddit_group_to_sqs(subreddit_group):
#     pass

# update processed_subreddit_group count and check if I'm the last group of today
# update_processed_subreddit_groups_count(ddb, logger, filter_posts.gather_posts)

# if last updated and last subreddit group of today, then push to queue


# def update_processed_subreddit_groups_count(
#     ddb, logger, gather_posts, unparsed_subreddit_group
# ):

#     params = {
#         "TableName": DAILY_UPLOADS_TABLE_NAME,
#         "Key": {
#             "PK": {"S": gather_posts.date},
#             "SK": {"S": "todays_subreddit_groups_count"},
#         },
#         "ConditionExpression": "attribute_exists(PK) and attribute_exists(SK)",
#         "UpdateExpression": "SET #count = #count + :inc, #last_processed_subreddit_group = :last_processed_subreddit_group",
#         "ExpressionAttributeNames": {
#             "#count": "count",
#             "#last_processed_subreddit_group": "last_processed_subreddit_group",
#         },
#         "ExpressionAttributeValues": {
#             ":inc": {"N": "1"},
#             ":last_processed_subreddit_group": {"S": unparsed_subreddit_group},
#         },
#         "ReturnValues": "ALL_NEW",
#     }

#     ddb_helpers.update_item(ddb, logger, **params)


def needs_to_execute(bucket_name, s3, logger):
    params = {"Bucket": bucket_name}
    if s3_helpers.bucket_exists(s3, logger, **params):
        logger.info("Exiting")
        return False

    else:
        logger.info(f"Going ahead with downloading videos")
        return True


def parse_subreddit_group(subreddit_group):
    subreddit_group_arr = subreddit_group.split("-")
    return subreddit_group_arr[4:]


# def push_to_sqs_for_stitching_subreddit_group_videos(todays_date):
#     from subreddit_groups import subreddit_groups

#     params = {
#         "QueueUrl": DAILY_UPLOADS_PROCESS_SUBREDDIT_GROUP_QUEUE_URL,
#         "MessageBody": None,
#     }

#     for group in subreddit_groups:
#         group_str = "-".join(group)
#         group_str = "whodoesntlovereddit" + "-" + todays_date + "-" + group_str
#         params["MessageBody"] = group_str
#         sqs_helpers.send_message(sqs, logger, **params
