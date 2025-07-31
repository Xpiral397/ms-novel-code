
#!/usr/bin/env python3
"""
server.py

A simple, scalable, multi-threaded TCP server that cleanly shuts down
when any client sends "quit_server".

Usage:
    python server.py 127.0.0.1 8000

Test with netcat:
    nc 127.0.0.1 8000
    hello           → ACK: hello
    shutdown        → closes only your connection

Test with telnet:
    telnet 127.0.0.1 8000
    quit_server     → shuts down entire server
"""

import logging
import socket
import sys
import threading
from typing import List, Tuple

BACKLOG = 100
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s"
)


class ClientHandler(threading.Thread):
    """
    Handle a single client connection in its own thread.

    Echo messages with "ACK: ". Close on "shutdown".
    Trigger full server shutdown on "quit_server".
    """

    def __init__(
        self,
        conn: socket.socket,
        addr: Tuple[str, int],
        shutdown_event: threading.Event
    ) -> None:
        super().__init__()  # non-daemon so we can join on shutdown
        self.conn = conn
        self.addr = addr
        self.shutdown_event = shutdown_event

    def run(self) -> None:
        logging.info("Client connected %s:%d", *self.addr)
        try:
            with self.conn:
                reader = self.conn.makefile("r", encoding="utf-8", newline="\n")
                writer = self.conn.makefile("w", encoding="utf-8", newline="\n")

                for line in reader:
                    if self.shutdown_event.is_set():
                        break

                    msg = line.rstrip("\n")

                    if msg == "shutdown":
                        logging.info("Closing connection to %s:%d", *self.addr)
                        break

                    if msg == "quit_server":
                        logging.info("Shutdown requested by %s:%d", *self.addr)
                        self.shutdown_event.set()
                        break

                    writer.write(f"ACK: {msg}\n")
                    writer.flush()
        except Exception as exc:
            logging.warning("Error with %s:%d: %s", *self.addr, exc)
        finally:
            try:
                self.conn.shutdown(socket.SHUT_RDWR)
            except Exception:
                pass
            self.conn.close()
            logging.info("Client disconnected %s:%d", *self.addr)


def _accept_loop(
    server_sock: socket.socket,
    shutdown_event: threading.Event,
    threads: List[threading.Thread]
) -> None:
    """
    Accept new connections until shutdown_event is set.
    Immediately re-check after each accept to avoid the shutdown race.
    """
    server_sock.settimeout(1.0)

    while not shutdown_event.is_set():
        try:
            conn, addr = server_sock.accept()
        except socket.timeout:
            continue
        except OSError:
            break

        if shutdown_event.is_set():
            conn.close()
            break

        handler = ClientHandler(conn, addr, shutdown_event)
        handler.start()
        threads.append(handler)


def start_server(host: str, port: int) -> None:
    """
    Start the TCP server on the given host and port.
    Blocks until a client sends "quit_server".
    """
    shutdown_event = threading.Event()
    threads: List[threading.Thread] = []

    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as srv:
        srv.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        srv.bind((host, port))
        srv.listen(BACKLOG)
        logging.info("Server listening on %s:%d", host, port)

        try:
            _accept_loop(srv, shutdown_event, threads)
        finally:
            # signal all handlers to stop, close listening socket, wait for threads
            shutdown_event.set()
            srv.close()
            for t in threads:
                t.join()
            logging.info("Server shutdown complete")


if __name__ == "__main__":
    if len(sys.argv) != 3:
        print("Usage: python server.py <host> <port>")
        sys.exit(1)

    try:
        host_arg = sys.argv[1]
        port_arg = int(sys.argv[2])
    except ValueError:
        print("Port must be an integer.")
        sys.exit(1)

    start_server(host_arg, port_arg)

