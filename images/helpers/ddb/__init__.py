import os, sys, traceback, json, pprint
import re

pp = pprint.PrettyPrinter(indent=2, compact=True, width=80)


# Making the current directory in which this file is in discoverable to python
sys.path.append(os.path.join(os.path.dirname(__file__)))


from helpers.Exceptions import RequestedItemNotFoundException
from helpers import Exceptions


def get_item(ddb, logger, **kwargs) -> dict:
    """Pass dynamoDb Client, logger and ddb details.
    TableName, Key in a dict are compulsory kwargs.

    Args:
        ddb (boto3.client): dynamodb client object
        logger (logger): For logging purposes
        **kwargs(dict): Dict containing details about item to get.

    Raises:
        RequestedItemNotFoundException: Is raised if requested item is not found.

    Returns:
        dict: response containing the item from ddb.
    """
    return_value = {"status_code": 500, "error": "Failed to get item. Check logs"}
    try:
        resp = ddb.get_item(**kwargs)

        if "Item" not in resp:
            raise RequestedItemNotFoundException(
                f"Item: {kwargs['Key']} not found in the table: {kwargs['TableName']}"
            )
        return_value = resp["Item"]
        logger.info("Received the following item from db:\n")
        logger.info(pp.pformat(return_value))

    except RequestedItemNotFoundException as err:
        logger.error("Requested Item not found. Failed with error:\n")
        logger.error(pp.pformat(err))
        logger.error("Key word arguments passed are:\n")
        logger.error(pp.pformat(kwargs))

    except Exception as err:
        Exceptions.log_generic_exception(logger)

    finally:
        return return_value


def transact_write_items(ddb, logger, **kwargs):
    """Pass dynamoDb Client, logger and ddb details.
    TransactItems in a dict are compulsory kwargs.

    Args:
        ddb (boto3.client): dynamodb client object
        logger (logger): For logging purposes
        **kwargs(dict): Dict containing details about TransactItems.

    Raises:
        TransactionCanceledException: Is raised if transaction is canceled.

    Returns:
        dict: response containing the response after transaction is done.
    """
    return_value = {
        "status_code": 500,
        "error": "Failed to write transaction. Check logs",
    }
    try:
        resp = ddb.transact_write_items(**kwargs)
        return_value = resp
        logger.info("Received the following item from db:\n")
        logger.info(pp.pformat(return_value))

    except ddb.exceptions.TransactionCanceledException as err:
        logger.error(f"TransactionCanceledException raised. Details:\nTransactItems:\n")
        logger.error(pp.pformat(kwargs))

    except Exception:
        Exceptions.log_generic_exception(logger)

    finally:
        return return_value


def get_datatype(variable):
    data_type = type(variable)
    if data_type == str:
        return "S"
    elif data_type == int or data_type == float:
        return "N"


def deserialize_piece_of_item(key, value):
    if key == "S":
        return value

    if key == "N":
        try:
            int_value = int(value)
            return int_value

        except ValueError:
            return float(value)

    if key == "M":
        deserialized_item = {}
        for _key, _value in value.items():
            for __key, __value in _value.items():
                deserialized_item[_key] = deserialize_piece_of_item(__key, __value)

        return deserialized_item

    if key == "L":
        deserialized_items = []
        for single_item in value:
            for _key, _value in single_item.items():
                deserialized_items.append(deserialize_piece_of_item(_key, _value))

        return deserialized_items
