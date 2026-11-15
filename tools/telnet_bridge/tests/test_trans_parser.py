# 文件名: tools/telnet_bridge/tests/test_trans_parser.py
"""Tests for telnet_bridge.trans_parser.parse_trans."""

import unittest

from telnet_bridge.trans_parser import parse_trans


class TestParseTrans(unittest.TestCase):
    def test_empty_is_usage(self):
        self.assertEqual(parse_trans([]).mode, "usage")

    def test_help(self):
        self.assertEqual(parse_trans(["-h"]).mode, "help")
        self.assertEqual(parse_trans(["--help"]).mode, "help")

    def test_from_name(self):
        cmd = parse_trans(["--from", "example"])
        self.assertEqual(cmd.mode, "from")
        self.assertEqual(cmd.file_name, "example")

    def test_from_missing_arg(self):
        self.assertEqual(parse_trans(["--from"]).mode, "error")

    def test_from_extra_arg(self):
        self.assertEqual(
            parse_trans(["--from", "a", "b"]).mode, "error")

    def test_from_help_short(self):
        self.assertEqual(parse_trans(["--from", "-h"]).mode, "help")

    def test_from_help_long(self):
        self.assertEqual(parse_trans(["--from", "--help"]).mode, "help")

    def test_unknown_short_option(self):
        self.assertEqual(parse_trans(["-x"]).mode, "error")

    def test_unknown_long_option(self):
        self.assertEqual(parse_trans(["--foo"]).mode, "error")

    def test_shub_only(self):
        cmd = parse_trans(["1000"])
        self.assertEqual(cmd.mode, "one")
        self.assertEqual(cmd.shub_port, 1000)
        self.assertIsNone(cmd.bridge_port)

    def test_shub_with_bridge(self):
        cmd = parse_trans(["1000", "to", "3000"])
        self.assertEqual(cmd.mode, "one")
        self.assertEqual(cmd.shub_port, 1000)
        self.assertEqual(cmd.bridge_port, 3000)

    def test_to_is_case_insensitive(self):
        cmd = parse_trans(["1000", "TO", "3000"])
        self.assertEqual(cmd.mode, "one")
        self.assertEqual(cmd.bridge_port, 3000)

    def test_invalid_shub_port(self):
        self.assertEqual(parse_trans(["abc"]).mode, "error")

    def test_shub_port_zero(self):
        self.assertEqual(parse_trans(["0"]).mode, "error")

    def test_shub_port_too_large(self):
        self.assertEqual(parse_trans(["65536"]).mode, "error")

    def test_invalid_bridge_port(self):
        self.assertEqual(
            parse_trans(["1000", "to", "abc"]).mode, "error")

    def test_bridge_port_zero(self):
        self.assertEqual(
            parse_trans(["1000", "to", "0"]).mode, "error")

    def test_bridge_port_too_large(self):
        self.assertEqual(
            parse_trans(["1000", "to", "65536"]).mode, "error")

    def test_wrong_shape(self):
        self.assertEqual(parse_trans(["1000", "x"]).mode, "error")
        self.assertEqual(
            parse_trans(["1000", "to", "2000", "extra"]).mode, "error")


if __name__ == "__main__":
    unittest.main()