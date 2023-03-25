"""Fancy Source Query 的对外接口

其它接口：

+ nonebot: Nonebot 接口
+ cli: 命令行接口

此接口导出一个 FancySourceQuery 对象，其成员函数提供了对应的功能。
"""
import logging

import toml

from ..config import MAPNAMES_PATH_PREFIX, FancySourceQueryConfig, Mapname, load_config
from ..guess_map import build_rlookup, guess_map
from ..querypool import QueryPool


class FancySourceQuery:
    config: FancySourceQueryConfig
    mapnames: list[Mapname]
    map_rlookup: dict[str, Mapname]
    query_pool: QueryPool

    def __init__(self) -> None:
        self.query_pool = QueryPool()
        self.update_config()
        self.update_mapnames()

    def update_config(self, path: str | None = None):
        self.config = load_config(path)
        self.query_pool.config(self.config.cache_delay)

    def update_mapnames(self):
        mapnames = toml.load(self.config.mapnames_db)
        self.mapnames = [Mapname.parse_obj(x) for x in mapnames[MAPNAMES_PATH_PREFIX]]
        self.map_rlookup = build_rlookup(self.mapnames)
        logging.debug("mapnames refreshed")

    def guess_map(self, code: str) -> str:
        "除了 guess map 之外还需要完成格式化任务 name|code"
        name = guess_map(self.map_rlookup, code)
        if name:
            return f"{name}|{code}"
        else:
            return code
