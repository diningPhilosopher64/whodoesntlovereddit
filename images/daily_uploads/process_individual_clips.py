import boto3, os, logging, pprint, json

# from time import time, time_ns
# from concurrent.futures import ProcessPoolExecutor, as_completed
from multiprocessing import Process
from datetime import datetime, timedelta
from pathlib import Path


pp = pprint.PrettyPrinter(indent=2, compact=True, width=80)

# Initialize logger and its config.
logger = logging.getLogger()


from entities.FilterPosts import FilterPosts
from entities.DownloadPosts import DownloadPosts
from entities.VideoProcessing import VideoProcessing
from helpers import s3 as s3_helpers

s3 = boto3.client("s3")
sqs = boto3.client("sqs", region_name="ap-south-1")


TRANSITION_CLIPS_BUCKET = os.getenv("TRANSITION_CLIPS_BUCKET")
INTRO_VIDEO_CLIPS_BUCKET = os.getenv("INTRO_VIDEO_CLIPS_BUCKET")
AUDIO_CLIPS_BUCKET = os.getenv("AUDIO_CLIPS_BUCKET")
OUTTRO_CLIPS_BUCKET = os.getenv("OUTTRO_CLIPS_BUCKET")


POSTS_DOWNLOAD_LOCATION = os.getenv("POSTS_DOWNLOAD_LOCATION", "posts")
UNPARSED_SUBREDDITS_GROUP = os.getenv("UNPARSED_SUBREDDITS_GROUP")


def run():

    for idx, item in enumerate(os.listdir(POSTS_DOWNLOAD_LOCATION)):
        encoded_files_path = Path(POSTS_DOWNLOAD_LOCATION) / item / "encoded"
        posts_json_file = Path(POSTS_DOWNLOAD_LOCATION) / item / f"{item}.json"

        logger.info(f"Processing individual clips of the file {posts_json_file}")
        with open(posts_json_file, "r") as f:
            posts = json.load(f)

        posts_for_processing = []
        for clip in os.listdir(encoded_files_path):
            post_name = get_post_from_name(posts, clip.split(".")[0])
            if post_name:
                posts_for_processing.append(post_name)

        video_processing = VideoProcessing(
            encode_path=encoded_files_path,
            posts=posts_for_processing,
            s3=s3,
            bucket_name=UNPARSED_SUBREDDITS_GROUP,
            final_video_name=UNPARSED_SUBREDDITS_GROUP + "_" + str(idx),
            logger=logger,
        )

        video_processing.process_video_clips(
            TRANSITION_CLIPS_BUCKET,
            INTRO_VIDEO_CLIPS_BUCKET,
            OUTTRO_CLIPS_BUCKET,
            AUDIO_CLIPS_BUCKET,
        )

        logger.info(
            f"Finished processing individual clips of the file {posts_json_file}"
        )


def get_post_from_name(posts, post_name):
    for post in posts:
        if post["name"] == post_name:
            return post
