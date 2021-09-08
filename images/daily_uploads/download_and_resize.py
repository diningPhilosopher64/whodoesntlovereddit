import boto3, os, logging, pprint, json
from pathlib import Path

from datetime import datetime, timedelta


pp = pprint.PrettyPrinter(indent=2, compact=True, width=80)

# Initialize logger and its config.
logger = logging.getLogger()
# logger.setLevel(logging.INFO)

from entities.FilterPosts import FilterPosts
from entities.DownloadPosts import DownloadPosts
from entities.VideoProcessing import VideoProcessing

POSTS_DOWNLOAD_LOCATION = os.getenv("POSTS_DOWNLOAD_LOCATION", "posts")
UNPARSED_SUBREDDITS_GROUP = os.getenv("UNPARSED_SUBREDDITS_GROUP")

s3 = boto3.client("s3")


def run():
    for item in os.listdir(POSTS_DOWNLOAD_LOCATION):
        posts_json_file = Path(POSTS_DOWNLOAD_LOCATION) / item / f"{item}.json"
        logger.info(f"Downloading posts from the file {posts_json_file}")
        with open(posts_json_file, "r") as f:
            posts_to_download = json.load(f)

        download_posts = DownloadPosts(
            s3=s3,
            posts=posts_to_download,
            bucket_name=UNPARSED_SUBREDDITS_GROUP,
            logger=logging.getLogger(),
            download_path=Path(POSTS_DOWNLOAD_LOCATION) / item,
            encode_path=Path(POSTS_DOWNLOAD_LOCATION) / item / "encoded",
        )

        download_posts.download_videos()

        logger.info(f"Finished posts of the file {posts_json_file}")
