# 文件名: tools/telnet_bridge/tests/test_config.py
"""Tests for telnet_bridge.config."""

import json
import os
import shutil
import tempfile
import unittest

from telnet_bridge.config import DEFAULT_CONFIG, load_config


class TestConfig(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.mkdtemp()

    def tearDown(self):
        shutil.rmtree(self.tmp, ignore_errors=True)

    def _write(self, data):
        path = os.path.join(self.tmp, "bridge_config.json")
        with open(path, "w", encoding="utf-8") as f:
            json.dump(data, f)
        return path

    def test_missing_file_returns_defaults(self):
        cfg, err = load_config(os.path.join(self.tmp, "nope.json"))
        self.assertIsNone(err)
        self.assertEqual(cfg["offset"], DEFAULT_CONFIG["offset"])
        self.assertEqual(cfg["bind_addr"], DEFAULT_CONFIG["bind_addr"])
        self.assertFalse(cfg["AutoTrans"])
        self.assertEqual(cfg["mappings"], [])

    def test_custom_values(self):
        path = self._write({
            "bind_addr": "127.0.0.1",
            "target_host": "192.168.1.100",
            "offset": 500,
            "AutoTrans": True,
            "mappings": ["1000:2000", "1001"],
        })
        cfg, err = load_config(path)
        self.assertIsNone(err)
        self.assertEqual(cfg["bind_addr"], "127.0.0.1")
        self.assertEqual(cfg["target_host"], "192.168.1.100")
        self.assertEqual(cfg["offset"], 500)
        self.assertTrue(cfg["AutoTrans"])
        self.assertEqual(cfg["mappings"], ["1000:2000", "1001"])

    def test_auto_trans_false_default(self):
        path = self._write({})
        cfg, err = load_config(path)
        self.assertIsNone(err)
        self.assertFalse(cfg["AutoTrans"])

    def test_mappings_non_strings_filtered(self):
        path = self._write({
            "mappings": ["1000", 123, None, "1001:2001"],
        })
        cfg, _ = load_config(path)
        self.assertEqual(cfg["mappings"], ["1000", "1001:2001"])

    def test_mappings_not_a_list_resets(self):
        path = self._write({"mappings": "not a list"})
        cfg, _ = load_config(path)
        self.assertEqual(cfg["mappings"], [])

    def test_bad_json_returns_defaults_with_error(self):
        path = os.path.join(self.tmp, "bad.json")
        with open(path, "w") as f:
            f.write("{not json")
        cfg, err = load_config(path)
        self.assertIsNotNone(err)
        self.assertEqual(cfg["offset"], DEFAULT_CONFIG["offset"])

    def test_offset_invalid_falls_back(self):
        path = self._write({"offset": "abc"})
        cfg, _ = load_config(path)
        self.assertEqual(cfg["offset"], DEFAULT_CONFIG["offset"])

    def test_bind_addr_empty_falls_back(self):
        path = self._write({"bind_addr": ""})
        cfg, _ = load_config(path)
        self.assertEqual(cfg["bind_addr"], DEFAULT_CONFIG["bind_addr"])


if __name__ == "__main__":
    unittest.main()