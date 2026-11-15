# 文件名: tools/telnet_bridge/main.py
"""Entry: load config, run the interactive shell.

--config accepts an arbitrary path (admin-explicit startup choice).
trans --from only accepts a plain file name under mappings/.
"""

import argparse
import logging
import os
import sys

from .config import load_config
from .repl import BridgeRepl


def main(argv=None):
    parser = argparse.ArgumentParser(
        prog="telnet_bridge",
        description="Telnet compatibility layer for shub.")
    parser.add_argument(
        "--config", default=None,
        help="path to bridge_config.json "
             "(default: conf/bridge_config.json next to this package)")
    args = parser.parse_args(argv)

    logging.basicConfig(
        level=logging.WARNING,
        format="%(asctime)s [%(levelname)s] %(message)s",
    )

    cfg_path = args.config
    if cfg_path is None:
        cfg_path = os.path.join(
            os.path.dirname(os.path.abspath(__file__)),
            "conf", "bridge_config.json")

    cfg, err = load_config(cfg_path)
    if err:
        print(f"warning: {err}, using defaults")

    BridgeRepl(cfg, cfg_path).run()
    return 0


if __name__ == "__main__":
    sys.exit(main())