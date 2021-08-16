import traceback, json, pprint

pp = pprint.PrettyPrinter(indent=2, compact=True, width=80)


class DDBException(Exception):
    def __init__(self, message, logs=None, stacktrace=None):
        self.message = message
        self.logs = logs
        self.stacktrace = stacktrace


class RequestedItemNotFoundException(DDBException):
    pass


class InvalidCredentialsProvidedException(Exception):
    pass


def log_generic_exception(logger):
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
