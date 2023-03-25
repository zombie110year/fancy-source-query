class FancySourceQueryError(Exception):
    pass


class CannotLoadConfig(FancySourceQueryError):
    pass


class QueryTimeout(TimeoutError):
    pass
