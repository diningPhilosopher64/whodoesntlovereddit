import os, sys, traceback, json, pprint

pp = pprint.PrettyPrinter(indent=2, compact=True, width=80)


# Making the current directory in which this file is in discoverable to python
sys.path.append(os.path.join(os.path.dirname(__file__)))

from Exceptions import RequestedItemNotFoundException


def get_item(ddb, TableName, Key, logger):
    try:
        resp = ddb.get_item(TableName=TableName, Key=Key)

        if "Item" not in resp:
            raise RequestedItemNotFoundException(
                f"Item: {Key} not found in the table: {TableName}"
            )

        return resp["Item"]
    except RequestedItemNotFoundException as err:
        logger.error("Requested Item not found. Failed with error:\n")
        logger.error(pp.pformat(err))

    except Exception as err:
        __log_generic_exception(logger)


def transact_write_items(ddb, TransactItems, logger):
    try:
        resp = ddb.transact_write_items(TransactItems=TransactItems)
        return resp
    except ddb.exceptions.TransactionCanceledException as err:
        logger.error(f"TransactionCanceledException raised. Details:\nTransactItems:\n")
        logger.error(pp.pformat(TransactItems))
        raise err

    except Exception:
        __log_generic_exception(logger)


def __log_generic_exception(logger):
    exception_type, exception_value, exception_traceback = sys.exc_info()
    traceback_string = traceback.format_exception(
        exception_type, exception_value, exception_traceback
    )
    err_msg = json.dumps(
        {
            "errorType": exception_type.__name__,
            "errorMessage": str(exception_value),
            "stackTrace": traceback_string,
        }
    )
    logger.error(pp.pformat(err_msg))


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
