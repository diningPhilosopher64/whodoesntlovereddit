import boto3, os, sys, logging, pprint
from pathlib import Path

pp = pprint.PrettyPrinter(indent=2, compact=True, width=80)

# Initialize logger and its config.
logger = logging.getLogger()
logger.setLevel(logging.INFO)

# Making the current directory in which this file is in discoverable to python
sys.path.append(os.path.join(os.path.dirname(__file__)))

from entities.GatherUrls import GatherUrls
from entities.RedditAccount import RedditAccount
from helpers import ddb as ddb_helpers
from helpers import sqs as sqs_helpers

from daily_uploads.subredditList import subreddits as all_subreddits


ddb = boto3.client("dynamodb", region_name="ap-south-1")
sqs = boto3.client("sqs")

REDDIT_AUTH_URL = os.getenv("REDDIT_AUTH_URL")
REDDIT_ACCOUNTS_TABLE_NAME = os.getenv("REDDIT_ACCOUNTS_TABLE_NAME")
DAILY_UPLOADS_TABLE_NAME = os.getenv("DAILY_UPLOADS_TABLE_NAME")
DAILY_UPLOADS_PROCESS_POSTS_FOR_A_SUBREDDIT_QUEUE_URL = os.getenv(
    "DAILY_UPLOADS_PROCESS_POSTS_FOR_A_SUBREDDIT_QUEUE_URL"
)


def run(event, context):

    # TODO: Hardcoding subreddit value for now. In production, should extract from queue:
    # subreddit = "funny"
    subreddit = str(event["Records"][0]["body"])
    logger.info(f"Subreddit : {subreddit}, is being processed")

    # Getting from env here because, if container is warm, it will fetch from the previously
    # executed subreddit url.
    REDDIT_API_URL_TOP = os.getenv("REDDIT_API_URL_TOP")
    REDDIT_API_URL_TOP = REDDIT_API_URL_TOP.replace("placeholder_value", subreddit)

    gather_urls = GatherUrls(subreddit=subreddit, logger=logger)
    reddit_account = RedditAccount(subreddit=subreddit, ddb=ddb, logger=logger)

    reddit_account.fetch_and_update_account_details(REDDIT_ACCOUNTS_TABLE_NAME)
    reddit_account.authenticate_with_api()
    reddit_account.fetch_and_update_access_token(REDDIT_AUTH_URL)

    # Keep fetching and parsing posts from reddit api till gather_urls.total_duration
    # is more than 600 seconds. Will use the 'after' param to keep going backwards.
    after = None
    while gather_urls.total_duration < 601:
        logger.info(f"Fetching subreddit: {subreddit} posts after {after}")
        posts = reddit_account.fetch_posts_as_json(
            REDDIT_API_URL_TOP, params={"limit": "100", "after": after}
        )
        gather_urls.parse_posts(posts)
        after = gather_urls.latest_post["name"]

    # After uploading this subreddits' urls, update the count of todays_subreddits_count
    # doing this as a transaction.
    # try:
    params = {
        "TransactItems": [
            {
                "Put": {
                    "TableName": DAILY_UPLOADS_TABLE_NAME,
                    "Item": gather_urls.serialize_to_item(),
                }
            },
            {
                "Update": {
                    "TableName": DAILY_UPLOADS_TABLE_NAME,
                    "Key": {
                        "PK": {"S": gather_urls.date},
                        "SK": {"S": "todays_subreddits_count"},
                    },
                    "ConditionExpression": "attribute_exists(PK) and attribute_exists(SK)",
                    "UpdateExpression": "SET #count = #count + :inc",
                    "ExpressionAttributeNames": {"#count": "count"},
                    "ExpressionAttributeValues": {":inc": {"N": "1"}},
                }
            },
        ]
    }

    res = ddb_helpers.transact_write_items(ddb, logger, **params)

    logger.info(
        f"Successfully updated DB for {subreddit} subreddit on {gather_urls.date}"
    )

    push_subreddits_to_queue(logger)

    res[
        "subreddit"
    ] = f"successfully gathered posts for subreddit: {subreddit}  on : {gather_urls.date} and pushed to {DAILY_UPLOADS_PROCESS_POSTS_FOR_A_SUBREDDIT_QUEUE_URL} for processing."

    return res


