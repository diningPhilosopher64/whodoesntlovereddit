import json, boto3

# Added the below 2 lines to let python discover files other than the handler
# ie. enabled relative imports with the below 2 lines.
# import sys, os
# sys.path.append(os.path.join(os.path.dirname(__file__)))
  

def run(event, context):

    
    response = {
      "hello": "world"
    }


    return response


