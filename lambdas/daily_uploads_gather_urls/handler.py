import sys, os

sys.path.append(os.path.join(os.path.dirname(__file__)))

from lib import db


def run(event, context):
    response = {"hello": "world", "value": db.double_number(10)}
    return response
