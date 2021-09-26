import boto3, os, logging, time


from entities.RedditAccount import RedditAccount


subreddit = "whatcouldgoright"
REDDIT_AUTH_URL = os.getenv("REDDIT_AUTH_URL")
REDDIT_ACCOUNTS_TABLE_NAME = os.getenv("REDDIT_ACCOUNTS_TABLE_NAME")
REDDIT_API_URL_NEW = os.getenv("REDDIT_API_URL_NEW")
REDDIT_API_URL_NEW = REDDIT_API_URL_NEW.replace("placeholder_value", subreddit)

ddb = boto3.client("dynamodb")


# reddit_account = RedditAccount(subreddit=subreddit, ddb=ddb, logger=logging.getLogger())
# reddit_account.fetch_and_update_account_details(REDDIT_ACCOUNTS_TABLE_NAME)
# reddit_account.authenticate_with_api()
# reddit_account.fetch_and_update_access_token(REDDIT_AUTH_URL)

# after = None
# posts = reddit_account.fetch_posts_as_json(
#     REDDIT_API_URL_NEW, params={"limit": "100", "after": after}
# )

results = []
last_evaluated_key = None

while True:
    if last_evaluated_key:
        response = ddb.scan(
            TableName=REDDIT_ACCOUNTS_TABLE_NAME, ExclusiveStartKey=last_evaluated_key
        )
    else:
        response = ddb.scan(TableName=REDDIT_ACCOUNTS_TABLE_NAME)

    last_evaluated_key = response.get("LastEvaluatedKey")

    results.extend(response["Items"])

    if not last_evaluated_key:
        break

problems = []
for result in results:
    sub = result["PK"]["S"]

    reddit_account = RedditAccount(
        subreddit=subreddit, ddb=ddb, logger=logging.getLogger()
    )
    reddit_account.fetch_and_update_account_details(REDDIT_ACCOUNTS_TABLE_NAME)
    reddit_account.authenticate_with_api()
    reddit_account.fetch_and_update_access_token(REDDIT_AUTH_URL)

    after = None
    posts = reddit_account.fetch_posts_as_json(
        REDDIT_API_URL_NEW, params={"limit": "100", "after": after}
    )
    print(f"Checking sub {sub}")
    time.sleep(1)
    try:
        print(posts["data"]["children"][0])
        # break
    except Exception as e:
        problems.append(sub)


print("problems ", problems)
