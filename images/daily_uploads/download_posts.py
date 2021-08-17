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


ddb = boto3.client("dynamodb", region_name="ap-south-1")
s3 = boto3.client("s3")

DAILY_UPLOADS_TABLE_NAME = os.getenv("DAILY_UPLOADS_TABLE_NAME")
DAILY_UPLOADS_PROCESS_POSTS_FOR_A_SUBREDDIT_QUEUE_URL = os.getenv(
    "DAILY_UPLOADS_PROCESS_POSTS_FOR_A_SUBREDDIT_QUEUE_URL"
)


def run(event, context):
    subreddit = str(event["Records"][0]["body"])
    logger.info(f"Received the message: {subreddit} from event.")
    bucket_name = f"whodoesntlovereddit-{str(datetime.today().date())}-{subreddit}"
    bucket_exists = True
    try:
        s3.head_bucket(Bucket=bucket_name)
        logger.info(f"The bucket {bucket_name} already exists.")
        return {"note": f"{bucket_name} bucket already exists. Exiting"}
    except:
        logger.info(
            f"The bucket {bucket_name} doesn't exist. Going ahead with downloading videos"
        )
        pass

    gather_posts = GatherPosts(subreddit=subreddit, logger=logger)

    logger.info(
        f"Videos of Subreddit : {subreddit}, are being downloaded on {gather_posts.date} with timestamp: {time.time()}"
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

    download_posts.download_videos_from_posts()

    logger.info("In the current working directory, we have :")
    logger.info(pp.pformat(os.listdir(".")))

    logger.info("In the tmp directory, we have:")
    logger.info(pp.pformat(os.listdir("/tmp")))

    return {"response": "Successfully uploaded videos to s3."}
