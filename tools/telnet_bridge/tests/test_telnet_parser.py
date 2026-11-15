# 文件名: tools/telnet_bridge/tests/test_telnet_parser.py
"""Tests for the Telnet state machine."""

import unittest

from telnet_bridge.telnet_parser import (
    TelnetParser, IAC, DO, DONT, WILL, WONT, SB, SE,
    OPT_ECHO, OPT_LINEMODE, OPT_NAWS, OPT_SUPPRESS_GA,
    MAX_SB_BYTES,
)


class TestTelnetParser(unittest.TestCase):
    def setUp(self):
        self.p = TelnetParser()

    def test_plain_data_passes_through(self):
        to_target, replies = self.p.feed(b"help\r")
        self.assertEqual(to_target, b"help\r")
        self.assertEqual(replies, b"")

    def test_reject_linemode(self):
        data = bytes([IAC, WILL, OPT_LINEMODE])
        to_target, replies = self.p.feed(data)
        self.assertEqual(to_target, b"")
        self.assertEqual(replies, bytes([IAC, DONT, OPT_LINEMODE]))

    def test_reject_echo(self):
        data = bytes([IAC, DO, OPT_ECHO])
        to_target, replies = self.p.feed(data)
        self.assertEqual(to_target, b"")
        self.assertEqual(replies, bytes([IAC, WONT, OPT_ECHO]))

    def test_reject_naws(self):
        data = bytes([IAC, WILL, OPT_NAWS])
        _, replies = self.p.feed(data)
        self.assertEqual(replies, bytes([IAC, DONT, OPT_NAWS]))

    def test_accept_suppress_go_ahead(self):
        data = bytes([IAC, DO, OPT_SUPPRESS_GA])
        _, replies = self.p.feed(data)
        self.assertEqual(replies, bytes([IAC, WILL, OPT_SUPPRESS_GA]))

    def test_crlf_to_cr(self):
        to_target, _ = self.p.feed(b"help\r\n")
        self.assertEqual(to_target, b"help\r")

    def test_standalone_cr_kept(self):
        to_target, _ = self.p.feed(b"help\r")
        self.assertEqual(to_target, b"help\r")

    def test_crlf_split_across_feeds(self):
        t1, _ = self.p.feed(b"help\r")
        t2, _ = self.p.feed(b"\n")
        self.assertEqual(t1, b"help\r")
        self.assertEqual(t2, b"")

    def test_cr_followed_by_normal_char(self):
        to_target, _ = self.p.feed(b"\rX")
        self.assertEqual(to_target, b"\rX")

    def test_double_crlf(self):
        to_target, _ = self.p.feed(b"\r\r\n")
        self.assertEqual(to_target, b"\r\r")

    def test_lone_lf_passes_through(self):
        to_target, _ = self.p.feed(b"a\nb")
        self.assertEqual(to_target, b"a\nb")

    def test_iac_iac_is_literal_ff(self):
        data = bytes([IAC, IAC])
        to_target, _ = self.p.feed(data)
        self.assertEqual(to_target, bytes([IAC]))

    def test_sb_subnegotiation_is_swallowed(self):
        data = bytes([IAC, SB, 34, 1, 0, IAC, SE]) + b"OK"
        to_target, replies = self.p.feed(data)
        self.assertEqual(replies, b"")
        self.assertEqual(to_target, b"OK")

    def test_sb_without_end_does_not_stall_forever(self):
        prefix = bytes([IAC, SB, 34]) + b"x" * 2000
        to_target, _ = self.p.feed(prefix)
        # Overflow is swallowed, not forwarded to the serial port.
        self.assertEqual(to_target, b"")

    def test_sb_overflow_ends_on_iac_se(self):
        # Start an over-long subnegotiation, then close it properly.
        prefix = bytes([IAC, SB, 34]) + b"x" * (MAX_SB_BYTES + 10)
        to_target, _ = self.p.feed(prefix)
        self.assertEqual(to_target, b"")

        tail, _ = self.p.feed(bytes([IAC, SE]) + b"OK")
        self.assertEqual(tail, b"OK")

    def test_sb_overflow_iac_iac_stays_in_overflow(self):
        prefix = bytes([IAC, SB, 34]) + b"x" * (MAX_SB_BYTES + 10)
        self.p.feed(prefix)

        # IAC IAC is an escaped 0xFF, still inside subnegotiation.
        mid, _ = self.p.feed(bytes([IAC, IAC]) + b"yy")
        self.assertEqual(mid, b"")

        # A real IAC SE closes it.
        tail, _ = self.p.feed(bytes([IAC, SE]) + b"OK")
        self.assertEqual(tail, b"OK")

    def test_sb_overflow_then_normal_data_after_close(self):
        prefix = bytes([IAC, SB, 34]) + b"x" * (MAX_SB_BYTES + 10)
        self.p.feed(prefix)
        tail, _ = self.p.feed(bytes([IAC, SE]) + b"help\r\n")
        self.assertEqual(tail, b"help\r")

    def test_text_after_negotiation(self):
        data = bytes([IAC, WILL, OPT_LINEMODE]) + b"help\r"
        to_target, replies = self.p.feed(data)
        self.assertEqual(replies, bytes([IAC, DONT, OPT_LINEMODE]))
        self.assertEqual(to_target, b"help\r")


if __name__ == "__main__":
    unittest.main()