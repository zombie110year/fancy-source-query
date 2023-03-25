import pytest
from fancy_source_query.guess_map import guess_map, build_rlookup
from fancy_source_query.config import DEFAULT_MAPNAMES_PATH, Mapname
import toml


@pytest.fixture(scope="session", autouse=True)
def rlookup():
    mapnames = toml.load(DEFAULT_MAPNAMES_PATH)
    mapnames = [Mapname.parse_obj(x) for x in mapnames["mapnames"]]
    return build_rlookup(mapnames)


def test_c1m1(rlookup: dict[str, Mapname]):
    code = "c1m1_hotel"
    name = guess_map(rlookup, code)
    assert name == f"死亡中心|{code}"
