"""Fancy Source Query 的 Nonebot 接口，在此处配置 Nonebot 相关响应器

其它接口：

+ interfaces : Python 接口
+ cli : 命令行接口
"""
import logging
import re
from io import BytesIO
from base64 import b64encode

import exrex
from impaper import SimpleTextDrawer
from nonebot import get_driver, on_command
from nonebot.adapters.onebot.v11 import Bot, Event, Message
from nonebot.exception import ActionFailed
from nonebot.params import CommandArg
from nonebot.permission import SUPERUSER
from nonebot.rule import to_me
from PIL.Image import Image

from ..config import NonebotConfig
from . import FancySourceQuery, ServerInfo, ServerPair

_global_config = get_driver().config
_nonebot_config = NonebotConfig.parse_obj(_global_config)
FSQ = FancySourceQuery()
FSQ.update_config(_nonebot_config.fancy_source_query_config)
FSQ.lazy_load_t2g(SimpleTextDrawer())


query = on_command("query", aliases=set(exrex.generate("查[查询]?")), rule=to_me())
refresh = on_command(
    "refresh",
    aliases={
        "刷新",
    },
    rule=to_me(),
    permission=SUPERUSER,
)

__RE_CQAT = re.compile(r"\[CQ:at,qq=([1-9]([0-9]{4,}))\]")
__RE_SESSION = re.compile(r"group_([1-9]([0-9]{4,}))_([1-9]([0-9]{4,}))")


@query.handle()
async def _query(bot: Bot, ev: Event, qstr: Message = CommandArg()):
    """自动根据群号加载服务器组"""
    session = ev.get_session_id()
    logging.debug(f"{session=!r}")
    m = __RE_SESSION.fullmatch(session)
    if m:
        # 群聊环境
        session = int(m[1])
        user = int(ev.get_user_id())
        private = False
    else:
        # 私聊环境
        session = int(ev.get_user_id())
        user = None
        private = True
    gname = FSQ.find_gname_from_session(session)
    qtime, result = await FSQ.query(gname, str(qstr))
    if result is None:
        text = f"【{qstr}】不在哦~😥"
    else:
        if isinstance(result, list):
            fmts = "\n".join(FSQ.ifmt.format(r) for r in result)
            players = 0
            for r in result:
                if isinstance(r, ServerPair):
                    players += r.server.players
                elif isinstance(r, ServerInfo):
                    players += r.players
        else:
            fmts = FSQ.ifmt.format(result)
            players = None
        ttime = FSQ.ifmt.fmt_time(qtime)
        if players:
            text = f"{fmts}\n\nPlayers: {players}\n----{ttime}"
        else:
            text = f"{fmts}\n\n----{ttime}"

    if text.count("\n") > FSQ.config.output_max_lines:
        im = FSQ.t2g.draw(text)
        text = im2cqcode(im)
        logging.debug(f"build image, cq code length = {len(text)}.")

    if private:
        msg = text
    else:
        msg = f"[CQ:at,qq={user}]\n{text}"

    try:
        await query.finish(Message(msg))
    except ActionFailed:
        logging.error(f"message send failed: {text!r}")
        await query.finish()
    return


@refresh.handle()
async def _refresh(bot: Bot, ev: Event, item: Message = CommandArg()):
    item = str(item).strip()
    if item == "配置":
        FSQ.update_config()
        await refresh.finish("已刷新配置")
    elif item == "地图数据":
        FSQ.update_mapnames()
        await refresh.finish("已刷新地图数据")
    else:
        FSQ.update_config()
        FSQ.update_mapnames()
        await refresh.finish("已刷新配置和地图数据")


def im2png(im: Image) -> bytes:
    """将 PIL Image 转换成优化的 png 二进制数据"""
    with BytesIO() as buf:
        im.save(buf, format="png", optimize=True)
        return buf.getvalue()


def im2cqcode(im: Image) -> str:
    """将 PIL Image 转换成 CQ Code

    示例：[CQ:image,file=base64://123=,subType=1]
    """
    b = im2png(im)
    b64 = b64encode(b).decode()
    cqcode = f"[CQ:image,file=base64://{b64},subType=1]"
    return cqcode
