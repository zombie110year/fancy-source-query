"""Fancy Source Query 的对外接口

其它接口：

+ nonebot: Nonebot 接口
+ cli: 命令行接口

此接口导出一个 FancySourceQuery 对象，其成员函数提供了对应的功能。
"""
from .config import FancySourceQueryConfig, load_config


class FancySourceQuery:
    config: FancySourceQueryConfig

    def __init__(self) -> None:
        self.config = load_config()
