# 文件名: tools/telnet_bridge/mapping_io.py
"""Resolve mapping file names under mappings/ and load them.

Names are file-name only: no path separators, no "..", no absolute
paths. Final path is validated to stay under mappings/ after resolving
symlinks and "..".

Errors:
- MappingPathError: file name violates path rules.
- MappingFormatError: file exists but is not a valid mapping file.
- FileNotFoundError: file does not exist.
- OSError: file exists but cannot be read.
"""

import json
import os

PROFILE_EXT = ".json"


class MappingPathError(ValueError):
    """File name violates path rules."""


class MappingFormatError(ValueError):
    """File exists but is not a valid mapping file."""


def mappings_dir():
    return os.path.join(
        os.path.dirname(os.path.abspath(__file__)), "mappings")


def _reject_path_components(name):
    if not name:
        raise MappingPathError("empty file name")
    if "/" in name or "\\" in name:
        raise MappingPathError(
            f"invalid mapping file name: {name!r}. "
            "Path separators are not allowed.")
    if ".." in name:
        raise MappingPathError(
            f"invalid mapping file name: {name!r}. "
            "'..' is not allowed.")
    if os.path.isabs(name):
        raise MappingPathError(
            f"invalid mapping file name: {name!r}. "
            "Absolute paths are not allowed.")


def mapping_file_path(name):
    name = (name or "").strip()
    _reject_path_components(name)
    if not name.lower().endswith(PROFILE_EXT):
        name += PROFILE_EXT
    base = os.path.realpath(mappings_dir())
    full = os.path.realpath(os.path.join(base, name))
    if not (full == base or full.startswith(base + os.sep)):
        raise MappingPathError(
            f"path escapes mappings directory: {name!r}")
    return full


def load_mapping_file(name):
    """Return the list of mapping tokens. Raises on errors."""
    path = mapping_file_path(name)
    if not os.path.exists(path):
        raise FileNotFoundError(f"mapping file not found: {path}")

    try:
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
    except json.JSONDecodeError as e:
        raise MappingFormatError(f"invalid JSON in {path}: {e}")
    except UnicodeError as e:
        raise MappingFormatError(
            f"mapping file is not valid UTF-8: {path}: {e}")
    except OSError as e:
        raise OSError(f"cannot read {path}: {e}")

    if not isinstance(data, list):
        raise MappingFormatError(
            f"mapping file must contain a JSON array: {path}")
    return data