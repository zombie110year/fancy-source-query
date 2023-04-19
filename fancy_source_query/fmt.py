import logging
from time import localtime, strftime

from .config import FmtConfig
from .guess_map import Mapname, guess_map
from .querypool.infos import PlayerInfo, RuleInfo, ServerInfo, ServerPair, ServerTriple


def fmt_time(t: float) -> str:
    return strftime("%Y-%m-%d %H:%M:%S", localtime(t))


class InfoFormatter:
    __fmt: FmtConfig
    __rlookup: dict[str, Mapname]

    def __init__(self) -> None:
        self.__fmt = FmtConfig()

    def config(
        self, fmt: FmtConfig | None = None, rlookup: dict[str, Mapname] | None = None
    ):
        if fmt:
            logging.debug("updated InfoFormatter's config.")
            self.__fmt = fmt
        if rlookup:
            logging.debug("updated InfoFormatter's map rlookup.")
            self.__rlookup = rlookup

    def format(
        self, info: ServerInfo | PlayerInfo | RuleInfo | ServerPair | ServerTriple
    ) -> str:
        "通用的格式化方法，会判断传入类型并具体分配实际方法"
        if isinstance(info, ServerInfo):
            return self.fmt_server_info(info)
        elif isinstance(info, ServerPair):
            return self.fmt_server_pair(info)
        elif isinstance(info, PlayerInfo):
            return self.fmt_player_info(info)
        elif isinstance(info, RuleInfo):
            return self.fmt_rule_info(info)
        elif isinstance(info, ServerTriple):
            return self.fmt_server_triple(info)

    def fmt_server_info(self, info: ServerInfo) -> str:
        name, code = self.guess_map(info.map)
        if name:
            mapname = f"{name}|{code}"
        else:
            mapname = code
        fmt = self.__fmt.server_info.format(
            name=info.name,
            players=info.players,
            max_players=info.max_players,
            mapname=mapname,
        )
        return fmt

    def fmt_player_info(self, info: PlayerInfo) -> str:
        fmt = self.__fmt.player_info.format(
            name=info.name,
            minutes=info.duration / 60,
            score=info.score,
        )
        return fmt

    def fmt_rule_info(self, info: RuleInfo) -> str:
        fmt = self.__fmt.rule_info.format(
            key=info.name,
            value=info.value,
        )
        return fmt

    def fmt_server_pair(self, info: ServerPair) -> str:
        sfmt = self.fmt_server_info(info.server)
        sorted_p = sorted(info.players, key=lambda x: x.score, reverse=True)
        pfmt = [self.fmt_player_info(p) for p in sorted_p]
        return "{}\n{}".format(sfmt, "\n".join(pfmt))

    def fmt_server_triple(self, info: ServerTriple) -> str:
        sfmt = self.fmt_server_info(info.server)
        sorted_p = sorted(info.players, key=lambda x: x.score, reverse=True)
        pfmt = [self.fmt_player_info(p) for p in sorted_p]
        sorted_r = sorted(info.rules, key=lambda x: x.name)
        rfmt = [self.fmt_rule_info(r) for r in sorted_r]
        return "{}\n{}\n{}".format(sfmt, "\n".join(pfmt), "\n".join(rfmt))

    def guess_map(self, code: str) -> str:
        "返回 name, code 元组"
        name = guess_map(self.__rlookup, code)
        if name:
            return name, code
        else:
            logging.warning(f"未知的地图代码：{code}")
            return None, code

    def fmt_players_count(self, p: int) -> str:
        "格式化总人数统计"
        return self.__fmt.players_count.format(players=p)

    def fmt_time(self, t: float) -> str:
        return strftime(self.__fmt.time, localtime(t))

    def fmt_query_time(self, t: float) -> str:
        "和 fmt_time 的区别在于，这个函数生成显示样式的时间"
        ttime = self.fmt_time(t)
        return self.__fmt.query_time.format(time=ttime)
