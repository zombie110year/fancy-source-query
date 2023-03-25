import pytest
import toml

from fancy_source_query.config import (
    DEFAULT_MAPNAMES_PATH,
    MAPNAMES_PATH_PREFIX,
    Mapname,
)
from fancy_source_query.guess_map import build_rlookup, guess_map
from fancy_source_query.interfaces import FancySourceQuery


@pytest.fixture(scope="session", autouse=True)
def rlookup():
    mapnames = toml.load(DEFAULT_MAPNAMES_PATH)
    mapnames = [Mapname.parse_obj(x) for x in mapnames[MAPNAMES_PATH_PREFIX]]
    return build_rlookup(mapnames)


@pytest.fixture(scope="session", autouse=True)
def fsquery():
    x = FancySourceQuery()
    return x


def test_c1m1(rlookup: dict[str, Mapname]):
    code = "c1m1_hotel"
    name = guess_map(rlookup, code)
    assert name == "死亡中心"


def test_fsquery_guess_map(fsquery: FancySourceQuery):
    code = "c1m1_hotel"
    name = fsquery.guess_map(code)
    assert name == f"死亡中心|{code}"
