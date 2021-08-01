import json, boto3

# Added the below 2 lines to let python discover files other than the handler
# ie. enabled relative imports with the below 2 lines.
# import sys, os
# sys.path.append(os.path.join(os.path.dirname(__file__)))
  

def pick_and_preprocess(event, context):

    print("event is \n ", event)

    response = {
        "event":json.dumps(event)
    }

    return response


