"""包装 Valve 的 A2S API"""
import logging
from time import time

import fancy_source_query.fmt as fmt

from ..exceptions import QueryTimeout, ServerRestarting
from .infos import PlayerInfo, ServerInfo, players_info, server_info


class QueryPool:
    """缓存查询结果

    (host, port) => (timestamp, value)

    提供以下方法：

    + `server_info` : 查询服务器信息，会读取缓存
    + `new_server_info` : 查询服务器信息，重新查询
    + `players_info` : 查询服务器中玩家信息，会读取缓存
    + `new_players_info` : 查询服务器中玩家信息，重新查询
    + `config` : 修改实例配置
    """

    __expire: float = 20.0
    # 只缓存一个
    __server_cache: dict[tuple[str, int], tuple[float, ServerInfo]]
    __players_cache: dict[tuple[str, int], tuple[float, list[PlayerInfo]]]

    def __init__(self) -> None:
        self.__server_cache = dict()
        self.__players_cache = dict()

    def config(self, expire: float | None = None):
        """修改缓存过期时间，例如 `.config(expire=60.0)`"""
        if expire:
            logging.debug(f"reset expire to {expire!r}")
            self.__expire = expire

    async def server_info(self, host: str, port: int) -> tuple[float, ServerInfo]:
        """查询对应服务器的信息，如果当前时间在缓存的有效期内，
        则读取缓存，否则重新查询。

        + 读取缓存：返回 (缓存时间, 缓存信息)
        + 重新查询：返回 (查询时间, 查询信息)
        """
        cache = self.__server_cache.get((host, port), None)
        if cache is None:
            # 无缓存内容
            querytime, sinfo = await self.new_server_info(host, port)
            return (querytime, sinfo)

        cache_time, cached = cache
        now = time()
        if now - cache_time > self.__expire:
            # 超时，重查
            querytime, sinfo = await self.new_server_info(host, port)
            return (querytime, sinfo)
        logging.debug(f"read cache({fmt.fmt_time(cache_time)}) {cached!r}")
        return (cache_time, cached)

    async def new_server_info(self, host: str, port: int) -> tuple[float, ServerInfo]:
        """重新查询服务器信息，将查询结果计入缓存。
        如果超时，则返回超时信息，但不计入缓存。
        """
        querytime = time()
        try:
            sinfo = await server_info(host, port)
        except QueryTimeout:
            return querytime, ServerInfo(
                name="超时",
                players=0,
                max_players=0,
                map="unknown",
                vac=False,
                ping=0.0,
            )
        except ServerRestarting:
            return querytime, ServerInfo(
                name="换图或重启",
                players=0,
                max_players=0,
                map="unknown",
                vac=False,
                ping=0.0,
            )
        logging.debug(f"new server query({fmt.fmt_time(querytime)}) {sinfo!r}")
        self.__server_cache[(host, port)] = (querytime, sinfo)
        return (querytime, sinfo)

    async def players_info(
        self, host: str, port: int
    ) -> tuple[float, list[PlayerInfo]]:
        """查询对应服务器的玩家信息列表，如果当前时间在缓存的有效期内，
        则读取缓存，否则重新查询。

        + 读取缓存：返回 (缓存时间, 缓存信息)
        + 重新查询：返回 (查询时间, 查询信息)
        """
        cache = self.__players_cache.get((host, port), None)
        if cache is None:
            # 无缓存内容
            querytime, pinfo = await self.new_players_info(host, port)
            return (querytime, pinfo)

        cache_time, cached = cache
        now = time()
        if now - cache_time > self.__expire:
            # 超时，重查
            querytime, pinfo = await self.new_players_info(host, port)
            return (querytime, pinfo)
        logging.debug(f"read cache({fmt.fmt_time(cache_time)}) {cached!r}")
        return (cache_time, cached)

    async def new_players_info(
        self, host: str, port: int
    ) -> tuple[float, list[PlayerInfo]]:
        """重新查询服务器信息，将查询结果计入缓存。
        如果超时，则返回超时信息，但不计入缓存。
        """
        querytime = time()
        try:
            pinfo = await players_info(host, port)
        except QueryTimeout:
            return querytime, []
        except ServerRestarting:
            return querytime, []

        logging.debug(f"new players query({fmt.fmt_time(querytime)}) {pinfo!r}")
        self.__players_cache[(host, port)] = (querytime, pinfo)
        return (querytime, pinfo)
