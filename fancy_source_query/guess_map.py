from .config import Mapname


def guess_map(rlookup: dict[str, Mapname], code: str):
    """从反查表 rlookup 中读取地图代码对应的地图名，
    如果没有，则返回 None；
    如果有则优先返回 name_zh，如果没有 name_zh 则返回 name。
    """
    mapname = rlookup.get(code.lower(), None)
    if mapname:
        if name := mapname.name_zh:
            return name
        else:
            name = mapname.name
            return name
    return


def build_rlookup(mapnames: list[Mapname]) -> dict[str, Mapname]:
    return {mapcode.lower(): obj for obj in mapnames for mapcode in obj.maps}
