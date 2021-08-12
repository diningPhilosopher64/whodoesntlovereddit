import boto3, os, sys
from pathlib import Path

# Making the current directory in which this file is in discoverable to python
sys.path.append(os.path.join(os.path.dirname(__file__)))

from entities.DailyUpload import DailyUpload
from entities.RedditAccount import RedditAccount

ddb = boto3.client("dynamodb", region_name="ap-south-1")

REDDIT_AUTH_URL = os.getenv("REDDIT_AUTH_URL")
REDDIT_ACCOUNTS_TABLE_NAME = os.getenv("REDDIT_ACCOUNTS_TABLE_NAME")
DAILY_UPLOADS_TABLE = os.getenv("DAILY_UPLOADS_TABLE_NAME")


def run(event, context):

    # TODO: Hardcoding subreddit value for now. In production, should extract from queue:
    subreddit = "funny"
    # Getting from env here because, if container is warm, it will fetch from the previously
    # executed subreddit url.
    REDDIT_API_URL_TOP = os.getenv("REDDIT_API_URL_TOP")
    REDDIT_API_URL_TOP = REDDIT_API_URL_TOP.replace("placeholder_value", subreddit)

    daily_upload = DailyUpload(subreddit=subreddit)
    reddit_account = RedditAccount(subreddit=subreddit, ddb=ddb)

    # Fetch account details from reddit accounts table and update object
    reddit_account.fetch_and_update_account_details(REDDIT_ACCOUNTS_TABLE_NAME)

    # Authenticate with reddit api and fetch access token
    reddit_account.authenticate_with_api()
    reddit_account.fetch_and_update_access_token(REDDIT_AUTH_URL)

    # Keep fetching and parsing posts from reddit api till daily_upload.total_duration
    # is more than 600 seconds. Will use the 'after' param to keep going backwards.
    after = None
    while daily_upload.total_duration < 601:
        posts = reddit_account.fetch_posts_as_json(
            REDDIT_API_URL_TOP, params={"limit": "100", "after": after}
        )
        daily_upload.parse_posts(posts)
        after = daily_upload.latest_post["name"]

    # After uploading this subreddits' urls, update the count of todays_subreddits_count
    # doing this as a transaction.
    try:
        res = ddb.transact_write_items(
            TransactItems=[
                {
                    "Put": {
                        "TableName": DAILY_UPLOADS_TABLE,
                        "Item": daily_upload.serialize_to_item(),
                    }
                },
                {
                    "Update": {
                        "TableName": DAILY_UPLOADS_TABLE,
                        "Key": {
                            "PK": {"S": daily_upload.date},
                            "SK": {"S": "todays_subreddits_count"},
                        },
                        "ConditionExpression": "attribute_exists(PK) and attribute_exists(SK)",
                        "UpdateExpression": "SET #count = #count + :inc",
                        "ExpressionAttributeNames": {"#count": "count"},
                        "ExpressionAttributeValues": {":inc": {"N": "1"}},
                    }
                },
            ]
        )

        if res["ResponseMetadata"]["HTTPStatusCode"] != 200:
            raise Exception("Failed to write transaction")

    except Exception as e:
        print(e)
        return {"error": e}

    # Prepping up for fetching todays_subreddits_count an total_subreddits_count from DailyUploads table.
    key = daily_upload.key()

    total_subreddits_key = daily_upload.key()
    todays_subreddits_key = daily_upload.key()

    total_subreddits_key["SK"]["S"] = "total_subreddits_count"
    todays_subreddits_key["SK"]["S"] = "todays_subreddits_count"

    try:
        res = ddb.transact_get_items(
            TransactItems=[
                {
                    "Get": {
                        "Key": total_subreddits_key,
                        "TableName": DAILY_UPLOADS_TABLE,
                    },
                },
                {
                    "Get": {
                        "Key": todays_subreddits_key,
                        "TableName": DAILY_UPLOADS_TABLE,
                    },
                },
            ]
        )

    except Exception as e:
        print(e)
        return {"error": e}

    # Extract items from response
    items = [response["Item"] for response in res["Responses"]]

    # Deserialize the items and extract total_subreddits_count and todays_subreddits_count items.
    total_subreddits_item_deserialized, todays_subreddit_item_deserialized = [
        DailyUpload.deserialize_PK_SK_count(item) for item in items
    ]

    # If evaluates to true, then push subreddit groups to download-videos-SQS
    if (
        total_subreddits_item_deserialized["count"]
        == todays_subreddit_item_deserialized["count"]
    ):
        # Add code here to push to SQS
        # and then send custom response to show today's urls of all subreddits have been processed.
        return {
            "success": f"All subreddits have been processed and uploaded urls for date {daily_upload.date}"
        }

    return {
        subreddit: f"successfully processed {subreddit} for date: {daily_upload.date}"
    }


# while daily_upload.total_duration < 601:
#     posts = reddit_account.fetch_posts_as_json(
#         REDDIT_API_URL_TOP, params={"limit": "100"}
#     )

#     daily_upload.parse_posts(posts)

# df_top = pd.DataFrame()
# total_duration = 0

# for post in posts["data"]["children"]:
#     if post["data"]["is_video"]:
#         df_top = df_top.append(
#             {
#                 "title": post["data"]["title"],
#                 "upvote_ratio": post["data"]["upvote_ratio"],
#                 "ups": post["data"]["ups"],
#                 "downs": post["data"]["downs"],
#                 "score": post["data"]["score"],
#                 "url": post["data"]["url"],
#             },
#             ignore_index=True,
#         )

#         total_duration += int(post["data"]["media"]["reddit_video"]["duration"])

# df_top = df_top.sort_values(
#     ["score", "upvote_ratio", "ups"], ascending=False, axis=0
# )

# daily_upload.urls = daily_upload.urls + df_top["url"].tolist()
# daily_upload.total_duration = total_duration

# Has to be done at the end when you know you have more than 600 seconds of content.
