# 文件名: tools/telnet_bridge/tests/test_repl_dispatch.py
"""Tests for BridgeRepl._handle dispatch.

These tests verify that each command name routes to the right handler
and that exit/quit/unknown/syntax-error paths behave as expected.
They do not exercise the handlers themselves.
"""

import unittest
from unittest.mock import patch

from telnet_bridge.config import DEFAULT_CONFIG
from telnet_bridge.repl import BridgeRepl


class TestReplDispatch(unittest.TestCase):
    def setUp(self):
        self.repl = BridgeRepl(dict(DEFAULT_CONFIG))

    def test_help_dispatches(self):
        with patch.object(self.repl, "_handle_help") as m:
            self.repl._handle("help")
        m.assert_called_once_with([])

    def test_trans_dispatches(self):
        with patch.object(self.repl, "_handle_trans") as m:
            self.repl._handle("trans 1000")
        m.assert_called_once_with(["1000"])

    def test_trans_case_insensitive(self):
        with patch.object(self.repl, "_handle_trans") as m:
            self.repl._handle("TRANS 1000")
        m.assert_called_once_with(["1000"])

    def test_list_dispatches(self):
        with patch.object(self.repl, "_handle_list") as m:
            self.repl._handle("list")
        m.assert_called_once_with([])

    def test_remove_dispatches(self):
        with patch.object(self.repl, "_handle_remove") as m:
            self.repl._handle("remove 2000")
        m.assert_called_once_with(["2000"])

    def test_exit_returns_false(self):
        self.assertFalse(self.repl._handle("exit"))
        self.assertFalse(self.repl._handle("quit"))

    def test_exit_case_insensitive(self):
        self.assertFalse(self.repl._handle("EXIT"))
        self.assertFalse(self.repl._handle("Quit"))

    def test_exit_with_arg_is_rejected(self):
        self.assertTrue(self.repl._handle("exit foo"))
        self.assertTrue(self.repl._handle("quit foo"))

    def test_unknown_command(self):
        self.assertTrue(self.repl._handle("foo"))

    def test_empty_line(self):
        self.assertTrue(self.repl._handle(""))
        self.assertTrue(self.repl._handle("   "))

    def test_syntax_error(self):
        # unclosed quote -> shlex raises ValueError; _handle returns True.
        self.assertTrue(self.repl._handle('trans "1000'))


if __name__ == "__main__":
    unittest.main()