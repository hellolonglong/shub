# 文件名: tools/telnet_bridge/mapping.py
"""One listen->target mapping: listening socket + per-client bridges.

Idle ticks clean up inactive clients so _clients does not grow
indefinitely when clients come and go.
"""

import logging
import socket
import threading

from .bridge import Bridge

log = logging.getLogger("telnet_bridge")


class Mapping:
    def __init__(self, bridge_port, target_host, target_port,
                 bind_addr="0.0.0.0"):
        self.bridge_port = bridge_port
        self.target_host = target_host
        self.target_port = target_port
        self.bind_addr = bind_addr
        self._server = None
        self._running = False
        self._thread = None
        self._clients = []
        self._lock = threading.Lock()

    def start(self):
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        try:
            sock.bind((self.bind_addr, self.bridge_port))
            sock.listen(5)
        except OSError as e:
            try:
                sock.close()
            except Exception:
                pass
            raise RuntimeError(
                f"cannot listen on {self.bind_addr}:{self.bridge_port}: {e}")

        sock.settimeout(0.5)
        self._server = sock
        self._running = True
        self._thread = threading.Thread(
            target=self._accept_loop, daemon=True)
        self._thread.start()

    def _cleanup_inactive(self):
        with self._lock:
            self._clients = [c for c in self._clients if c.is_active()]

    def _accept_loop(self):
        while self._running:
            try:
                conn, addr = self._server.accept()
            except socket.timeout:
                self._cleanup_inactive()
                continue
            except OSError:
                break

            label = f"{addr[0]}:{addr[1]}"
            client = Bridge(conn, label, self.target_host, self.target_port)
            with self._lock:
                self._clients.append(client)
            log.info("bridge %d: client %s connected",
                     self.bridge_port, label)
            client.start()

    def client_count(self):
        with self._lock:
            return len([c for c in self._clients if c.is_active()])

    def stop(self):
        self._running = False
        if self._server:
            try:
                self._server.close()
            except Exception:
                pass
        if self._thread:
            self._thread.join(timeout=1)
            self._thread = None
        with self._lock:
            clients = list(self._clients)
            self._clients.clear()
        for c in clients:
            try:
                c.close()
            except Exception:
                pass