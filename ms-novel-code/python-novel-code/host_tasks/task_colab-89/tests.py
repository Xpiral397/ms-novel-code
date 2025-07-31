# tests

import unittest
import tempfile
import os
import json
from main import log_webhook_event

class TestLogWebhookEvent(unittest.TestCase):
    def setUp(self):
        self.tempdir = tempfile.TemporaryDirectory()
        self.original_cwd = os.getcwd()
        os.chdir(self.tempdir.name)

    def tearDown(self):
        os.chdir(self.original_cwd)
        self.tempdir.cleanup()

    def test_payload_length_too_short(self):
        short_payload = '{}'  # length < 10
        result = log_webhook_event(short_payload)
        self.assertEqual(result, -1)
        self.assertFalse(os.path.exists('webhook_audit_log.json'))

    def test_payload_length_too_long(self):
        long_payload = '"' + 'a' * 499 + '"'  # total length 501
        result = log_webhook_event(long_payload)
        self.assertEqual(result, -1)
        self.assertFalse(os.path.exists('webhook_audit_log.json'))

    def test_file_missing_returns_error(self):
        if os.path.exists('webhook_audit_log.json'):
            os.remove('webhook_audit_log.json')
        valid_payload = json.dumps({
            "event_id": "3fa85f64-5717-4562-b3fc-2c963f66afa6",
            "event_type": "user.created",
            "timestamp": "2020-01-01T00:00:00Z",
            "source": {"ip": "192.168.1.1", "user_agent": "Mozilla"},
            "payload": {
                "user": {"id": 101, "email": "user@example.com"},
                "metadata": {"priority": "low"}
            }
        })
        result = log_webhook_event(valid_payload)
        self.assertEqual(result, -1)
        self.assertFalse(os.path.exists('webhook_audit_log.json'))

    def test_valid_event_logged(self):
        with open('webhook_audit_log.json', 'w') as f:
            f.write('[]')
        payload = json.dumps({
            "event_id": "11111111-1111-1111-1111-111111111111",
            "event_type": "payment.failed",
            "timestamp": "2025-01-01T00:00:00Z",
            "source": {"ip": "10.0.0.1", "user_agent": "TestAgent"},
            "payload": {
                "user": {"id": 42, "email": "foo@bar.com"},
                "metadata": {"priority": "medium"}
            }
        })
        result = log_webhook_event(payload)
        self.assertEqual(result, "Logged")
        with open('webhook_audit_log.json') as f:
            data = json.load(f)
        self.assertEqual(len(data), 1)
        self.assertEqual(data[0]["event_id"], "11111111-1111-1111-1111-111111111111")
        self.assertEqual(data[0]["payload"]["metadata"]["priority"], "medium")

    def test_duplicate_event_id(self):
        with open('webhook_audit_log.json', 'w') as f:
            json.dump([{"event_id": "22222222-2222-2222-2222-222222222222"}], f)
        payload = json.dumps({
            "event_id": "22222222-2222-2222-2222-222222222222",
            "event_type": "user.created",
            "timestamp": "2024-01-01T00:00:00Z",
            "source": {"ip": "127.0.0.1", "user_agent": "Agent"},
            "payload": {
                "user": {"id": 1, "email": "x@y.com"},
                "metadata": {"priority": "high"}
            }
        })
        result = log_webhook_event(payload)
        self.assertEqual(result, "Duplicate event")
        with open('webhook_audit_log.json') as f:
            data = json.load(f)
        self.assertEqual(len(data), 1)

    def test_missing_priority(self):
        with open('webhook_audit_log.json', 'w') as f:
            f.write('[]')
        payload = json.dumps({
            "event_id": "33333333-3333-3333-3333-333333333333",
            "event_type": "user.created",
            "timestamp": "2023-01-01T00:00:00Z",
            "source": {"ip": "1.2.3.4", "user_agent": "UA"},
            "payload": {
                "user": {"id": 2, "email": "test@test.com"},
                "metadata": {}
            }
        })
        result = log_webhook_event(payload)
        self.assertEqual(result, "Bad payload")
        with open('webhook_audit_log.json') as f:
            data = json.load(f)
        self.assertEqual(len(data), 0)

    def test_invalid_timestamp_future(self):
        with open('webhook_audit_log.json', 'w') as f:
            f.write('[]')
        future_time = "2100-01-01T00:00:00Z"
        payload = json.dumps({
            "event_id": "44444444-4444-4444-4444-444444444444",
            "event_type": "payment.failed",
            "timestamp": future_time,
            "source": {"ip": "8.8.8.8", "user_agent": "UA"},
            "payload": {
                "user": {"id": 3, "email": "a@b.com"},
                "metadata": {"priority": "low"}
            }
        })
        result = log_webhook_event(payload)
        self.assertEqual(result, "Invalid timestamp")
        with open('webhook_audit_log.json') as f:
            data = json.load(f)
        self.assertEqual(len(data), 0)

    def test_invalid_ip_format(self):
        with open('webhook_audit_log.json', 'w') as f:
            f.write('[]')
        payload = json.dumps({
            "event_id": "55555555-5555-5555-5555-555555555555",
            "event_type": "user.created",
            "timestamp": "2020-01-01T00:00:00Z",
            "source": {"ip": "999.999.999.999", "user_agent": "UA"},
            "payload": {
                "user": {"id": 4, "email": "test@e.com"},
                "metadata": {"priority": "medium"}
            }
        })
        result = log_webhook_event(payload)
        self.assertEqual(result, "Bad payload")
        with open('webhook_audit_log.json') as f:
            data = json.load(f)
        self.assertEqual(len(data), 0)

    def test_invalid_priority_value(self):
        with open('webhook_audit_log.json', 'w') as f:
            f.write('[]')
        payload = json.dumps({
            "event_id": "66666666-6666-6666-6666-666666666666",
            "event_type": "payment.failed",
            "timestamp": "2020-01-01T00:00:00Z",
            "source": {"ip": "127.0.0.1", "user_agent": "Agent"},
            "payload": {
                "user": {"id": 5, "email": "ok@ok.com"},
                "metadata": {"priority": "urgent"}
            }
        })
        result = log_webhook_event(payload)
        self.assertEqual(result, "Bad payload")
        with open('webhook_audit_log.json') as f:
            data = json.load(f)
        self.assertEqual(len(data), 0)

    def test_optional_tags_missing(self):
        with open('webhook_audit_log.json', 'w') as f:
            f.write('[]')
        payload = json.dumps({
            "event_id": "77777777-7777-7777-7777-777777777777",
            "event_type": "user.created",
            "timestamp": "2020-01-01T00:00:00Z",
            "source": {"ip": "123.123.123.123", "user_agent": "UA"},
            "payload": {
                "user": {"id": 6, "email": "tt@tt.com"},
                "metadata": {"priority": "high"}
            }
        })
        result = log_webhook_event(payload)
        self.assertEqual(result, "Logged")
        with open('webhook_audit_log.json') as f:
            data = json.load(f)
        self.assertNotIn("tags", data[0]["payload"]["metadata"])

    def test_tags_present(self):
        with open('webhook_audit_log.json', 'w') as f:
            f.write('[]')
        payload = json.dumps({
            "event_id": "99999999-9999-9999-9999-999999999999",
            "event_type": "payment.failed",
            "timestamp": "2025-01-01T00:00:00Z",
            "source": {"ip": "2.2.2.2", "user_agent": "UA"},
            "payload": {
                "user": {"id": 7, "email": "yes@yes.com"},
                "metadata": {"priority": "low", "tags": ["test", "sample"]}
            }
        })
        result = log_webhook_event(payload)
        self.assertEqual(result, "Logged")
        with open('webhook_audit_log.json') as f:
            data = json.load(f)
        self.assertEqual(data[0]["payload"]["metadata"]["tags"], ["test", "sample"])

    def test_malformed_json_file_resets(self):
        with open('webhook_audit_log.json', 'w') as f:
            f.write('not a json')
        payload = json.dumps({
            "event_id": "88888888-8888-8888-8888-888888888888",
            "event_type": "payment.failed",
            "timestamp": "2025-01-01T00:00:00Z",
            "source": {"ip": "1.1.1.1", "user_agent": "UA"},
            "payload": {
                "user": {"id": 7, "email": "mm@mm.com"},
                "metadata": {"priority": "low"}
            }
        })
        result = log_webhook_event(payload)
        self.assertEqual(result, "Logged")
        with open('webhook_audit_log.json') as f:
            data = json.load(f)
        self.assertEqual(len(data), 1)

if __name__ == '__main__':
    unittest.main(argv=[''])
