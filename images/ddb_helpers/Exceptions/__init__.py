class DDBException(Exception):
    def __init__(self, message, logs=None, stacktrace=None):
        self.message = message
        self.logs = logs
        self.stacktrace = stacktrace


class RequestedItemNotFoundException(DDBException):
    pass


class InvalidCredentialsProvidedException(Exception):
    pass
