# 文件名: tools/telnet_bridge/tests/test_remove_parser.py
"""Tests for telnet_bridge.remove_parser.parse_remove."""

import unittest

from telnet_bridge.remove_parser import parse_remove


class TestParseRemove(unittest.TestCase):
    def test_empty_is_usage(self):
        self.assertEqual(parse_remove([]).mode, "usage")

    def test_help(self):
        self.assertEqual(parse_remove(["-h"]).mode, "help")
        self.assertEqual(parse_remove(["--help"]).mode, "help")

    def test_all(self):
        self.assertEqual(parse_remove(["all"]).mode, "all")
        self.assertEqual(parse_remove(["ALL"]).mode, "all")

    def test_single_port(self):
        cmd = parse_remove(["2000"])
        self.assertEqual(cmd.mode, "one")
        self.assertEqual(cmd.bridge_port, 2000)

    def test_invalid_port(self):
        self.assertEqual(parse_remove(["abc"]).mode, "error")

    def test_port_zero(self):
        self.assertEqual(parse_remove(["0"]).mode, "error")

    def test_port_too_large(self):
        self.assertEqual(parse_remove(["65536"]).mode, "error")

    def test_extra_args(self):
        self.assertEqual(parse_remove(["2000", "extra"]).mode, "usage")


if __name__ == "__main__":
    unittest.main()