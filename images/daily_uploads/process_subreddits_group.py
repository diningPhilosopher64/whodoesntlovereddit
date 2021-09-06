import boto3, os, logging, pprint, subprocess
from time import time, time_ns
from concurrent.futures import ProcessPoolExecutor, as_completed
from multiprocessing import Process
from datetime import datetime, timedelta

from botocore.retries import bucket

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
sqs = boto3.client("sqs", region_name="ap-south-1")


DAILY_UPLOADS_TABLE_NAME = os.getenv("DAILY_UPLOADS_TABLE_NAME")
TRANSITION_CLIPS_BUCKET = os.getenv("TRANSITION_CLIPS_BUCKET")
INTRO_VIDEO_CLIPS_BUCKET = os.getenv("INTRO_VIDEO_CLIPS_BUCKET")
AUDIO_CLIPS_BUCKET = os.getenv("AUDIO_CLIPS_BUCKET")
OUTTRO_CLIPS_BUCKET = os.getenv("OUTTRO_CLIPS_BUCKET")
LIKE_AND_SUBSCRIBE_CLIPS_BUCKET = os.getenv("LIKE_AND_SUBSCRIBE_CLIPS_BUCKET")
MAX_VIDEO_DURATION = os.getenv("MAX_VIDEO_DURATION")


def run(event, context):
    # Initialize logger and its config.
    logger = logging.getLogger()
    logger.setLevel(logging.INFO)
    # os.chdir("/tmp")
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

    filter_posts = FilterPosts(
        ddb=ddb,
        subreddits_group=parsed_subreddits_group,
        date=str(datetime.today().date()),
        logger=logger,
    )

    filter_posts.get_posts_of_subreddits_from_db(TableName=DAILY_UPLOADS_TABLE_NAME)
    filter_posts.marshall_and_sort_posts()
    filter_posts.filter_best_posts()

    posts = filter_posts.get_filtered_posts()
    filter_posts_yesterday = FilterPosts(
        ddb=ddb,
        subreddits_group=parsed_subreddits_group,
        date=str(datetime.today().date() - timedelta(days=1)),
        logger=logger,
    )
    try:
        filter_posts_yesterday.get_posts_of_subreddits_from_db(
            TableName=DAILY_UPLOADS_TABLE_NAME
        )

        filter_posts_yesterday.marshall_and_sort_posts()
        filter_posts_yesterday.filter_best_posts()

        posts_yesterday = filter_posts_yesterday.get_filtered_posts()

        posts_to_download = []

        for post in posts:
            if post not in posts_yesterday:
                posts_to_download.append(post)
    except:
        posts_to_download = posts

    download_posts = DownloadPosts(
        s3=s3,
        posts=posts_to_download,
        bucket_name=unparsed_subreddit_group,
        logger=logger,
        download_path="./tt",
        encode_path="./tt/encode",
    )
    download_posts.download_videos()

    total_duration = 0
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

    video_stamps = video_stamps[0:1]

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
        final_video_name=bucket_name + "_" + str(counter),
        logger=logger,
    )

    video_processing.process_video_clips(
        TRANSITION_CLIPS_BUCKET,
        INTRO_VIDEO_CLIPS_BUCKET,
        OUTTRO_CLIPS_BUCKET,
        AUDIO_CLIPS_BUCKET,
    )

    video_processing.concatenate_videos_and_render(LIKE_AND_SUBSCRIBE_CLIPS_BUCKET)

    print(f"Finished processing video {bucket_name + str(counter)}")

    print(f"Uploading the video: {video_processing.final_video_name}")

    # video_credits = [f'u/{post["author"]} - {post["url"]}' for post in current_video]
    video_credits = [f'u/{post["author"]}' for post in current_video]

    video_credits = "\n".join(video_credits)

    keywords = ", ".join(parse_subreddits_group(video_processing.bucket_name))
    keywords = f'"{keywords}"'
    description = f"""
    Enjoy watching these funny memes.

    Try not to laugh as you watch these funny/awesome/wholesome/creative/amazing  videos.

    Like the video and Subscribe for more.

    ➟ Credits (Please check out the creators of these clips, without them these kinds of videos won't exist):\n
    🎥 CONTENT CREATORS FEATURED (Show them some love):
    {video_credits}

    E-mail me on my business e-mail if you want your video removed or if i missed your credit (if i missed it, you will be credited with special thanks in the comments.)
    I browse hundreds of repost pages for one video and without a watermark, it's impossible for me to find the source of every clip.

    For promotions/removals, contact my email:📩  vidsfromaroundtheinternet@gmail.com

    ⚠️ Copyright Disclaimer, Under Section 107 of the Copyright Act 1976, allowance is made for 'fair use' for purposes
    such as criticism, comment, news reporting, teaching, scholarship, and research.
    Fair use is a use permitted by copyright statute that might otherwise be infringing.
    Non-profit, educational or personal use tips the balance in favor of fair use.

    ⚠️ Community Guidelines Disclaimer
    This video is for entertainment purposes only. My videos are not intented to bully / harass or offend anyone. The clips shown are funny, silly, they relieve stress and anxiety, create good vibes and make viewers laugh.  Many of them leaving feedback about these videos helping with depression, anxiety and all type of bad moods.
    This video should not be taken seriously.
    Do not perform any actions shown in this video!
    """

    description = f'"{description}"'
    category_id = '"23"'
    title = f'"{video_processing.final_video_name}"'
    file_path = f'"{video_processing.final_video_path}"'

    upload_cmd = [
        "python",
        "upload_video.py",
        f"--file={file_path}",
        f"--title={title}",
        f"--description={description}",
        f"--keywords={keywords}",
        f"--category={category_id}",
        '--privacyStatus="private"',
    ]

    os.system(" ".join(upload_cmd))

    videos_of_the_day_bucket = bucket_name.split("-")
    videos_of_the_day_bucket = videos_of_the_day_bucket[0:4]
    videos_of_the_day_bucket = "-".join(videos_of_the_day_bucket)

    kwargs = {"Bucket": videos_of_the_day_bucket}

    if not s3_helpers.bucket_exists(s3, logger, kwargs):
        kwargs = {
            "Bucket": kwargs["Bucket"],
            "ACL": "private",
            "CreateBucketConfiguration": {"LocationConstraint": "ap-south-1"},
        }
        s3_helpers.create_bucket(s3, logger, kwargs)

    s3_helpers.upload_file(
        s3,
        logger,
        bucket_name=videos_of_the_day_bucket,
        file_path=video_processing.final_video_path,
    )


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
