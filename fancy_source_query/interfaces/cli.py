"""Fancy Source Query 的命令行接口，主要是从 interfaces 导入

其它接口：

+ nonebot: Nonebot 接口
+ interfaces: Python 接口
"""
import asyncio
import os
from argparse import ArgumentParser
from pathlib import Path

from . import FancySourceQuery, QueryResult, fmt_qresult


def cli_parser():
    """命令行工具不提供刷新配置的功能"""
    p = ArgumentParser(
        prog="fsq",
        usage="query source server's info",
        description="查询 Valve Source 服务器的信息和其中的玩家信息",
    )
    p.add_argument("GROUP", help="服务器组名")
    p.add_argument("QSTR", help="查询内容，可以是服务器名、“人数”、或玩家名", default="", nargs="?")
    p.add_argument("-c", default=None, help="设置工作目录，即加载配置文件的路径")
    return p


async def cli_main_async():
    p = cli_parser()
    args = p.parse_args()
    # 是否修改工作目录
    if args.c:
        cwd = Path(args.c).absolute().as_posix()
        os.chdir(cwd)
    app = FancySourceQuery()
    gname = args.GROUP
    qstr = args.QSTR
    qresult: QueryResult = await app.query(gname, qstr)
    text = await fmt_qresult(app, qresult, qstr)
    print(text)


def cli_main():
    asyncio.run(cli_main_async())


if __name__ == "__main__":
    cli_main()
