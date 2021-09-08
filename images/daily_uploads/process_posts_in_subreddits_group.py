import boto3, os, logging, pprint, json
from multiprocessing import Process
from datetime import datetime, timedelta
from pathlib import Path


from entities.FilterPosts import FilterPosts
from entities.DownloadPosts import DownloadPosts
from entities.VideoProcessing import VideoProcessing
from helpers import s3 as s3_helpers

pp = pprint.PrettyPrinter(indent=2, compact=True, width=80)


ddb = boto3.client("dynamodb", region_name="ap-south-1")
s3 = boto3.client("s3")
sqs = boto3.client("sqs", region_name="ap-south-1")

DAILY_UPLOADS_TABLE_NAME = os.getenv("DAILY_UPLOADS_TABLE_NAME")
MAX_VIDEO_DURATION = int(os.getenv("MAX_VIDEO_DURATION"))
UNPARSED_SUBREDDITS_GROUP = os.getenv("UNPARSED_SUBREDDITS_GROUP")
POSTS_DOWNLOAD_LOCATION = os.getenv("POSTS_DOWNLOAD_LOCATION", "posts")

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger()


def process_posts():
    logger.info(f"Current working directory is {os.getcwd()}")
    bucket_name = UNPARSED_SUBREDDITS_GROUP

    # TODO: Make this lambda idempotent.
    # if not needs_to_execute(bucket_name, s3, logger):
    #     return {"note": f"{bucket_name} bucket already exists. Exiting."}

    parsed_subreddits_group = parse_subreddits_group(bucket_name)
    logger.info("Parsed subreddit groups")
    logger.info(pp.pformat(parsed_subreddits_group))

    filter_posts = FilterPosts(
        ddb=ddb,
        subreddits_group=parsed_subreddits_group,
        # date=str(datetime.today().date()),
        date="2021-09-07",
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

    # posts_to_download = posts

    split_posts_across_videos(posts_to_download)


def split_posts_across_videos(posts):
    total_duration = 0
    start_idx = 0
    idx = 0
    counter = 1

    for idx, post in enumerate(posts):
        total_duration += post["duration"]

        if total_duration > MAX_VIDEO_DURATION:
            create_posts_json_file(posts, start_idx, idx + 1, counter)
            start_idx = idx + 1
            total_duration = 0
            counter += 1

    total_duration = 0
    idx = start_idx
    while idx < len(all_posts):
        total_duration += all_posts[idx]["duration"]
        idx += 1

    if total_duration > MAX_VIDEO_DURATION:
        print("total duration of final video greater than MAX_VIDEO_DURATION")
        create_posts_json_file(posts, start_idx, len(all_posts), counter)
    else:
        print(
            "total duration of final video lesser than MAX_VIDEO_DURATION. So appending final video posts to penultimate video posts"
        )
        last_posts_json_file = (
            Path(POSTS_DOWNLOAD_LOCATION)
            / f"posts_{counter - 1}"
            / f"posts_{counter -1}.json"
        )

        with open(last_posts_json_file, "r") as f:
            contents = json.load(f)

        contents = contents + posts[start_idx : len(posts)]

        with open(last_posts_json_file, "w") as f:
            json.dump(contents, f, indent=2)


def create_posts_json_file(posts, first_idx, last_idx, counter):
    posts_part_folder = Path(POSTS_DOWNLOAD_LOCATION) / f"posts_{counter}"
    posts_part_folder.mkdir(parents=True, exist_ok=True)
    posts_part_dict = posts[first_idx:last_idx]
    posts_part_file = posts_part_folder / f"posts_{counter}.json"

    with open(posts_part_file, "w") as f:
        json.dump(posts_part_dict, f, indent=2)


# def split_posts_across_videos(posts):
#     total_duration = 0
#     start_idx = 0
#     idx = 0
#     counter = 1
#     video_stamps = []

#     while idx < len(posts):
#         total_duration += posts[idx]["duration"]

#         if total_duration > MAX_VIDEO_DURATION:
#             posts_part_folder = Path(POSTS_DOWNLOAD_LOCATION) / f"posts_{counter}"
#             posts_part_folder.mkdir(parents=True, exist_ok=True)

#             posts_part_dict = posts[start_idx:idx]
#             posts_part_file = posts_part_folder / f"posts_{counter}.json"

#             with open(posts_part_file, "w") as f:
#                 json.dump(posts_part_dict, f, indent=2)

#             # video_stamps.append((counter, start_idx, idx))
#             start_idx = idx + 1
#             total_duration = 0
#             counter += 1

#         idx += 1


def parse_subreddits_group(subreddits_group) -> list:
    subreddits_group_arr = subreddits_group.split("-")
    return subreddits_group_arr[4:]
