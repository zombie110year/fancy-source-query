import logging
from os import getenv
from pathlib import Path

import toml
from nonebot import get_driver
from pydantic import BaseModel, Extra

NONEBOT_CONFIG_KEY = "fancy_source_query_config"
CONFIG_PATH_PREFIX = "fancy_source_query"
MAPNAMES_PATH_PREFIX = "mapnames"
DEFAULT_CONFIG_PATH = "fancy_source_query.toml"
DEFAULT_MAPNAMES_PATH = "mapnames.toml"


class ServerConfig(BaseModel, extra=Extra.ignore):
    "服务器名称、地址"
    group: str
    name: str
    host: str
    port: int


class ServerGroupConfig(BaseModel, extra=Extra.ignore):
    "服务器组"
    name: str
    related_sessions: list[str]


class FmtConfig(BaseModel, extra=Extra.ignore):
    "设置格式化模板"
    server_info: str = "{name}\n==({players:>2d}/{max_players:>2d})[{mapname}]"
    player_info: str = ">>[{score}]({minutes:.1f}min){name}"
    rule_info: str = "({key} = {value})"
    # strftime 格式符
    time: str = "%Y-%m-%d %H:%M:%S"


class FancySourceQueryConfig(BaseModel, extra=Extra.ignore):
    """插件的主要配置"""

    # 默认超时等待 5s
    timeout: int = 5
    # 默认查询池缓存 20s
    cache_delay: int = 20
    # 默认限制文本输出 5 行，超过 5 行的转成图片输出
    output_max_lines: int = 5
    # Fancy Source Query 可以配置地图数据库，方便将地图代码转换成人类可读的地图名
    # 该路径相对于 nonebot 进程工作目录
    mapnames_db: str = DEFAULT_MAPNAMES_PATH

    fmt: FmtConfig
    server_groups: list[ServerGroupConfig]
    servers: list[ServerConfig]


class NonebotConfig(BaseModel, extra=Extra.ignore):
    "nonebot env 配置"
    fancy_source_query_config: str = DEFAULT_CONFIG_PATH


def load_config(config_path: str | None = None):
    """加载配置
    1. 首先尝试从 nonebot 全局配置中加载
    2. 如果上一条失败，则尝试从环境变量中加载
    3. 如果上一条失败，则尝试从工作目录的 `fancy_source_query.toml` 中加载
    4. 如果上一条失败，抛出 CannotLoadConfig 异常
    """
    if config_path:
        config_path = Path(config_path).absolute().as_posix()
        logging.info(f"read config_path from argument {config_path!r}")

    if config_path is None:
        try:
            config_path = getattr(get_driver().config, NONEBOT_CONFIG_KEY, None)
        except Exception:
            config_path = None
        if config_path:
            config_path = Path(config_path).absolute().as_posix()
            logging.info(f"read config_path from nonebot env config {config_path!r}")

    if config_path is None:
        config_path = getenv(NONEBOT_CONFIG_KEY.upper(), None)
        if config_path:
            config_path = Path(config_path).absolute().as_posix()
            logging.info(f"read config_path from os env {config_path!r}")

    if config_path is None:
        config_path = DEFAULT_CONFIG_PATH
        if config_path:
            config_path = Path(config_path).absolute().as_posix()
            logging.info(f"read config_path from default {config_path!r}")

    config = toml.load(config_path)
    config = FancySourceQueryConfig.parse_obj(config[CONFIG_PATH_PREFIX])
    return config


class Mapname(BaseModel, extra=Extra.ignore):
    name: str
    name_zh: str | None = None
    maps: list[str]
