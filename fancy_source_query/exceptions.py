class FancySourceQueryError(Exception):
    pass


class CannotLoadConfig(FancySourceQueryError):
    pass


class QueryTimeout(TimeoutError, FancySourceQueryError):
    pass


class ObjectNotFound(FancySourceQueryError):
    pass


class ServerRestarting(ConnectionRefusedError, FancySourceQueryError):
    pass
