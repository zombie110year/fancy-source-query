"""Fancy Source Query 的对外接口

其它接口：

+ nonebot: Nonebot 接口
+ cli: 命令行接口

此接口导出一个 FancySourceQuery 对象，其成员函数提供了对应的功能。
"""
import asyncio
import logging
import re
import socket
from typing import Literal

import toml
from pydantic import BaseModel

from impaper.draw import TextDrawer

from ..config import MAPNAMES_PATH_PREFIX, FancySourceQueryConfig, Mapname, load_config
from ..exceptions import ObjectNotFound
from ..fmt import InfoFormatter
from ..guess_map import build_rlookup
from ..querypool import QueryPool
from ..querypool.infos import PlayerInfo, ServerInfo, ServerPair
from ..server_group import Server, ServerGroup, build_server_group_graph

WHITESPACE = re.compile("[ \u2002\u2003]")


class QueryResult(BaseModel):
    """查询结果

    + tag : 查询类型，一共有一下几种：
        + o : overview
        + s : only server
        + sp : server and players
        + spm : server and players multi
        + p : search player
    """
    tag: Literal["o", "s", "sp", "spm", "p"]
    # query time
    qtime: float
    result: None | list[ServerPair] | list[ServerInfo] | ServerPair | ServerInfo


class FancySourceQuery:
    """面向 Python 的 Fancy Source Query 接口，各方法返回 对象 而非文本。
    格式化为文本是 cli 或 nonebot 接口的工作。

    + `update_config` : 刷新配置项（本体配置、服务器组配置）
    + `update_mapnames` : 刷新地图名反查表
    + `find_server` : 在指定的服务器组中根据名称寻找服务器
    + `find_group` : 根据名称寻找指定的服务器组
    + `query_server`(async): 查询服务器信息，返回查询时间 和 Server Info
    """

    config: FancySourceQueryConfig
    mapnames: list[Mapname]
    map_rlookup: dict[str, Mapname]
    query_pool: QueryPool
    ifmt: InfoFormatter
    server_group: dict[str, ServerGroup]
    servers: dict[str, Server]
    # session_id => server_group name
    session_group: dict[str, str]
    qstr_pat_overview: re.Pattern
    qstr_pat_server_name: re.Pattern
    # text to graphic 引擎，按需加载
    t2g: TextDrawer | None

    def __init__(self) -> None:
        self.query_pool = QueryPool()
        self.ifmt = InfoFormatter()
        self.t2g = None
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
        self.session_group = {
            s: g.name for g in self.config.server_groups for s in g.related_sessions
        }
        self.qstr_pat_overview = re.compile(r"^(?:人数)?$")
        all_server_names = "|".join(self.servers.keys())
        self.qstr_pat_server_name = re.compile(f"^(?:{all_server_names})$")
        socket.setdefaulttimeout(self.config.timeout)
        if self.t2g is not None:
            self.t2g.conf = self.config.impaper
            self.t2g.fontsize = self.config.fontsize

    def update_mapnames(self):
        mapnames = toml.load(self.config.mapnames_db)
        self.mapnames = [Mapname.parse_obj(x) for x in mapnames[MAPNAMES_PATH_PREFIX]]
        self.map_rlookup = build_rlookup(self.mapnames)
        self.ifmt.config(rlookup=self.map_rlookup)
        logging.debug("mapnames refreshed")

    def find_server(self, sname: str, gname: str | None) -> Server:
        """在指定的服务器组中寻找服务器"""
        group = self.find_group(gname)
        server = group.servers.get(sname, None)
        if server is None:
            logging.error(f"server {sname!r} in group {gname!r} not found.")
            raise ObjectNotFound("server in group not found", gname, sname)
        return server

    def find_group(self, gname: str | None) -> ServerGroup:
        """根据组名寻找服务器组"""
        if gname is None:
            gname = self.config.default_server_group
            logging.info(f"use default server group {gname!r}.")
        group = self.server_group.get(gname, None)
        if group is None:
            logging.error(f"server group {gname!r} not found.")
            raise ObjectNotFound("server group not found", gname)
        return group

    async def query_server(
        self, sname: str, gname: str | None
    ) -> QueryResult:
        """根据服务器组和服务器的名称查询服务器信息，返回查询时间 和 Server Info"""
        server = self.find_server(sname, gname)
        host, port = server.host, server.port
        qtime, sinfo = await self.query_pool.server_info(host, port)
        r = QueryResult(tag="s", qtime=qtime, result=sinfo)
        return r

    async def query_server_and_players(
        self, sname: str, gname: str | None
    ) -> QueryResult:
        """根据服务器组和服务器的名称查询服务器信息和玩家信息，
        返回查询时间 和 ServerPair"""
        server = self.find_server(sname, gname)
        host, port = server.host, server.port
        qtime1, sinfo = await self.query_pool.server_info(host, port)
        qtime2, pinfo = await self.query_pool.players_info(host, port)
        spair = ServerPair(server=sinfo, players=pinfo)
        qtime = max(qtime1, qtime2)
        r = QueryResult(tag="sp", qtime=qtime, result=spair)
        return r

    async def query_server_and_players_multi(
        self, snames: list[str], gname: str | None
    ) -> QueryResult:
        """查询多个服务器的信息和玩家信息，返回最晚查询时间和 list[ServerPair]"""
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
        qtime = max([r[0] for r in sinfos] + [r[0] for r in pinfos])
        pairs = sorted(
            [ServerPair(server=r[0][1], players=r[1][1]) for r in zip(sinfos, pinfos)],
            key=lambda pair: pair.server.name,
        )
        r = QueryResult(tag="spm", qtime=qtime, result=pairs)
        return r

    async def query_servers_overview(
        self, gname: str | None
    ) -> QueryResult:
        """查询某服务器组内的服务器信息，返回最晚查询时间和 `list[ServerInfo]`

        + `sgroup` 服务器组名
        """
        group = self.find_group(gname)
        servers = sorted(group.servers.values(), key=lambda s: s.name)
        results = await asyncio.gather(
            *[self.query_pool.server_info(s.host, s.port) for s in servers]
        )
        qtime = max(r[0] for r in results)
        sinfos = [r[1] for r in results]
        r = QueryResult(tag="o", qtime=qtime, result=sinfos)
        return r

    async def search_player(
        self, player_regex: str, gname: str | None
    ) -> QueryResult:
        """在某个组中查找某些玩家，只要玩家名中含有 `player` 的片段，
        便会认为是查找目标。
        返回最晚查询时间和相关的服务器与玩家信息。
        如果未找到则返回无意义的时间戳和None。
        """
        group = self.find_group(gname)
        servers = sorted(group.servers.values(), key=lambda s: s.name)
        stasks = await asyncio.gather(
            *[self.query_pool.server_info(s.host, s.port) for s in servers]
        )
        ptasks = await asyncio.gather(
            *[self.query_pool.players_info(s.host, s.port) for s in servers]
        )
        total = [
            (max(qt1, qt2), sinfo, pinfo)
            for (qt1, sinfo), (qt2, pinfo) in zip(stasks, ptasks)
        ]
        total: list[tuple[float, ServerInfo, list[PlayerInfo]]]
        pat = re.compile(player_regex, re.IGNORECASE)
        # index of total => player info
        occursins: dict[int, list[PlayerInfo]] = {}
        qtime = 0.0
        for i, (qt, si, pi) in enumerate(total):
            for p in pi:
                # 忽略空白字符
                if pat.search(WHITESPACE.sub("", p.name)):
                    qtime = max(qtime, qt)
                    if i not in occursins:
                        occursins[i] = [p]
                    else:
                        occursins[i].append(p)
        if len(occursins) == 0:
            return QueryResult(tag="p", qtime=qtime, result=None)
        pairs = sorted(
            (ServerPair(server=total[i][1], players=p) for (i, p) in occursins.items()),
            key=lambda pair: pair.server.name,
        )
        r = QueryResult(tag="p", qtime=qtime, result=pairs)
        return r

    async def query(
        self, gname: str | None, qstr: str
    ) -> QueryResult:
        """根据 qstr 内容进行查询：

        1. qstr 是空字符串或“人数” - 调用 `query_servers_overview`
        2. qstr 是已知的服务器名 - 调用 `query_server_and_players`
        3. qstr 是空格分隔的服务器名 - 调用 `query_server_and_players_multi`
        4. qstr 是其它情况 - 调用 `search_player`
        """
        qstr = qstr.strip()
        if self.qstr_pat_overview.fullmatch(qstr):
            return await self.query_servers_overview(gname)
        if self.qstr_pat_server_name.fullmatch(qstr):
            return await self.query_server_and_players(qstr, gname)
        # 先尝试是不是查询多个服务器
        if " " in qstr:
            # 忽略不认识的
            servers = [
                name
                for name in qstr.split(" ")
                if self.qstr_pat_server_name.fullmatch(name)
            ]
            return await self.query_server_and_players_multi(servers, gname)
        # 尝试搜索玩家
        return await self.search_player(qstr, gname)

    def find_gname_from_session(self, session: str) -> str | None:
        """根据群号查找相关的服务器组，如果找不到则返回 None"""
        return self.session_group.get(session, None)

    def lazy_load_t2g(self, t2g: TextDrawer):
        """需要时再加载"""
        self.t2g = t2g
        self.t2g.conf = self.config.impaper
        self.t2g.fontsize = self.config.fontsize


async def fmt_qresult(fsq: FancySourceQuery, r: QueryResult, qstr: str) -> str:
    if r.tag == "p" and r.result is None:
        if r.result is None:
            return f"【{qstr}】不在哦~😥"

    body = []
    if isinstance(r.result, list):
        body.extend(fsq.ifmt.format(r) for r in r.result)
    else:
        body.append(fsq.ifmt.format(r.result))
    body.append("\n")
    if isinstance(r.result, list):
        players = 0
        for rr in r.result:
            if r.tag == "p":
                players += len(rr.players)
            elif isinstance(rr, ServerPair):
                players += rr.server.players
            elif isinstance(rr, ServerInfo):
                players += rr.players
        tplayers = fsq.ifmt.fmt_players_count(players)
        body.append(tplayers)
    ttime = fsq.ifmt.fmt_query_time(r.qtime)
    body.append(ttime)
    text = "\n".join(body)
    return text
