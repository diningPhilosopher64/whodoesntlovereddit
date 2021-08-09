import requests, pandas as pd, boto3
import sys, os


sys.path.append(os.path.join(os.path.dirname(__file__)))

from lib import db_helpers
from entities.DailyUpload import DailyUpload


ddb = boto3.client("dynamodb", region_name="ap-south-1")

# Replace placeholder_value with value from the event object.

headers = {"User-Agent": "placeholder_valueAPI/0.0.1"}

# Initializing without the actual username and password
data = {"grant_type": "password", "username": "", "password": ""}


REDDIT_AUTH_URL = os.getenv("REDDIT_AUTH_URL")
REDDIT_ACCOUNTS_TABLE_NAME = os.getenv("REDDIT_ACCOUNTS_TABLE_NAME")


def run(event, context):

    # TODO: Hardcoding subreddit value for now. In production, should extract from queue:
    subreddit = "funny"
    REDDIT_API_URL_TOP = os.getenv("REDDIT_API_URL_TOP")
    REDDIT_API_URL_TOP = REDDIT_API_URL_TOP.replace("placeholder_value", subreddit)

    daily_upload = DailyUpload(subreddit=subreddit)

    get_item = {"subreddit": {"S": subreddit}}
    CLIENT_ID = None
    SECRET_KEY = None
    USERNAME = None
    PASSWORD = None

    try:
        response = ddb.get_item(TableName=REDDIT_ACCOUNTS_TABLE_NAME, Key=get_item)
        item = db_helpers.deserialize_from_db_item(response["Item"])
        CLIENT_ID = item["personal_use_script"]
        SECRET_KEY = item["secret_key"]
        USERNAME = item["username"]
        PASSWORD = item["password"]

    except Exception as e:
        print(f"Failed with exception: {e.args[0]}")

    auth = requests.auth.HTTPBasicAuth(CLIENT_ID, SECRET_KEY)

    data["username"] = USERNAME
    data["password"] = PASSWORD

    # Request for access token from Reddit API
    res = requests.post(REDDIT_AUTH_URL, auth=auth, data=data, headers=headers)

    ACCESS_TOKEN = res.json()["access_token"]

    headers["Authorization"] = f"bearer {ACCESS_TOKEN}"

    res = requests.get(REDDIT_API_URL_TOP, headers=headers)

    posts = []
    df_top = pd.DataFrame()

    for post in res.json()["data"]["children"]:
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

    df_top = df_top.sort_values(
        ["score", "upvote_ratio", "ups"], ascending=False, axis=0
    )

    daily_upload.urls = list(df_top["url"])

    daily_uploads_table = os.getenv("DAILY_UPLOADS_TABLE_NAME")

    res = ddb.put_item(
        TableName=daily_uploads_table,
        Item=daily_upload.serialize_date_subreddit(),
    )

    print(res)

    response = {"hello": "world"}
    return response
