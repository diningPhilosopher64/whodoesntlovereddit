import boto3, os, sys, logging, pprint, asyncio
from time import time, time_ns
from concurrent.futures import ProcessPoolExecutor, as_completed
from multiprocessing import Process

pp = pprint.PrettyPrinter(indent=2, compact=True, width=80)

# Initialize logger and its config.
logger = logging.getLogger()
logger.setLevel(logging.INFO)

from entities.FilterPosts import FilterPosts
from entities.DownloadPosts import DownloadPosts
from entities.VideoProcessing import VideoProcessing
from helpers import sqs as sqs_helpers
from helpers import s3 as s3_helpers

ddb = boto3.client("dynamodb", region_name="ap-south-1")
s3 = boto3.client("s3")
sqs = boto3.client("sqs")


DAILY_UPLOADS_TABLE_NAME = os.getenv("DAILY_UPLOADS_TABLE_NAME")
TRANSITION_CLIPS_BUCKET = os.getenv("TRANSITION_CLIPS_BUCKET")
INTRO_CLIPS_BUCKET = os.getenv("INTRO_CLIPS_BUCKET")
AUDIO_CLIPS_BUCKET = os.getenv("AUDIO_CLIPS_BUCKET")
OUTTRO_CLIPS_BUCKET = os.getenv("OUTTRO_CLIPS_BUCKET")
LIKE_AND_SUBSCRIBE_CLIPS_BUCKET = os.getenv("LIKE_AND_SUBSCRIBE_CLIPS_BUCKET")


def run(event, context):
    # Initialize logger and its config.
    logger = logging.getLogger()
    logger.setLevel(logging.INFO)
    os.chdir("/tmp")
    logger.info(f"Current working directory is {os.getcwd()}")
    unparsed_subreddit_group = str(event["Records"][0]["body"])
    logger.info(f"Received the following item from SQS: {unparsed_subreddit_group}")
    bucket_name = unparsed_subreddit_group

    # TODO: Make this lambda idempotent.
    # if not needs_to_execute(bucket_name, s3, logger):
    #     return {"note": f"{bucket_name} bucket already exists. Exiting."}

    parsed_subreddits_group = parse_subreddits_group(bucket_name)
    logger.info("Parsed subreddit groups")
    logger.info(pp.pformat(parsed_subreddits_group))

    # posts_arr = get_posts_of_subreddits_from_db(ddb, parsed_subreddit_group, logger)

    filter_posts = FilterPosts(
        ddb, subreddits_group=parsed_subreddits_group, logger=logger
    )

    filter_posts.get_posts_of_subreddits_from_db(TableName=DAILY_UPLOADS_TABLE_NAME)
    filter_posts.marshall_and_sort_posts()
    filter_posts.filter_best_posts()

    posts = filter_posts.get_filtered_posts()

    download_posts = DownloadPosts(
        s3=s3,
        posts=posts,
        bucket_name=unparsed_subreddit_group,
        logger=logger,
        # download_path="./tt",
        # encode_path="./tt/encode",
    )
    # download_posts.download_videos()

    total_duration = 0
    MAX_VIDEO_DURATION = 70
    start_idx = 0
    idx = 0
    counter = 1
    video_stamps = []

    while idx < len(posts):
        total_duration += posts[idx]["duration"]

        if total_duration > MAX_VIDEO_DURATION:
            video_stamps.append((counter, start_idx, idx))
            start_idx = idx + 1
            total_duration = 0
            counter += 1

        idx += 1

    video_stamps = video_stamps[0:2]

    for counter, start_stamp, end_stamp in video_stamps:
        process = Process(
            target=process_a_video,
            args=(
                download_posts.encode_path,
                posts[start_stamp:end_stamp],
                s3,
                bucket_name,
                counter,
                logging.getLogger(),
            ),
        )

        process.start()
        process.join()


def process_a_video(
    encode_path,
    current_video,
    s3,
    bucket_name,
    counter,
    logger,
):
    video_processing = VideoProcessing(
        encode_path=encode_path,
        posts=current_video,
        s3=s3,
        bucket_name=bucket_name,
        final_video_name=bucket_name + "_" + str(time_ns()),
        logger=logger,
    )

    print("Processing ", video_processing.final_video_path)

    video_processing.process_video_clips(
        TRANSITION_CLIPS_BUCKET,
        INTRO_CLIPS_BUCKET,
        OUTTRO_CLIPS_BUCKET,
        AUDIO_CLIPS_BUCKET,
    )

    video_processing.concatenate_videos_and_render()

    print(f"Finished processing video {bucket_name + str(counter)}")


def needs_to_execute(bucket_name, s3, logger):
    params = {"Bucket": bucket_name}
    if s3_helpers.bucket_exists(s3, logger, **params):
        logger.info("Exiting")
        return False

    else:
        logger.info(f"Going ahead with downloading videos")
        return True


def parse_subreddits_group(subreddits_group) -> list:
    subreddits_group_arr = subreddits_group.split("-")
    return subreddits_group_arr[4:]


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


# video_processing = VideoProcessing(
#     encode_path=download_posts.encode_path,
#     posts=posts,
#     s3=s3,
#     bucket_name=bucket_name,
#     final_video_name=unparsed_subreddit_group,
#     logger=logger,
# )

# video_processing.upload_subreddits_group_videos_to_s3()


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
