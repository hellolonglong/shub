# 文件名: tools/telnet_bridge/__main__.py
"""Allow `python -m telnet_bridge`."""

import sys

from .main import main

if __name__ == "__main__":
    sys.exit(main())