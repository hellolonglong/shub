# 文件名: tools/telnet_bridge/telnet_parser.py
"""Telnet 状态机: 拒绝 LINEMODE/ECHO/NAWS，过滤协商字节，CRLF 归一化。

CRLF normalization: a CR is passed through immediately; an LF that
directly follows a CR is dropped. Standalone CR is passed through.
Standalone LF is passed through as-is.

Subnegotiation overflow: if a subnegotiation exceeds MAX_SB_BYTES
without closing, the parser enters SB_OVERFLOW and keeps swallowing
bytes until a real IAC SE arrives. This prevents subnegotiation bytes
from leaking into the serial port if the client never closes it.

Only for interactive text sessions. It rewrites CRLF to CR, so it is
NOT suitable for binary file transfers. Use Raw TCP for those.
"""

IAC = 0xFF
DONT = 0xFE
DO = 0xFD
WONT = 0xFC
WILL = 0xFB
SB = 0xFA
SE = 0xF0

OPT_ECHO = 1
OPT_SUPPRESS_GA = 3
OPT_NAWS = 31
OPT_LINEMODE = 34

CR = 0x0D
LF = 0x0A

MAX_SB_BYTES = 1024


class TelnetParser:
    """Feed client bytes; get (to_target, replies_to_client)."""

    def __init__(self):
        self._state = "DATA"
        self._pending_cmd = None
        self._last_was_cr = False
        self._sb_bytes = 0

    def feed(self, data):
        to_target = bytearray()
        replies = bytearray()
        for byte in data:
            self._feed_byte(byte, to_target, replies)
        return bytes(to_target), bytes(replies)

    def _feed_byte(self, byte, to_target, replies):
        state = self._state
        if state == "DATA":
            if byte == IAC:
                self._state = "IAC"
            else:
                self._emit_data(byte, to_target)
        elif state == "IAC":
            if byte == IAC:
                self._emit_data(IAC, to_target)
                self._state = "DATA"
            elif byte in (WILL, WONT, DO, DONT):
                self._pending_cmd = byte
                self._state = "OPTION"
            elif byte == SB:
                self._sb_bytes = 0
                self._state = "SB_OPTION"
            else:
                self._state = "DATA"
        elif state == "OPTION":
            self._handle_option(byte, replies)
            self._state = "DATA"
        elif state == "SB_OPTION":
            self._state = "SB_DATA"
        elif state == "SB_DATA":
            self._sb_bytes += 1
            if self._sb_bytes > MAX_SB_BYTES:
                self._state = "SB_OVERFLOW"
            elif byte == IAC:
                self._state = "SB_IAC"
        elif state == "SB_IAC":
            if byte == SE:
                self._state = "DATA"
                self._sb_bytes = 0
            elif byte == IAC:
                self._state = "SB_DATA"
            else:
                self._state = "SB_DATA"
        elif state == "SB_OVERFLOW":
            if byte == IAC:
                self._state = "SB_OVERFLOW_IAC"
        elif state == "SB_OVERFLOW_IAC":
            if byte == SE:
                self._state = "DATA"
                self._sb_bytes = 0
            else:
                self._state = "SB_OVERFLOW"

    def _handle_option(self, opt, replies):
        cmd = self._pending_cmd
        self._pending_cmd = None

        if cmd == WILL:
            replies.extend([IAC, DONT, opt])
        elif cmd == DO:
            if opt == OPT_SUPPRESS_GA:
                replies.extend([IAC, WILL, opt])
            else:
                replies.extend([IAC, WONT, opt])

    def _emit_data(self, byte, to_target):
        if self._last_was_cr and byte == LF:
            self._last_was_cr = False
            return
        self._last_was_cr = (byte == CR)
        to_target.append(byte)