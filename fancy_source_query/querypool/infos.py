import logging
import socket
from typing import Any
from pydantic import BaseModel

from steam.game_servers import a2s_info, a2s_players, a2s_rules

from ..exceptions import QueryTimeout


class PlayerInfo(BaseModel):
    name: str
    score: int
    duration: float
    index: int


class ServerInfo(BaseModel):
    name: str
    players: int
    max_players: int
    map: str
    vac: bool
    ping: float


class RuleInfo(BaseModel):
    name: str
    value: Any


class ServerPair(BaseModel):
    "包含了服务器信息和玩家信息"
    server: ServerInfo
    players: list[PlayerInfo]


class ServerTriple(BaseModel):
    "包含了服务器信息、玩家信息和规则信息"
    server: ServerInfo
    players: list[PlayerInfo]
    rules: list[RuleInfo]


class Overview(BaseModel):
    players: int = 0
    servers: list[ServerInfo] = list()


async def server_info(host: str, port: int) -> ServerInfo:
    """查询服务器信息，只保留了部分感兴趣的信息：

    + name: 服务器名称
    + players: 玩家人数
    + max_players: 人数上限
    + map: 地图代码
    + vac: 是否开启 VAC
    + ping: 本机与服务器的延迟
    """
    try:
        info = a2s_info(server_addr=(host, port))
    except socket.timeout:
        raise QueryTimeout({"host": host, "port": port})

    info_ = {
        "name": info["name"],
        "players": info["players"],
        "max_players": info["max_players"],
        "map": info["map"],
        "vac": True if info["vac"] == 1 else False,
        "ping": info["_ping"],
    }
    if info_["name"].startswith("\ufeff"):
        info_["name"] = info_["name"].strip("\ufeff")

    info_obj = ServerInfo(**info_)

    logging.debug(f"new server info query to {host}:{port}")
    return info_obj


async def players_info(host: str, port: int) -> list[PlayerInfo]:
    """查询服务器中的玩家信息

    + duration: 游玩时间（秒）
    + index: 玩家所在区块索引
    + score: 分数
    + name: 名称
    """
    try:
        info = a2s_players(server_addr=(host, port))
    except socket.timeout:
        raise QueryTimeout({"host": host, "port": port})

    logging.debug(f"new players info query to {host}:{port}")
    return sorted([PlayerInfo(**i) for i in info], key=lambda o: -o.score)


async def rules_info(host: str, port: int) -> list[RuleInfo]:
    """查询服务器的规则

    + name: 规则名称
    + value: 值
    """
    try:
        info = a2s_rules(server_addr=(host, port))
    except socket.timeout:
        raise QueryTimeout({"host": host, "port": port})
    return [RuleInfo(**i) for i in info]
