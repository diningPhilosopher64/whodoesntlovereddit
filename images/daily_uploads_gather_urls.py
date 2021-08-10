import requests, boto3, pandas as pd, os, sys
from pathlib import Path

# Making the current directory in which this file is in discoverable to python
sys.path.append(os.path.join(os.path.dirname(__file__)))

from lib import db_helpers
from entities.DailyUpload import DailyUpload
from entities.RedditAccount import RedditAccount


ddb = boto3.client("dynamodb", region_name="ap-south-1")


REDDIT_AUTH_URL = os.getenv("REDDIT_AUTH_URL")
REDDIT_ACCOUNTS_TABLE_NAME = os.getenv("REDDIT_ACCOUNTS_TABLE_NAME")
DAILY_UPLOADS_TABLE = os.getenv("DAILY_UPLOADS_TABLE_NAME")


def run(event, context):

    # TODO: Hardcoding subreddit value for now. In production, should extract from queue:
    subreddit = "funny"
    REDDIT_API_URL_TOP = os.getenv("REDDIT_API_URL_TOP")
    REDDIT_API_URL_TOP = REDDIT_API_URL_TOP.replace("placeholder_value", subreddit)

    daily_upload = DailyUpload(subreddit=subreddit)
    reddit_account = RedditAccount(subreddit=subreddit, ddb=ddb)

    # Fetch account details from reddit accounts table and update object
    reddit_account.fetch_and_update_account_details(REDDIT_ACCOUNTS_TABLE_NAME)

    # Authenticate with reddit api and fetch access token
    reddit_account.authenticate_with_api()
    reddit_account.fetch_access_token(REDDIT_AUTH_URL)

    posts = reddit_account.fetch_posts_as_json(
        REDDIT_API_URL_TOP, params={"limit": "100"}
    )

    df_top = pd.DataFrame()
    total_duration = 0

    for post in posts["data"]["children"]:
        if post["data"]["is_video"]:
            df_top = df_top.append(
                {
                    "title": post["data"]["title"],
                    "upvote_ratio": post["data"]["upvote_ratio"],
                    "ups": post["data"]["ups"],
                    "downs": post["data"]["downs"],
                    "score": post["data"]["score"],
                    "url": post["data"]["url"],
                },
                ignore_index=True,
            )

            total_duration += int(post["data"]["media"]["reddit_video"]["duration"])

    df_top = df_top.sort_values(
        ["score", "upvote_ratio", "ups"], ascending=False, axis=0
    )

    daily_upload.urls = daily_upload.urls + df_top["url"].tolist()
    daily_upload.total_duration = total_duration

    res = ddb.transact_write_items(
        TransactItems=[
            {
                "Put": {
                    "TableName": DAILY_UPLOADS_TABLE,
                    "Item": daily_upload.serialize_date_subreddit(),
                }
            },
            {
                "Put": {
                    "TableName": DAILY_UPLOADS_TABLE,
                    "Item": daily_upload.serialize_subreddit_date(),
                }
            },
        ]
    )

    response = {"hello": "world"}
    return response
