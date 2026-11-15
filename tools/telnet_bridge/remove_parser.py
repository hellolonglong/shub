# 文件名: tools/telnet_bridge/remove_parser.py
"""Parse `remove` argument tokens into a RemoveCommand.

Pure function: no printing, no REPL dependency, easy to unit test.

Grammar:
    remove <bridge_port>
    remove all
    remove -h | --help
"""

from dataclasses import dataclass


@dataclass
class RemoveCommand:
    mode: str             # "help" / "usage" / "error" / "all" / "one"
    bridge_port: int = 0
    error: str = ""


def parse_remove(parts):
    """Return a RemoveCommand. `parts` is the token list after `remove`."""
    if not parts:
        return RemoveCommand("usage")

    if len(parts) == 1 and parts[0] in ("-h", "--help"):
        return RemoveCommand("help")

    if len(parts) != 1:
        return RemoveCommand("usage")

    arg = parts[0]

    if arg.lower() == "all":
        return RemoveCommand("all")

    try:
        bridge_port = int(arg)
    except ValueError:
        return RemoveCommand(
            "error", error=f"invalid bridge_port: {arg}")

    if not (1 <= bridge_port <= 65535):
        return RemoveCommand(
            "error",
            error=f"bridge_port must be 1-65535, got {bridge_port}")

    return RemoveCommand("one", bridge_port=bridge_port)