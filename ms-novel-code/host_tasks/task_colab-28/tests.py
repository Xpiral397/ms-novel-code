# tests

# test.py

import unittest
import os
import json
import tempfile
import shutil
import threading
import http.client
import time
import socket
import sys

import main  # assumes your implementation is in main.py

# Helper to find an available port
def find_free_port():
    s = socket.socket()
    s.bind(('localhost', 0))
    port = s.getsockname()[1]
    s.close()
    return port

class TestEventLogger(unittest.TestCase):
    def setUp(self):
        self.tmpdir = tempfile.mkdtemp()
        self.logger = main.EventLogger(self.tmpdir)

    def tearDown(self):
        shutil.rmtree(self.tmpdir)

    def test_append_and_verify_success(self):
        payload = {"event": "user.created", "data": {"id": 1}}
        eid = self.logger.append(payload)

        # Check events.jsonl
        ev_file = os.path.join(self.tmpdir, 'events.jsonl')
        with open(ev_file, 'r', encoding='utf-8') as f:
            lines = f.read().splitlines()
        self.assertEqual(len(lines), 1)
        rec = json.loads(lines[0])
        self.assertIn('ts', rec)
        self.assertEqual(rec['payload'], payload)

        # Check audit.log
        au_file = os.path.join(self.tmpdir, 'audit.log')
        with open(au_file, 'r', encoding='utf-8') as f:
            lines = f.read().splitlines()
        self.assertEqual(len(lines), 1)
        chain, logged_eid = lines[0].split(' ')
        self.assertEqual(logged_eid, eid)

        # verify should be True
        self.assertTrue(self.logger.verify())

    def test_tamper_audit_detected(self):
        eid = self.logger.append({"event": "test"})
        au_file = os.path.join(self.tmpdir, 'audit.log')
        with open(au_file, 'r+', encoding='utf-8') as f:
            data = f.read()
            f.seek(0)
            f.write('X' + data[1:])
            f.truncate()
        self.assertFalse(self.logger.verify())

    def test_invalid_event_payloads(self):
        with self.assertRaises(TypeError):
            self.logger.append(123)
        with self.assertRaises(ValueError):
            self.logger.append({})            # missing event
        with self.assertRaises(ValueError):
            self.logger.append({'event': ''})
        long_event = 'a' * 256
        with self.assertRaises(ValueError):
            self.logger.append({'event': long_event})

class TestHTTPServer(unittest.TestCase):
    def setUp(self):
        self.tmpdir = tempfile.mkdtemp()
        self.port = find_free_port()
        server = http.server.ThreadingHTTPServer(('localhost', self.port), main.WebhookHandler)
        main.WebhookHandler.logger = main.EventLogger(self.tmpdir)
        self.server = server
        self.thread = threading.Thread(target=server.serve_forever)
        self.thread.daemon = True
        self.thread.start()
        time.sleep(0.1)

    def tearDown(self):
        self.server.shutdown()
        self.thread.join()
        shutil.rmtree(self.tmpdir)

    def http_post(self, body, headers):
        conn = http.client.HTTPConnection('localhost', self.port)
        conn.request('POST', '/webhook', body, headers)
        resp = conn.getresponse()
        data = resp.read().decode('utf-8')
        conn.close()
        return resp.status, data

    def test_http_success(self):
        body = json.dumps({'event': 'ping', 'data': {}})
        status, data = self.http_post(
            body,
            {'Content-Type': 'application/json', 'Content-Length': str(len(body))}
        )
        self.assertEqual(status, 200)
        obj = json.loads(data)
        self.assertIn('id', obj)
        self.assertTrue(main.WebhookHandler.logger.verify())

    def test_http_not_found(self):
        status, _ = self.http_post(
            '{}',
            {'Content-Type': 'application/json', 'Content-Length': '2'}
        )
        self.assertEqual(status, 404)

    def test_http_bad_content_type(self):
        body = json.dumps({'event': 'ping'})
        status, data = self.http_post(
            body,
            {'Content-Type': 'text/plain', 'Content-Length': str(len(body))}
        )
        self.assertEqual(status, 415)
        self.assertIn('error', json.loads(data))

    def test_http_payload_too_large(self):
        body = 'x' * (main._MAX_BODY_BYTES + 1)
        status, _ = self.http_post(
            body,
            {'Content-Type': 'application/json', 'Content-Length': str(len(body))}
        )
        self.assertEqual(status, 413)

    def test_http_invalid_json(self):
        status, _ = self.http_post(
            '{not json}',
            {'Content-Type': 'application/json', 'Content-Length': '10'}
        )
        self.assertEqual(status, 400)

class TestCLI(unittest.TestCase):
    def setUp(self):
        self.tmpdir = tempfile.mkdtemp()

    def tearDown(self):
        shutil.rmtree(self.tmpdir)

    def test_verify_exit_code(self):
        # no events-> exit 0
        with self.assertRaises(SystemExit) as cm:
            main._verify(self.tmpdir)
        self.assertEqual(cm.exception.code, 0)

        # tamper-> exit non-zero
        logger = main.EventLogger(self.tmpdir)
        eid = logger.append({'event': 'e'})
        audit = os.path.join(self.tmpdir, 'audit.log')
        with open(audit, 'r+', encoding='utf-8') as f:
            data = f.read(); f.seek(0); f.write('X'+data[1:]); f.truncate()
        with self.assertRaises(SystemExit) as cm2:
            main._verify(self.tmpdir)
        self.assertNotEqual(cm2.exception.code, 0)

if __name__ == '__main__':
    unittest.main()
