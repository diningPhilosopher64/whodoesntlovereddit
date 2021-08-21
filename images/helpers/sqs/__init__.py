import os, sys, traceback, json, pprint
from typing import final

from helpers import Exceptions

pp = pprint.PrettyPrinter(indent=2, compact=True, width=80)


# Making the current directory in which this file is in discoverable to python
# sys.path.append(os.path.join(os.path.dirname(__file__)))


def send_message(sqs, logger, **kwargs):
    """Pass SQS client, logger and Queue details.
    QueueUrl, MessageBody in a dict are compulsory kwargs.

    Args:
        sqs (boto3.client): SQS client object
        logger (logger): For logging purposes.
        **kwargs(dict): Dict containing details of about the message.
    """

    return_value = {
        "status_code": 500,
        "error": "Failed to push message. Check logs",
    }
    try:
        resp = sqs.send_message(**kwargs)

        logger.info(
            f"Successfully pushed message: {kwargs['MessageBody']} to {kwargs['QueueUrl']}."
        )

        return_value = resp

    except sqs.exceptions.QueueDoesNotExist:
        logger.error(
            f"Queue doesn't exist. Details:\nQueueUrl: {kwargs['QueueUrl']}\nMessageBody: {kwargs['MessageBody']}\n"
        )
        logger.info(pp.pformat(kwargs))

    except Exception:
        Exceptions.log_generic_exception(logger)

    finally:
        return return_value
