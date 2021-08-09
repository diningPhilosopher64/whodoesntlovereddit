import requests, pandas as pd, boto3
import sys, os

sys.path.append(os.path.join(os.path.dirname(__file__)))

from lib import db_helpers


ddb = boto3.client("dynamodb")

# Replace placeholder_value with value from the event object.

headers = {"User-Agent": "placeholder_valueAPI/0.0.1"}

# Initializing without the actual username and password
data = {"grant_type": "password", "username": "", "password": ""}


REDDIT_API_URL_TOP = os.getenv("REDDIT_API_URL_TOP")
REDDIT_AUTH_URL = os.getenv("REDDIT_AUTH_URL")
REDDIT_ACCOUNTS_TABLE_NAME = os.getenv("REDDIT_ACCOUNTS_TABLE_NAME")


def run(event, context):

    # Hardcoding subreddit value for now. In production, should extract from queue:
    subreddit = "funny"

    get_item = {"subreddit": {"S": subreddit}}
    CLIENT_ID = None
    SECRET_KEY = None
    USERNAME = None
    PASSWORD = None

    try:
        response = ddb.get_item(TableName=REDDIT_ACCOUNTS_TABLE_NAME, Key=get_item)
        item = db_helpers.deserialize_db_item(response["Item"])
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

    print("Auth request response ", res.json())

    ACCESS_TOKEN = res.json()["access_token"]

    headers["Authorization"] = f"bearer {ACCESS_TOKEN}"

    res = requests.get(REDDIT_API_URL_TOP, headers=headers)

    # posts = []
    # for post in res.json()["data"]["children"]:
    #     print(post["data"]["title"])

    response = {"hello": "world", "response": res.json()}
    return response
