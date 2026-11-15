# 文件名: tools/telnet_bridge/bridge.py
"""One client: MobaXterm Telnet side <-> shub side."""

import logging
import socket
import threading

from .telnet_parser import TelnetParser

log = logging.getLogger("telnet_bridge")


def _enable_keepalive(sock):
    try:
        sock.setsockopt(socket.SOL_SOCKET, socket.SO_KEEPALIVE, 1)
    except OSError:
        pass


class Bridge:
    def __init__(self, client_conn, client_label, target_host, target_port):
        self.client_conn = client_conn
        self.client_label = client_label
        self.target_host = target_host
        self.target_port = target_port
        self._target_conn = None
        self._running = True
        self._parser = TelnetParser()
        self._closed = False
        self._close_lock = threading.Lock()

    def start(self):
        _enable_keepalive(self.client_conn)
        try:
            self._target_conn = socket.create_connection(
                (self.target_host, self.target_port), timeout=3)
            self._target_conn.settimeout(None)
            _enable_keepalive(self._target_conn)
        except OSError as e:
            log.warning("Bridge %s: cannot connect to %s:%d: %s",
                        self.client_label, self.target_host,
                        self.target_port, e)
            self._running = False
            self.close()
            return

        t1 = threading.Thread(target=self._client_to_target, daemon=True)
        t2 = threading.Thread(target=self._target_to_client, daemon=True)
        t1.start()
        t2.start()

    def is_active(self):
        return self._running

    def _client_to_target(self):
        try:
            while self._running:
                data = self.client_conn.recv(1024)
                if not data:
                    break
                to_target, replies = self._parser.feed(data)
                if replies:
                    try:
                        self.client_conn.sendall(replies)
                    except OSError:
                        break
                if to_target and self._target_conn:
                    try:
                        self._target_conn.sendall(to_target)
                    except OSError:
                        break
        except OSError:
            pass
        finally:
            self._running = False
            self.close()

    def _target_to_client(self):
        try:
            while self._running:
                data = self._target_conn.recv(1024)
                if not data:
                    break
                self.client_conn.sendall(data)
        except OSError:
            pass
        finally:
            self._running = False
            self.close()

    def close(self):
        with self._close_lock:
            if self._closed:
                return
            self._closed = True
        self._running = False
        if self._target_conn:
            try:
                self._target_conn.close()
            except Exception:
                pass
        try:
            self.client_conn.close()
        except Exception:
            pass