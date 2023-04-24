"""Fancy Source Query 的 Nonebot 接口，在此处配置 Nonebot 相关响应器

其它接口：

+ interfaces : Python 接口
+ cli : 命令行接口
"""
import logging
import re
from base64 import b64encode
from io import BytesIO
from random import shuffle

import exrex
from nonebot import get_driver, on_command
from nonebot.adapters.onebot.v11 import (
    GROUP_ADMIN,
    GROUP_OWNER,
    Bot,
    Event,
    Message,
    MessageSegment,
)
from nonebot.exception import ActionFailed
from nonebot.params import CommandArg
from nonebot.permission import SUPERUSER
from nonebot.rule import to_me
from PIL.Image import Image

from impaper import SimpleTextDrawer

from ..config import NonebotConfig
from . import FancySourceQuery, QueryResult, ServerInfo, ServerPair, fmt_qresult

_global_config = get_driver().config
_nonebot_config = NonebotConfig.parse_obj(_global_config)
FSQ = FancySourceQuery()
FSQ.update_config(_nonebot_config.fancy_source_query_config)
FSQ.lazy_load_t2g(SimpleTextDrawer())

ALL_ADMINS = SUPERUSER | GROUP_OWNER | GROUP_ADMIN

query = on_command("query", aliases=set(exrex.generate("查[查询]?")), rule=to_me())
refresh = on_command(
    "refresh",
    aliases={
        "刷新",
    },
    rule=to_me(),
    permission=ALL_ADMINS,
)
choose_map = on_command(
    "choose_map",
    aliases=set(exrex.generate("[抽选]图")),
    rule=to_me(),
    permission=ALL_ADMINS,
)
__RE_CQAT = re.compile(r"\[CQ:at,qq=([1-9]([0-9]{4,}))\]")
__RE_SESSION = re.compile(r"group_([1-9]([0-9]{4,}))_([1-9]([0-9]{4,}))")
__RE_COUNTS = re.compile(r"(\d+)[张]?")


@query.handle()
async def _query(bot: Bot, ev: Event, qstr: Message = CommandArg()):
    """自动根据群号加载服务器组"""
    session = ev.get_session_id()
    logging.debug(f"{session=!r}")
    m = __RE_SESSION.fullmatch(session)
    if m:
        # 群聊环境
        session = m[1]
        user = ev.get_user_id()
        private = False
    else:
        # 私聊环境
        session = ev.get_user_id()
        user = ev.get_user_id()
        private = True
    gname = FSQ.find_gname_from_session(session)
    maybe_at = str(qstr).strip()
    if m := __RE_CQAT.fullmatch(maybe_at):
        target_qq = m[1]
        name = await get_group_member_name(bot, session, target_qq)
        qresult: QueryResult = await search_user_by_qq_name(gname, name)
        qstr = name
    else:
        qresult: QueryResult = await FSQ.query(gname, str(qstr))
    text = await fmt_qresult(FSQ, qresult, qstr)
    lines = text.count("\n")
    if lines > FSQ.config.output_max_lines:
        im = FSQ.t2g.draw(text)
        text = im2cqcode(im)
        logging.info(f"build image, cq code length = {len(text)}.")
    else:
        # 以文本模式输出时去除标签
        t2g: SimpleTextDrawer = FSQ.t2g
        text = t2g._labels_re.sub("", text)
    if private:
        msg = Message(text)
    else:
        if lines > FSQ.config.output_max_lines * 2:
            # 即便转成图片也很长，则收集到合并转发消息中
            at_ = Message(f"[CQ:at,qq={user}]\n图片太长，收到合并转发里了")
            msg = Message(
                MessageSegment.node_custom(user_id=user, nickname="这谁？", content=text)
            )
            await query.send(at_)
            await bot.send_group_forward_msg(group_id=int(session), messages=msg)
            return
        else:
            msg = Message(f"[CQ:at,qq={user}]\n{text}")

    try:
        await query.finish(msg)
    except ActionFailed:
        logging.error(f"message send failed: {text[:100]!r}")
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


@choose_map.handle()
async def _choose_map(bot: Bot, ev: Event, counts: Message = CommandArg()):
    """抽取非官方地图，默认3张，若输入数字则抽取对应数量"""
    session = ev.get_session_id()
    logging.debug(f"{session=!r}")
    m = __RE_SESSION.fullmatch(session)
    # 群聊环境
    session = m[1]
    user = ev.get_user_id()
    counts = str(counts).strip()
    m2 = __RE_COUNTS.search(counts)
    counts = int(m2[1]) if m2 is not None else 3
    if counts > FSQ.config.map_choices_max_counts:
        counts = FSQ.config.map_choices_max_counts
        await choose_map.send(Message(f"抽这么多，打得完吗？😅\n给你{counts}张。"))
    candidates = [i for i in FSQ.mapnames if not i.official]
    shuffle(candidates)
    selected = candidates[:counts]
    names = []
    for i in selected:
        if i.name_zh is not None:
            names.append(i.name_zh)
        else:
            names.append(i.name)
    text = "/".join(names)
    msg = Message(f"[CQ:at,qq={user}]\n{text}")
    await choose_map.finish(msg)
    return


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


async def get_group_member_name(bot: Bot, group: str, id: str) -> str:
    """查询群聊中成员名称，如果有群名片，则获取群名片，否则获取昵称"""
    info = await bot.get_group_member_info(
        group_id=int(group), user_id=int(id), no_cache=True
    )
    name = info.get("card", "")
    if name == "":
        name = info.get("nickname", ".")
    return name


async def search_user_by_qq_name(gname: str, name: str) -> QueryResult:
    """搜索玩家，如果全名找不到，则搜索含任意一个字的名称"""
    result = await FSQ.search_player(name, gname)
    if result.result is None:
        pat = f"[{name}]"
        result = await FSQ.search_player(pat, gname)
    return result
