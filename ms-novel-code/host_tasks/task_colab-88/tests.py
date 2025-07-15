# tests


# test_server_full.py

import importlib.util
import os
import socket
import threading
import time
import unittest

# dynamically load our implementation from main.py (or server.py)
MODULE_PATH = os.path.join(os.getcwd(), "main.py")  # adjust if your file is named server.py
spec = importlib.util.spec_from_file_location("app", MODULE_PATH)
app = importlib.util.module_from_spec(spec)
spec.loader.exec_module(app)


class FullServerTest(unittest.TestCase):
    def setUp(self):
        # pick an ephemeral port
        listener = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        listener.bind(("127.0.0.1", 0))
        self.host, self.port = listener.getsockname()
        listener.close()

        # start the server in its own thread
        self.server_thread = threading.Thread(
            target=app.start_server,
            args=(self.host, self.port),
            daemon=True
        )
        self.server_thread.start()

        # give it a moment to bind & listen
        time.sleep(0.1)

    def tearDown(self):
        # if it's still running, trigger shutdown
        if self.server_thread.is_alive():
            try:
                s = socket.create_connection((self.host, self.port), timeout=1)
                s.sendall(b"quit_server\n")
                s.close()
            except Exception:
                pass
            # wait at most 1s for it to finish
            self.server_thread.join(timeout=1)

    def _connect(self):
        return socket.create_connection((self.host, self.port), timeout=1)

    def test_echo_and_client_shutdown(self):
        s = self._connect()
        r = s.makefile("r", encoding="utf-8")
        w = s.makefile("w", encoding="utf-8")

        # normal echo
        w.write("hello world\n")
        w.flush()
        self.assertEqual(r.readline(), "ACK: hello world\n")

        # per-client shutdown should close only this socket
        w.write("shutdown\n")
        w.flush()
        time.sleep(0.05)
        self.assertEqual(r.readline(), "")  # EOF
        s.close()

    def test_empty_line(self):
        s = self._connect()
        r = s.makefile("r", encoding="utf-8")
        w = s.makefile("w", encoding="utf-8")

        w.write("\n")
        w.flush()
        self.assertEqual(r.readline(), "ACK: \n")

        w.write("shutdown\n")
        w.flush()
        s.close()

    def test_global_quit_server(self):
        # open two clients
        s1 = self._connect()
        s2 = self._connect()
        r1 = s1.makefile("r", encoding="utf-8")
        w1 = s1.makefile("w", encoding="utf-8")
        r2 = s2.makefile("r", encoding="utf-8")
        w2 = s2.makefile("w", encoding="utf-8")

        # trigger full shutdown
        w1.write("quit_server\n")
        w1.flush()

        # both should see EOF
        time.sleep(0.05)
        self.assertEqual(r1.readline(), "")
        self.assertEqual(r2.readline(), "")

        # wait for server thread to exit
        self.server_thread.join(timeout=1)
        self.assertFalse(self.server_thread.is_alive())

        s1.close()
        s2.close()

    def test_malformed_utf8_closes_client(self):
        s = self._connect()
        # send invalid UTF-8
        s.sendall(b"\xff\xfe\xfd\n")
        # server should detect decode error and close that socket
        time.sleep(0.05)
        data = s.recv(1024)
        self.assertEqual(data, b"")  # closed, no data
        s.close()


if __name__ == "__main__":
    unittest.main()
