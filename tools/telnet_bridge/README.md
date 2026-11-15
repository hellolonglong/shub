<!-- 文件名: tools/telnet_bridge/README.md -->
# telnet_bridge — shub 的 Telnet 兼容层

## 定位

独立于 shub 的可选工具。解决 MobaXterm Telnet 会话连 shub 时的终端兼容问题（方向键只移动光标、回车多空行）。shub 不知道它存在，它也不感知 shub 进程。

## 数据流

```
MobaXterm Telnet
   ↓
telnet_bridge（监听 2000 段）
   ├── 拒绝 LINEMODE / ECHO / NAWS
   ├── 正向过滤 Telnet 协商字节
   ├── 正向 \r\n 归一化成 \r
   └── 反向原样转发
   ↓ 裸 TCP
shub 127.0.0.1:1000
   ↓
真实串口
```

## 目录

```
tools/telnet_bridge/
├── conf/
│   └── bridge_config.json     程序自身配置
├── mappings/
│   └── example.json           映射文件示例
├── main.py
├── config.py
├── telnet_parser.py
├── bridge.py
├── mapping.py
├── mapping_io.py
├── trans_parser.py            trans 参数解析
├── remove_parser.py           remove 参数解析
├── repl.py
└── README.md
```

## 启动

```bash
cd tools
python -m telnet_bridge
```

启动后进入空 shell，不监听任何端口：

```
telnet_bridge v0.1
  config: C:\shub\tools\telnet_bridge\conf\bridge_config.json
  bind_addr: 0.0.0.0
  target_host: 127.0.0.1
  offset: 1000
  AutoTrans: off

No mappings. Use 'trans <shub_port> [to <bridge_port>]' to add one.
Type 'help' for commands.

telnet_bridge>
```

## 指令

| 指令 | 作用 |
|---|---|
| `trans <shub_port>` | 监听 `shub_port + offset`，转发到 `target_host:<shub_port>` |
| `trans <shub_port> to <bridge_port>` | 显式指定监听端口 |
| `trans --from <name>` | 从 `mappings/<name>.json` 批量加载映射 |
| `trans -h` / `trans --help` | 显示 trans 帮助 |
| `list` | 列出所有映射 |
| `remove <bridge_port>` | 停止并移除指定映射 |
| `remove all` | 停止并移除所有映射 |
| `remove -h` / `remove --help` | 显示 remove 帮助 |
| `help` | 显示总帮助 |
| `exit` / `quit` | 停止所有映射并退出 |

`list` 和 `help` 不接受参数，带参数会报错。

`remove` 只接受 **BRIDGE 端口**（`list` 左列）。传入 shub_port 时会提示对应的 bridge_port。

同一 `shub_port` 只能映射一次；再次 `trans` 会报 `already mapped to bridge port X`，先 `remove` 再 `trans`。

`trans -x` 这类未知选项会报 `unknown option: -x`，不会被当作端口解析。

`trans --from -h` / `trans --from --help` 显示 trans 帮助。

## 配置文件 `conf/bridge_config.json`

```json
{
  "bind_addr": "0.0.0.0",
  "target_host": "127.0.0.1",
  "offset": 1000,
  "AutoTrans": false,
  "mappings": []
}
```

| 字段 | 默认 | 说明 |
|---|---|---|
| `bind_addr` | `0.0.0.0` | 兼容层监听地址 |
| `target_host` | `127.0.0.1` | shub 地址 |
| `offset` | `1000` | `trans 1000` 默认监听 `2000` |
| `AutoTrans` | `false` | `true` 时启动加载 `mappings` |
| `mappings` | `[]` | 字符串数组 |

`AutoTrans` 是“启动时预置一批映射”，不是锁定模式。加载完成后照常进入 shell，`trans` / `remove` / `list` 全部可用。

## 映射文件

固定放在 `mappings/` 下，`trans --from` 只接受**纯文件名**：

| 用户输入 | 实际读取 |
|---|---|
| `trans --from example` | `mappings/example.json` |
| `trans --from example.json` | `mappings/example.json` |
| `trans --from ../evil` | 拒绝：`invalid mapping file name` |
| `trans --from sub/example` | 拒绝：`invalid mapping file name` |
| `trans --from C:\evil` | 拒绝：`invalid mapping file name` |

映射文件格式是字符串数组：

```json
["1000:2000", "1001", "1002:3000"]
```

| 文件里的写法 | 等价指令 |
|---|---|
| `"1000:2000"` | `trans 1000 to 2000` |
| `"1001"` | `trans 1001`（走 offset） |

这里 `<shub_port>` 和 `<bridge_port>` 是占位符，实际写的是端口号，不是 `shub` / `bridge` 这两个词。

示例文件 `mappings/example.json` 可以直接复制改名：

```
copy mappings\example.json mappings\my_boards.json
trans --from my_boards
```

## 错误分类

`trans --from` 的错误分三类，提示不同：

| 错误 | 提示 |
|---|---|
| `MappingPathError`（路径非法） | `Use a plain file name under mappings/` |
| `MappingFormatError`（JSON / 非数组 / 非 UTF-8） | 只报具体格式错误，不误导为路径问题 |
| `FileNotFoundError`（文件不存在） | `Mapping files live under mappings/` |

## 路径规则

| 参数 | 规则 |
|---|---|
| `--config`（命令行） | 接受任意路径，由运维人员显式指定 |
| `trans --from <name>` | 只接受 `mappings/` 下的纯文件名 |

`trans --from` 的路径校验和 shub 的 `profiles.py` 一致：

- 拒绝空名；
- 拒绝 `/` `\` `..`；
- 拒绝绝对路径；
- `realpath` 校验必须位于 `mappings/` 下。

## 端口约定

| 端口段 | 用途 |
|---|---|
| `1000–1999` | shub 串口共享 |
| `2000–2999` | 兼容层监听 |

MobaXterm Telnet 连 `A:2000` 段；Raw TCP / PuTTY Raw 直连 shub `A:1000` 段。

## 限制

- **只适合交互式文本会话**，`\r\n → \r` 归一化会破坏二进制；
- 不支持文件传输（ZMODEM/XMODEM/YMODEM）；
- 不做认证、加密，部署在可信局域网；
- 不做 BINARY 协商、反向 `0xFF` 转义、NVT 换行规则；
- 不感知、不管理 shub 进程。

## 测试

```bash
cd tools
python -m unittest discover telnet_bridge/tests -v
```