import json, boto3, asyncio, concurrent.futures
from timeit import default_timer as timer

# Added the below 2 lines to let python discover files other than the handler
# ie. enabled relative imports with the below 2 lines.
import sys, os
sys.path.append(os.path.join(os.path.dirname(__file__)))

from subredditList import subreddits as all_subreddits

sqs = boto3.client('sqs')
queue_url = os.getenv("INITIAL_SUBREDDIT_QUEUE_URL")

def push_subreddits_to_queue():
    for idx, subreddit in enumerate(all_subreddits):
        sqs.send_message(QueueUrl=queue_url, MessageBody=subreddit + str(idx))
  

def check(event, context):
    start = timer()
    push_subreddits_to_queue()
    end = timer()
    response = {
        "statusCode": 200, 
        "time_taken": end - start
    }

    return response


