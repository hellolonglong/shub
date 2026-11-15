# 文件名: tools/telnet_bridge/trans_parser.py
"""Parse `trans` argument tokens into a TransCommand.

Pure function: no printing, no REPL dependency, easy to unit test.

Grammar:
    trans <shub_port>
    trans <shub_port> to <bridge_port>
    trans --from <name>
    trans -h | --help
"""

from dataclasses import dataclass
from typing import Optional


@dataclass
class TransCommand:
    mode: str                 # "help" / "usage" / "error" / "from" / "one"
    shub_port: int = 0
    bridge_port: Optional[int] = None
    file_name: str = ""
    error: str = ""


def parse_trans(parts):
    """Return a TransCommand. `parts` is the token list after `trans`."""
    if not parts:
        return TransCommand("usage")

    if parts[0] in ("-h", "--help"):
        return TransCommand("help")

    if parts[0] == "--from":
        if len(parts) == 2 and parts[1] in ("-h", "--help"):
            return TransCommand("help")
        if len(parts) != 2:
            return TransCommand(
                "error",
                error="'--from' takes exactly one file name")
        return TransCommand("from", file_name=parts[1])

    if parts[0].startswith("-"):
        return TransCommand(
            "error", error=f"unknown option: {parts[0]}")

    try:
        shub_port = int(parts[0])
    except ValueError:
        return TransCommand(
            "error", error=f"invalid shub_port: {parts[0]}")

    if not (1 <= shub_port <= 65535):
        return TransCommand(
            "error",
            error=f"shub_port must be 1-65535, got {shub_port}")

    if len(parts) == 1:
        return TransCommand("one", shub_port=shub_port)

    if len(parts) == 3 and parts[1].lower() == "to":
        try:
            bridge_port = int(parts[2])
        except ValueError:
            return TransCommand(
                "error", error=f"invalid bridge_port: {parts[2]}")
        if not (1 <= bridge_port <= 65535):
            return TransCommand(
                "error",
                error=f"bridge_port must be 1-65535, got {bridge_port}")
        return TransCommand(
            "one", shub_port=shub_port, bridge_port=bridge_port)

    return TransCommand(
        "error",
        error="usage: trans <shub_port> [to <bridge_port>]")