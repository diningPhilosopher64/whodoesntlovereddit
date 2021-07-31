import json, boto3

# Added the below 2 lines to let python discover files other than the handler
# ie. enabled relative imports with the below 2 lines.
import sys, os
sys.path.append(os.path.join(os.path.dirname(__file__)))

from subredditList import subreddits as all_subreddits

sns = boto3.client('sns')

"""
Need to handle a case where number of topics is greater than 100
If number of topics is greater than 100 below code will not work
Look for list_topics() method in the docs on how to handle this.
"""

def check(event, context):
    #Get current list of sns topics
    topics = sns.list_topics()['Topics']

    # Get list of currently tracked subreddits
    current_subreddits = []
    for topic in topics:
        current_subreddits.append(extract_topic_name(topic['TopicArn']))

    # if sns topic is not present create it.
    for subreddit in all_subreddits:
        if subreddit not in current_subreddits:
            sns.create_topic(Name=subreddit)


    response = {
        "statusCode": 200,        
    }

    return response



def extract_topic_name(topic_arn):    
    return topic_arn.split(":")[-1]