def push_subreddits_to_queue(logger):
    # TODO: Look at avg running time of daily_uploads_process_posts lambda
    # and update delay_seconds in the for loop.
    delay_seconds = 0
    params = {
        "QueueUrl": DAILY_UPLOADS_PROCESS_POSTS_FOR_A_SUBREDDIT_QUEUE_URL,
        "MessageBody": None,
        "DelaySeconds": delay_seconds,
    }

    for subreddit in all_subreddits:
        params["MessageBody"] = subreddit
        params["DelaySeconds"] = delay_seconds
        res = sqs_helpers.send_message(sqs, logger, **params)

        # TODO: Update this accordingly
        # delay_seconds += 10

    # # Prepping up for fetching todays_subreddits_count an total_subreddits_count from DailyUploads table.
    # key = gather_urls.key()

    # total_subreddits_key = gather_urls.key()
    # todays_subreddits_key = gather_urls.key()

    # total_subreddits_key["SK"]["S"] = "total_subreddits_count"
    # todays_subreddits_key["SK"]["S"] = "todays_subreddits_count"

    # params = {
    #     "TransactItems": [
    #         {
    #             "Get": {
    #                 "Key": total_subreddits_key,
    #                 "TableName": DAILY_UPLOADS_TABLE_NAME,
    #             },
    #         },
    #         {
    #             "Get": {
    #                 "Key": todays_subreddits_key,
    #                 "TableName": DAILY_UPLOADS_TABLE_NAME,
    #             },
    #         },
    #     ]
    # }

    # res = ddb_helpers.transact_get_items(ddb, logger, **params)

    # logger.info(f"{subreddit} subreddit has updated todays_subreddit_count ")

    # # Extract items from response
    # items = [response["Item"] for response in res["Responses"]]

    # # Deserialize the items and extract total_subreddits_count and todays_subreddits_count items.
    # total_subreddits_item_deserialized, todays_subreddit_item_deserialized = [
    #     GatherUrls.deserialize_PK_SK_count(item) for item in items
    # ]

    # # If evaluates to true, then push subreddit groups to ProcessUrlsQueue
    # if (
    #     total_subreddits_item_deserialized["count"]
    #     == todays_subreddit_item_deserialized["count"]
    # ):
    #     logger.info(
    #         f"The lambda handling {subreddit} subredddit is the last one to gather urls"
    #     )
    #     push_subreddit_groups_to_queue(logger)

    #     # and then send custom response to show today's urls
    #     # of all subreddits have been processed.
    #     return {
    #         "success": f"All subreddits have been processed and uploaded urls for date {gather_urls.date}.\nPushed subreddit_groups to: {PROCESS_URLS_FOR_SUBREDDIT_GROUP_QUEUE_URL}"
    #     }


# def push_subreddit_groups_to_queue(subreddit, logger):
#     logger.info(
#         f"Ready to push to push from lambda-{subreddit}-subreddit to {PROCESS_URLS_FOR_SUBREDDIT_GROUP_QUEUE_URL}"
#     )
#     for group in subreddit_groups:
#         logger.info(f"Pushing group: {pp.pformat(group)}")
#         res = sqs.send_message(
#             QueueUrl=PROCESS_URLS_FOR_SUBREDDIT_GROUP_QUEUE_URL, MessageBody=group
#         )


# while gather_urls.total_duration < 601:
#     posts = reddit_account.fetch_posts_as_json(
#         REDDIT_API_URL_TOP, params={"limit": "100"}
#     )

#     gather_urls.parse_posts(posts)

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

# gather_urls.urls = gather_urls.urls + df_top["url"].tolist()
# gather_urls.total_duration = total_duration

# Has to be done at the end when you know you have more than 600 seconds of content.
