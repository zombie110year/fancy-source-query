from time import localtime, strftime


def fmt_time(t: float) -> str:
    return strftime("%Y-%m-%d %H:%M:%S", localtime(t))
