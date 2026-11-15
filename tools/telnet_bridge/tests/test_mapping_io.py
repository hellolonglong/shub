# 文件名: tools/telnet_bridge/tests/test_mapping_io.py
"""Tests for telnet_bridge.mapping_io."""

import os
import shutil
import tempfile
import unittest

from telnet_bridge import mapping_io
from telnet_bridge.mapping_io import MappingFormatError, MappingPathError


class TestMappingIO(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.mkdtemp()
        self._orig = mapping_io.mappings_dir
        mapping_io.mappings_dir = lambda: self.tmp

    def tearDown(self):
        mapping_io.mappings_dir = self._orig
        shutil.rmtree(self.tmp, ignore_errors=True)

    def test_plain_name(self):
        p = mapping_io.mapping_file_path("example")
        self.assertTrue(p.endswith("example.json"))

    def test_name_with_ext(self):
        p = mapping_io.mapping_file_path("example.json")
        self.assertTrue(p.endswith("example.json"))

    def test_empty(self):
        with self.assertRaises(MappingPathError):
            mapping_io.mapping_file_path("")

    def test_forward_slash(self):
        with self.assertRaises(MappingPathError):
            mapping_io.mapping_file_path("../evil")

    def test_backslash(self):
        with self.assertRaises(MappingPathError):
            mapping_io.mapping_file_path("..\\evil")

    def test_absolute(self):
        with self.assertRaises(MappingPathError):
            mapping_io.mapping_file_path("C:\\evil")

    def test_subdir(self):
        with self.assertRaises(MappingPathError):
            mapping_io.mapping_file_path("sub/x")

    def test_stays_under_mappings(self):
        p = mapping_io.mapping_file_path("ok")
        self.assertTrue(
            os.path.realpath(p).startswith(
                os.path.realpath(self.tmp) + os.sep))

    def test_load_valid(self):
        with open(os.path.join(self.tmp, "ex.json"), "w",
                  encoding="utf-8") as f:
            f.write('["1000:2000", "1001"]')
        data = mapping_io.load_mapping_file("ex")
        self.assertEqual(data, ["1000:2000", "1001"])

    def test_load_missing(self):
        with self.assertRaises(FileNotFoundError):
            mapping_io.load_mapping_file("nope")

    def test_load_bad_json(self):
        with open(os.path.join(self.tmp, "bad.json"), "w") as f:
            f.write("{not json")
        with self.assertRaises(MappingFormatError):
            mapping_io.load_mapping_file("bad")

    def test_load_not_array(self):
        with open(os.path.join(self.tmp, "obj.json"), "w",
                  encoding="utf-8") as f:
            f.write('{"a": 1}')
        with self.assertRaises(MappingFormatError):
            mapping_io.load_mapping_file("obj")

    def test_load_non_utf8(self):
        with open(os.path.join(self.tmp, "latin1.json"), "wb") as f:
            f.write(b'["1000"]\xff')
        with self.assertRaises(MappingFormatError):
            mapping_io.load_mapping_file("latin1")


if __name__ == "__main__":
    unittest.main()