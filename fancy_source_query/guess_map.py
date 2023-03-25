from .config import Mapname


def guess_map(rlookup: dict[str, Mapname], code: str):
    """从反查表 rlookup 中读取地图代码对应的地图名，
    如果没有，则只返回 code；
    如果有则返回 name | code。
    """
    mapname = rlookup.get(code, None)
    if mapname:
        if name := mapname.name_zh:
            return f"{name}|{code}"
        else:
            name = mapname.name
            return f"{name}|{code}"
    else:
        return code


def build_rlookup(mapnames: list[Mapname]) -> dict[str, Mapname]:
    return {mapcode: obj for obj in mapnames for mapcode in obj.maps}
