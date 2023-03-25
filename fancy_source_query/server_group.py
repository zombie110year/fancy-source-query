from .config import ServerConfig, ServerGroupConfig
import logging


class Server:
    name: str
    host: str
    port: int

    group: "ServerGroup"

    def __init__(self, name: str, host: str, port: int) -> None:
        self.name = name
        self.host = host
        self.port = port
        self.group = None

    def __str__(self) -> str:
        return f"Server(name={self.name}, host={self.host}, port={self.port})"


class ServerGroup:
    name: str
    related_sessions: list[str]
    servers: dict[str, "Server"]

    def __init__(self, name: str, related_sessions: list[str]) -> None:
        self.name = name
        self.related_sessions = related_sessions
        self.servers = dict()

    def add(self, server: Server):
        self.servers[server.name] = server
        server.group = self

    def __str__(self) -> str:
        servers = "\n".join(str(s) for s in self.servers.values())
        return f"ServerGroup({self.name}):\n{servers}"


def build_server_group_graph(
    groups_conf: list[ServerGroupConfig], servers_conf: list[ServerConfig]
) -> tuple[dict[str, ServerGroup], dict[str, Server]]:
    """根据服务器组配置创建服务器组、服务器组成的查找树：

    组名 => 服务器组 => 服务器名 => 服务器

    同时也返回直接根据服务器名查找服务器的查找树：

    服务器名 => 服务器
    """
    groups = {
        o.name: ServerGroup(name=o.name, related_sessions=o.related_sessions)
        for o in groups_conf
    }
    servers = {}
    for conf in servers_conf:
        if conf.group not in groups:
            logging.warning(f"orphan server, skip adding to group: {conf!r}")
            continue
        server = Server(name=conf.name, host=conf.host, port=conf.port)
        groups[conf.group].add(server)
        servers[server.name] = server

    debugtext = "\n".join(str(g) for g in groups.values())
    logging.debug(f"build server group graph: {debugtext}")
    return groups, servers
