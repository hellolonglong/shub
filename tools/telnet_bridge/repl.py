# 文件名: tools/telnet_bridge/repl.py
"""Interactive shell: trans / list / remove / help / exit.

Parsing lives in trans_parser / remove_parser. This file only
dispatches commands and manages mappings.
"""

import logging
import shlex
import threading

from .mapping import Mapping
from .mapping_io import (
    load_mapping_file, MappingFormatError, MappingPathError,
)
from .remove_parser import parse_remove
from .trans_parser import parse_trans

log = logging.getLogger("telnet_bridge")


TRANS_HELP = """\
  trans <shub_port> [to <bridge_port>]
    Add a mapping: listen on <bridge_port> (or shub_port + offset)
    and forward to <target_host>:<shub_port>.
    Examples:
      trans 1000
      trans 1000 to 3000

  trans --from <name>
    Load mappings from mappings/<name>.json.
    <name> must be a plain file name; the .json suffix is optional.
    Example file content:
      ["1000:2000", "1001", "1002:3000"]
"""


REMOVE_HELP = """\
  remove <bridge_port>
    Stop and remove the mapping whose BRIDGE port matches.
    Use the left column of 'list' as the argument.

  remove all
    Stop and remove every mapping.
"""


LIST_HELP = """\
  list
    Show all mappings: BRIDGE port, TARGET, STATUS, CLIENTS.
"""


