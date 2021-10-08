import boto3, os, sys, logging, pprint, operator

# from time import time
import time, random
from pathlib import Path
from concurrent.futures import ProcessPoolExecutor, as_completed
from datetime import datetime
import requests

pp = pprint.PrettyPrinter(indent=2, compact=True, width=80)

# Initialize logger and its config.
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger()


from entities.GatherPosts import GatherPosts
from entities.TTS import TTS
from entities.RedditAccount import RedditAccount
from helpers import ddb as ddb_helpers
from helpers import sqs as sqs_helpers

from daily_uploads.subredditList import subreddits as all_subreddits


ddb = boto3.client("dynamodb", region_name="ap-south-1")
# sqs = boto3.client("sqs")

REDDIT_AUTH_URL = os.getenv("REDDIT_AUTH_URL")
REDDIT_ACCOUNTS_TABLE_NAME = os.getenv("REDDIT_ACCOUNTS_TABLE_NAME")
REDDIT_API_URL_NEW = "https://oauth.reddit.com/r/placeholder_value/new"
DAILY_UPLOADS_TABLE_NAME = os.getenv("DAILY_UPLOADS_TABLE_NAME")
VIDEO_URLS_TABLE_NAME = os.getenv("VIDEO_URLS_TABLE_NAME")
REDDIT_API_URL_TOP = "https://oauth.reddit.com/r/AskReddit/top"


def run():
    logger = logging.getLogger()

    logger.info("Hello world")

    subreddit = "AskReddit"
    reddit_account = RedditAccount(subreddit=subreddit, ddb=ddb, logger=logger)
    reddit_account.fetch_and_update_account_details(REDDIT_ACCOUNTS_TABLE_NAME)
    reddit_account.authenticate_with_api()
    reddit_account.fetch_and_update_access_token(REDDIT_AUTH_URL)

    posts = fetch_posts(reddit_account)

    posts_to_download = [
        post for post in posts if not is_old_post(post, VIDEO_URLS_TABLE_NAME, logger)
    ]

    # TODO: Considering only 1 post for now.
    post = posts_to_download[-1]

    post_name = post["name"]

    posts_root_path = Path(os.getcwd()) / "posts"

    posts_root_path.mkdir(parents=True, exist_ok=True)

    tts = TTS(
        reddit_account=reddit_account,
        post=post,
        posts_root_path=posts_root_path,
        generic_index_file_path="generic_index.html",
        logger=logger,
    )

    tts.fetch_and_filter_comments()
    tts.fetch_and_filter_replies_to_comments()
    tts.process_and_render()
    tts.stitch_clips_together()


def update_db_of_considered_posts(posts, TABLE_NAME, subreddits_group, logger):
    # 25 hours is 90000 seconds
    EXPIRES_IN = 90000
    EXPIRES_AT = int(time.time()) + EXPIRES_IN
    date = str(datetime.today().date())

    for idx, post in enumerate(posts):
        pk = "-".join(subreddits_group) + "-" + date
        sk = post["url"]
        kwargs = {
            "TableName": TABLE_NAME,
            "Item": {"PK": {"S": pk}, "SK": {"S": sk}, "TTL": {"N": str(EXPIRES_AT)}},
        }

        logger.info(f"Updating {VIDEO_URLS_TABLE_NAME} with post {idx}")

        ddb_helpers.put_item(ddb, **kwargs)


def is_old_post(post, TABLE_NAME, logger):
    date = str(datetime.today().date())
    pk = "askreddit" + "-" + date
    sk = post["url"]

    kwargs = {
        "TableName": TABLE_NAME,
        "Key": {"PK": {"S": pk}, "SK": {"S": sk}},
    }
    return True if ddb_helpers.item_exists(ddb=ddb, logger=logger, **kwargs) else False


def fetch_posts(reddit_account):
    after = None
    posts = reddit_account.fetch_posts_as_json(
        REDDIT_API_URL_TOP, params={"limit": "100", "after": after}
    )

    posts = posts["data"]["children"]

    actual_posts = []

    for post in posts:
        actual_posts.append(post["data"])

    actual_posts.sort(key=operator.itemgetter("ups"))
    logger.info("Fetch top posts of the day")

    return actual_posts
