# Nonebot plugin fancy source query

这个插件的目的是将 Source Server Query 的功能集成进 Nonebot 框架中，
以便使用者方便地实现查询 Valve Source 服务器状态的查询。
并且默认实现了将较长的查询结果转换成图片输出的功能，以免刷屏
（此功能仅在 QQ 上测试）。


## 功能介绍

FancySourceQuery(以下简称FSQ) 插件可以查询 Source 服务器的名称、人数、正在运行的地图和服务器内玩家的详细状态。
提供以下指令：

1. 查询：查询当前服务器组的概况（所有服务器名称、当前人数、最大玩家数、地图名称）并统计总人数
2. 查询人数：同上
3. 查询（服务器名）：当输入的参数不为空或“人数”时，机器人优先将其认作服务器的名称，将会从当前服务器中寻找对应的服务器，
    查询服务器的状态和详细的玩家状态
4. 查询（玩家名）：当输入的参数不为空或“人数”或已知的服务器名时，机器人会将其认作玩家的名称片段，将会从当前服务器组里的所有服务器中搜索玩家名匹配的玩家信息（输入参数被当作正则表达式处理，并且匹配标准是 `re.search`）
5. 刷新配置：此功能仅 SUPERUSER 可用，可让机器人在不停机的情况下重新加载配置文件
6. 刷新地图数据：此功能仅 SUPERUSER 可用，可让机器人在不停机的情况下重新加载地图数据

该插件的所有功能都提供 Python 接口或命令行接口，可以在不启动 Nonebot 的情况下执行，以便调试。

+ Python 接口为 `fancy_source_query.interfaces:FancySourceQuery` 此对象的所有方法都返回适合 Python 处理的对象
+ Cli 接口在 `fancy_source_query.interfaces.cli:cli_main` 此方法提供了命令行的程序调用
+ nonebot 接口在 `fancy_source_query.interfaces.nonebot` 此模块中定义了 Nonebot 响应函数，只支持 Onebot v11 程序

## 相关文件

运行时，你的项目文件夹下必须有这两个文件：

1. `fancy_source_query.toml` ： 默认的配置文件
2. `mapnames.toml` ： 默认的地图数据文件，其中储存了地图的原名、中文名、地图代码，以便插件生成对应的反查表

文件内容可以查看仓库中的示例，其中 `mapnames.toml` 文件在另一地址有随时更新的版本 （TODO）

## 安装

将此插件添加到 Nonebot 项目的依赖中，可以使用 nb-cli 或者 pdm, poetry, pip 等
包管理工具安装。

例如：

```sh
pdm add fancy_source_query
```

然后在 `pyproject.toml` 中配置：

```toml
[tool.nonebot]
plugins = [
    # ...
    "fancy_source_query.interfaces.nonebot",
    # ...
]
```

## 配置

此插件的配置分为两个部分，一个是 NoneBot 的 Env 配置文件，另一个（主要的）是 toml 格式的配置。

```env
FANCY_SOURCE_QUERY_CONFIG="fancy_source_query.toml"
```

env 配置中只需要指定插件配置文件的路径，默认为 nonebot 进程工作目录下的 `fancy_source_query.toml` 文件。
以下为默认的配置模板与解释：

```toml
[fancy_source_query]
# 默认超时等待 5s
timeout = 5
# 默认查询池缓存 20s
cache_delay = 20
# 默认限制文本输出 5 行，超过 5 行的转成图片输出
output_max_lines = 5
# Fancy Source Query 可以配置地图数据库，方便将地图代码转换成人类可读的地图名
# 该路径相对于 nonebot 进程工作目录
mapnames_db = "mapnames.toml"
# 默认的服务器组，在不传入组名时使用此组
default_server_group = "A"
# 转图片时的字号，px
fontsize = 16

[fancy_source_query.impaper]
# 建议留空，加载默认的更纱黑体，
# 或者指定一个 ttf 文件的路径。
# font.path =
[fancy_source_query.impaper.layout]
# 外边距，按上右下左的顺序（和 CSS 里的习惯一致），px
# 右边距建议拉大一点，防止手机上看时像素被遮住
margin = [6, 6, 18, 6]
# 内边距，按上右下左的顺序（和 CSS 里的习惯一致），px
padding = [2, 2, 2, 2]
# 行间距，px
spacing = 2
[fancy_source_query.impaper.typesetting]
# 行宽，英文1，汉字2
line_width = 52
# 折行缩进
indentation = "  "

# 格式化查询数据的模板
[fancy_source_query.fmt]
server_info = "{name}\n==({players:>2d}/{max_players:>2d})[{mapname}]"
player_info = ">>[{score}]({minutes:.1f}min){name}"
rule_info = "({key} = {value})"
# strftime 格式符
time = "%Y-%m-%d %H:%M:%S"

# Fancy Source Query 可以为不同的 QQ 群设置不同的服务器组
# 为不同的群分别提供查询服务，例如为 A 群配置服务器组 AG, 其中包含服务器 A1, A2, A3；
# 为 B 群配置服务器组 BG，其中包含服务器 B1, B2, B3；
# 为 开发者测试群 配置服务器组 DEVG，其中包含所有服务器；
# 那么机器人在 A 群中查询时只会考虑 A1, A2, A3 服务器，以此类推。
[[fancy_source_query.server_groups]]
name = "A"
related_sessions = ["<QQ群号A>", "<开发者测试群>"]
[[fancy_source_query.server_groups]]
name = "B"
related_sessions = ["<QQ群号B>", "<开发者测试群>"]

[[fancy_source_query.servers]]
# 此处的 A 需要与 server_group.name 相同
group = "A"
name = "A1"
host = "127.0.0.1"
port = 65501
[[fancy_source_query.servers]]
group = "A"
name = "A2"
host = "127.0.0.1"
port = 65502
[[fancy_source_query.servers]]
group = "B"
name = "B1"
host = "127.0.0.1"
port = 64501
```

在修改完配置文件后，可以通过 SUPERUSER 账号向机器人发送 "刷新" 指令，以热重载配置和数据。
