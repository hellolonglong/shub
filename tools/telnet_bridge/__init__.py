# 文件名: tools/telnet_bridge/__init__.py
"""telnet_bridge: Telnet compatibility layer for shub.

A standalone optional tool. It listens on bridge ports and forwards
Telnet clients to a shub port, rejecting LINEMODE / ECHO so MobaXterm
enters character-at-a-time mode. It does not know or manage shub.
"""