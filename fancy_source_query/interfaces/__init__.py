"""Fancy Source Query 的对外接口

其它接口：

+ nonebot: Nonebot 接口
+ cli: 命令行接口

此接口导出一个 FancySourceQuery 对象，其成员函数提供了对应的功能。
"""
import asyncio
import logging

import toml

from ..config import MAPNAMES_PATH_PREFIX, FancySourceQueryConfig, Mapname, load_config
from ..guess_map import build_rlookup
from ..querypool import QueryPool
from ..fmt import InfoFormatter
from ..querypool.infos import ServerInfo, PlayerInfo, ServerPair
from ..server_group import Server, ServerGroup, build_server_group_graph
from ..exceptions import ObjectNotFound


class FancySourceQuery:
    config: FancySourceQueryConfig
    mapnames: list[Mapname]
    map_rlookup: dict[str, Mapname]
    query_pool: QueryPool
    ifmt: InfoFormatter
    server_group: dict[str, ServerGroup]
    servers: dict[str, Server]

    def __init__(self) -> None:
        self.query_pool = QueryPool()
        self.ifmt = InfoFormatter()
        self.update_config()
        self.update_mapnames()

    def update_config(self, path: str | None = None):
        self.config = load_config(path)
        self.query_pool.config(self.config.cache_delay)
        self.ifmt.config(fmt=self.config.fmt)
        groups, servers = build_server_group_graph(
            self.config.server_groups, self.config.servers
        )
        self.server_group = groups
        self.servers = servers

    def update_mapnames(self):
        mapnames = toml.load(self.config.mapnames_db)
        self.mapnames = [Mapname.parse_obj(x) for x in mapnames[MAPNAMES_PATH_PREFIX]]
        self.map_rlookup = build_rlookup(self.mapnames)
        self.ifmt.config(rlookup=self.map_rlookup)
        logging.debug("mapnames refreshed")

    def find_server(self, sname: str, gname: str) -> Server:
        """在指定的服务器组中寻找服务器"""
        group = self.server_group.get(gname, None)
        if group is None:
            logging.error(f"server group {gname!r} not found.")
            raise ObjectNotFound("server group not found", gname)
        server = group.servers.get(sname, None)
        if server is None:
            logging.error(f"server {sname!r} in group {gname!r} not found.")
            raise ObjectNotFound("server in group not found", gname, sname)
        return server

    async def query_server(self, sname: str, gname: str) -> str:
        """只查询服务器信息，返回格式化文本"""
        server = self.find_server(sname, gname)
        host, port = server.host, server.port
        qtime, sinfo = await self.query_pool.server_info(host, port)
        fmtsinfo = self.ifmt.fmt_server_info(sinfo)
        qtime = self.ifmt.fmt_time(qtime)
        return f"{fmtsinfo}\n\n----{qtime}"

    async def query_server_and_players(self, sname: str, gname: str) -> str:
        """查询某服务器的信息和玩家信息，返回格式化文本"""
        server = self.find_server(sname, gname)
        host, port = server.host, server.port
        qtime1, sinfo = await self.query_pool.server_info(host, port)
        qtime2, pinfo = await self.query_pool.players_info(host, port)
        spair = ServerPair(server=sinfo, players=pinfo)
        qtime = self.ifmt.fmt_time(max(qtime1, qtime2))
        fmted = self.ifmt.fmt_server_pair(spair)
        return f"{fmted}\n\n----{qtime}"

    async def query_server_and_players_multi(
        self, snames: list[str], gname: str
    ) -> str:
        """查询多个服务器的信息和玩家信息，返回格式化文本"""
        servers = []
        for sname in snames:
            try:
                servers.append(self.find_server(sname, gname))
            except ObjectNotFound:
                logging.warning("object not found, but skiped.")
                continue
        # servers = [self.find_server(sname, gname) for sname in snames]
        sinfos = await asyncio.gather(
            *(self.query_pool.server_info(s.host, s.port) for s in servers)
        )
        pinfos = await asyncio.gather(
            *(self.query_pool.players_info(s.host, s.port) for s in servers)
        )
        qtime = self.ifmt.fmt_time(max([r[0] for r in sinfos] + [r[0] for r in pinfos]))
        pairs = sorted(
            [ServerPair(server=r[0][1], players=r[1][1]) for r in zip(sinfos, pinfos)],
            key=lambda pair: pair.server.name,
        )
        fmted = "\n".join(self.ifmt.fmt_server_pair(p) for p in pairs)
        return f"{fmted}\n\n----{qtime}"

    async def query_servers_overview(self, gname: str) -> str:
        """查询某服务器组内的服务器信息，返回格式化文本

        + `sgroup` 服务器组名
        """
        group = self.server_group.get(gname, None)
        if group is None:
            raise ObjectNotFound("server group not found", gname)
        servers = sorted(group.servers.values(), key=lambda s: s.name)
        results = await asyncio.gather(
            *[self.query_pool.server_info(s.host, s.port) for s in servers]
        )
        qtime = self.ifmt.fmt_time(max(r[0] for r in results))
        sinfos = [r[1] for r in results]
        fmted = "\n".join(self.ifmt.fmt_server_info(sinfo) for sinfo in sinfos)
        players = sum(s.players for s in sinfos)
        return f"{fmted}\n\n\n总人数：{players}\n----{qtime}"