class BridgeRepl:
    def __init__(self, cfg, config_path=""):
        self.cfg = cfg
        self.config_path = config_path
        self.mappings = {}
        self._lock = threading.Lock()
        self._dispatch = {
            "help": "_handle_help",
            "trans": "_handle_trans",
            "list": "_handle_list",
            "remove": "_handle_remove",
        }

    # ---------- lookup ----------

    def _find_by_bridge_port(self, bridge_port):
        with self._lock:
            return self.mappings.get(bridge_port)

    def _find_by_shub_port(self, shub_port):
        with self._lock:
            for m in self.mappings.values():
                if m.target_port == shub_port:
                    return m
        return None

    # ---------- mapping lifecycle ----------

    def _start_mapping(self, shub_port, bridge_port=None):
        existing = self._find_by_shub_port(shub_port)
        if existing:
            print(f"  error: shub_port {shub_port} is already mapped to "
                  f"bridge port {existing.bridge_port}")
            print(f"    Use 'remove {existing.bridge_port}' first.")
            return False

        if bridge_port is None:
            bridge_port = shub_port + self.cfg["offset"]
            if bridge_port > 65535:
                print(f"  error: bridge_port {bridge_port} exceeds 65535 "
                      f"(shub_port {shub_port} + offset "
                      f"{self.cfg['offset']}); "
                      f"specify 'to <bridge_port>' explicitly.")
                return False

        if self._find_by_bridge_port(bridge_port):
            print(f"  error: bridge port {bridge_port} already mapped")
            return False

        mapping = Mapping(
            bridge_port, self.cfg["target_host"], shub_port,
            self.cfg["bind_addr"])
        try:
            mapping.start()
        except RuntimeError as e:
            print(f"  error: {e}")
            return False

        with self._lock:
            self.mappings[bridge_port] = mapping
        print(f"  started: listen {self.cfg['bind_addr']}:{bridge_port}"
              f" -> {self.cfg['target_host']}:{shub_port}")
        return True

    def _parse_mapping_token(self, token):
        """Parse "shub" or "shub:bridge". Returns (shub, bridge|None) or None."""
        if ":" in token:
            parts = token.split(":", 1)
            try:
                shub = int(parts[0])
                bridge = int(parts[1])
            except ValueError:
                return None
            if not (1 <= shub <= 65535 and 1 <= bridge <= 65535):
                return None
            return shub, bridge
        try:
            shub = int(token)
        except ValueError:
            return None
        if not (1 <= shub <= 65535):
            return None
        return shub, None

    def _load_mappings(self, tokens):
        ok = failed = 0
        for token in tokens:
            if not isinstance(token, str):
                print(f"  error: invalid mapping item: {token!r}")
                failed += 1
                continue
            parsed = self._parse_mapping_token(token)
            if parsed is None:
                print(f"  error: invalid mapping: {token!r}")
                failed += 1
                continue
            shub, bridge = parsed
            if self._start_mapping(shub, bridge):
                ok += 1
            else:
                failed += 1
        return ok, failed

    # ---------- command handlers ----------

    def _handle_help(self, parts):
        if parts:
            print("  error: 'help' takes no arguments.")
            return
        print("""
  Commands:
    trans <shub_port> [to <bridge_port>]   Add a mapping
    trans --from <name>                    Load mappings from mappings/<name>.json
    list                                   Show all mappings
    remove <bridge_port> | all             Stop and remove a mapping
    help                                   Show this message
    exit                                   Stop all mappings and quit

  Notes:
    - <shub_port> is the port shub listens on.
    - <bridge_port> is the port this tool listens on.
    - If <bridge_port> is omitted, it defaults to shub_port + offset.
    - 'remove' takes the BRIDGE port (left column of 'list'),
      not the shub port.
    - Mapping files must live under mappings/ and be referenced by
      plain file name only (no paths).
""")

    def _handle_list(self, parts):
        if parts:
            print("  error: 'list' takes no arguments.")
            return
        with self._lock:
            mappings = list(self.mappings.values())
        if not mappings:
            print("  (no mappings)")
            return
        print(f"  {'BRIDGE':<10} {'TARGET':<24} {'STATUS':<10} CLIENTS")
        for m in mappings:
            target = f"{m.target_host}:{m.target_port}"
            print(f"  {m.bridge_port:<10} {target:<24} "
                  f"{'running':<10} {m.client_count()}")
        print()
        print("  Use 'remove <BRIDGE>' to stop a mapping.")

    def _handle_trans(self, parts):
        cmd = parse_trans(parts)
        if cmd.mode == "help":
            print(TRANS_HELP)
            return
        if cmd.mode == "usage":
            print("  usage: trans <shub_port> [to <bridge_port>]")
            print("         trans --from <name>")
            return
        if cmd.mode == "error":
            print(f"  error: {cmd.error}")
            return
        if cmd.mode == "from":
            self._load_from_mapping_file(cmd.file_name)
            return
        if cmd.mode == "one":
            self._start_mapping(cmd.shub_port, cmd.bridge_port)
            return

    def _load_from_mapping_file(self, name):
        try:
            data = load_mapping_file(name)
        except FileNotFoundError as e:
            print(f"  error: {e}")
            print(f"    Mapping files live under mappings/. "
                  f"Use a plain name, e.g. 'trans --from example'.")
            return
        except MappingPathError as e:
            print(f"  error: {e}")
            print(f"    Use a plain file name under mappings/, "
                  f"e.g. 'trans --from example'.")
            return
        except MappingFormatError as e:
            print(f"  error: {e}")
            return
        except OSError as e:
            print(f"  error: {e}")
            return

        self._load_mappings(data)

    def _handle_remove(self, parts):
        cmd = parse_remove(parts)
        if cmd.mode == "help":
            print(REMOVE_HELP)
            return
        if cmd.mode == "usage":
            print("  usage: remove <bridge_port> | all")
            return
        if cmd.mode == "error":
            print(f"  error: {cmd.error}")
            return
        if cmd.mode == "all":
            self._remove_all()
            return
        if cmd.mode == "one":
            self._remove_one(cmd.bridge_port)
            return

    def _remove_all(self):
        with self._lock:
            mappings = list(self.mappings.values())
            self.mappings.clear()
        if not mappings:
            print("  (no mappings)")
            return
        for m in mappings:
            try:
                m.stop()
            except Exception:
                pass
        print(f"  stopped {len(mappings)} mapping(s)")

    def _remove_one(self, bridge_port):
        mapping = self._find_by_bridge_port(bridge_port)
        if mapping:
            with self._lock:
                self.mappings.pop(bridge_port, None)
            mapping.stop()
            print(f"  stopped: bridge port {bridge_port}")
            return

        shub_mapping = self._find_by_shub_port(bridge_port)
        if shub_mapping:
            print(f"  error: {bridge_port} is a shub_port, "
                  f"not a bridge_port.")
            print(f"    It is mapped to bridge port "
                  f"{shub_mapping.bridge_port}.")
            print(f"    Use: remove {shub_mapping.bridge_port}")
            return

        print(f"  error: no mapping on bridge port {bridge_port}")

    # ---------- main loop ----------

    def _handle(self, line):
        line = line.strip()
        if not line:
            return True
        try:
            parts = shlex.split(line)
        except ValueError as e:
            print(f"  syntax error: {e}")
            return True

        head = parts[0].lower()
        rest = parts[1:]

        if head in ("exit", "quit"):
            if rest:
                print(f"  error: '{head}' takes no arguments.")
                return True
            return False

        handler_name = self._dispatch.get(head)
        if not handler_name:
            print(f"  error: unknown command '{head}'. Type 'help'.")
            return True

        getattr(self, handler_name)(rest)
        return True

    # ---------- startup ----------

    def _auto_start(self):
        tokens = self.cfg.get("mappings") or []
        if not tokens:
            return
        print(f"  AutoTrans: on, loading {len(tokens)} mapping(s)...")
        ok, failed = self._load_mappings(tokens)
        if failed:
            print(f"  auto-loaded {ok}, failed {failed}")
        else:
            print(f"  auto-loaded {ok}")

    def run(self):
        print("telnet_bridge v0.1")
        if self.config_path:
            print(f"  config: {self.config_path}")
        print(f"  bind_addr: {self.cfg['bind_addr']}")
        print(f"  target_host: {self.cfg['target_host']}")
        print(f"  offset: {self.cfg['offset']}")
        print(f"  AutoTrans: {'on' if self.cfg.get('AutoTrans') else 'off'}")
        print()

        if self.cfg.get("AutoTrans"):
            self._auto_start()
        else:
            print("No mappings. Use 'trans <shub_port> [to <bridge_port>]' "
                  "to add one.")
            print("Type 'help' for commands.")
        print()

        while True:
            try:
                line = input("telnet_bridge> ")
            except (EOFError, KeyboardInterrupt):
                print()
                break
            try:
                if not self._handle(line):
                    break
            except Exception as e:
                print(f"  error: {e}")
                log.error("repl command failed: %s", e, exc_info=True)

        with self._lock:
            mappings = list(self.mappings.values())
            self.mappings.clear()
        for m in mappings:
            try:
                m.stop()
            except Exception:
                pass
        if mappings:
            print(f"  stopped {len(mappings)} mapping(s)")
        print("[telnet_bridge] Bye")