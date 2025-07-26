# tests
import unittest
from flask import Flask, Response, render_template_string, jsonify
from main import apply_advanced_secure_headers, get_current_nonce


class TestAdvancedSecureHeaders(unittest.TestCase):

    def _create_app(self, default_cfg=None, route_cfg=None):
        app = Flask(__name__)
        apply_advanced_secure_headers(app, default_cfg or {}, route_cfg or {})
        return app

    @staticmethod
    def _get_header(resp: Response, key: str) -> str | None:
        for k, v in resp.headers.items():
            if k.lower() == key.lower():
                return v
        return None

    def test_default_headers_applied(self):
        default_cfg = {
            'csp': {'default-src': ["'self'"]},
            'hsts': 86400,
            'x_content_type_options': True,
        }
        app = self._create_app(default_cfg)

        @app.route('/')
        def index():
            return 'ok'

        with app.test_client() as client:
            resp = client.get('/')
            self.assertEqual(self._get_header(
                resp, 'Strict-Transport-Security'), 'max-age=86400')
            self.assertIn("default-src 'self'",
                          self._get_header(resp, 'Content-Security-Policy'))
            self.assertEqual(self._get_header(
                resp, 'X-Content-Type-Options'), 'nosniff')

    def test_route_specific_override(self):
        default_cfg = {
            'csp': {'default-src': ["'self'"]},
            'hsts': 86400,
        }
        route_cfg = {
            '/public': {
                'csp': {'default-src': ["'self'", 'cdn.example.com']},
                'hsts': 0,
            }
        }
        app = self._create_app(default_cfg, route_cfg)

        @app.route('/public')
        def public():
            return 'pub'

        with app.test_client() as client:
            resp = client.get('/public')
            # When hsts == 0 the reference impl omits the header entirely.
            self.assertIsNone(self._get_header(
                resp, 'Strict-Transport-Security'))
            csp = self._get_header(resp, 'Content-Security-Policy')
            self.assertIn('cdn.example.com', csp)

    def test_nonce_available_and_in_header(self):
        default_cfg = {
            'csp': {'script-src': ["'self'", "'nonce-{nonce}'"]},
        }
        app = self._create_app(default_cfg)

        @app.route('/dash')
        def dash():
            nonce = get_current_nonce()
            return render_template_string("<html>{{ nonce }}</html>", nonce=nonce)

        with app.test_client() as client:
            first = client.get('/dash')
            nonce_1 = first.get_data(as_text=True)[6:-7]
            self.assertIn(nonce_1, self._get_header(
                first, 'Content-Security-Policy'))
            second = client.get('/dash')
            nonce_2 = second.get_data(as_text=True)[6:-7]
            self.assertNotEqual(nonce_1, nonce_2)

    def test_non_html_response_headers(self):
        app = self._create_app({'csp': {'default-src': ["'none'"]}})

        @app.route('/json')
        def jsn():
            return jsonify(ok=True)

        with app.test_client() as client:
            resp = client.get('/json')
            self.assertIsNotNone(self._get_header(
                resp, 'Content-Security-Policy'))

    def test_disable_csp_and_hsts(self):
        default_cfg = {'csp': {'default-src': ["'self'"]}, 'hsts': 86400}
        route_cfg = {'/nocsp': {'csp': None, 'hsts': 0}}
        app = self._create_app(default_cfg, route_cfg)

        @app.route('/nocsp')
        def nocsp():
            return 'n'

        with app.test_client() as client:
            resp = client.get('/nocsp')
            self.assertIsNone(self._get_header(
                resp, 'Content-Security-Policy'))
            self.assertIsNone(self._get_header(
                resp, 'Strict-Transport-Security'))

    def test_route_added_after_apply(self):
        app = Flask(__name__)
        apply_advanced_secure_headers(
            app, {'csp': {'default-src': ["'self'"]}})

        @app.route('/later')
        def later():
            return 'ok'

        with app.test_client() as client:
            resp = client.get('/later')
            self.assertIn("default-src 'self'",
                          self._get_header(resp, 'Content-Security-Policy'))

    def test_unknown_route_inherits_defaults(self):
        default_cfg = {'csp': {'default-src': ["'self'"]}}
        route_cfg = {'/special': {'csp': {'default-src': ["'none'"]}}}
        app = self._create_app(default_cfg, route_cfg)

        @app.route('/other')
        def other():
            return 'x'

        with app.test_client() as client:
            resp = client.get('/other')
            self.assertIn("'self'", self._get_header(
                resp, 'Content-Security-Policy'))

    def test_invalid_config_type_error(self):
        app = Flask(__name__)
        bad_default = {'csp': 'not-a-dict'}
        with self.assertRaises(TypeError):
            apply_advanced_secure_headers(app, bad_default)

    def test_idempotent_after_request_handlers(self):
        """Re-applying should not produce duplicate CSP headers in response."""
        app = Flask(__name__)
        apply_advanced_secure_headers(
            app, {'csp': {'default-src': ["'self'"]}})
        apply_advanced_secure_headers(
            app, {'csp': {'default-src': ["'self'"]}})  # second call

        @app.route('/dup')
        def dup():
            return 'ok'

        with app.test_client() as client:
            resp = client.get('/dup')
            self.assertEqual(
                len(resp.headers.getlist('Content-Security-Policy')), 1)

    def test_blueprint_level_override(self):
        """Blueprint‑scoped config overrides defaults for its routes."""
        from flask import Blueprint
        default_cfg = {'csp': {'default-src': ["'self'"]}, 'hsts': 0}
        bp_cfg = {'bp.index': {
            'csp': {'default-src': ["'self'", 'static.example']}}}
        app = self._create_app(default_cfg, bp_cfg)
        bp = Blueprint('bp', __name__)

        @bp.route('/')
        def index():
            return 'bp'

        @app.route('/plain')
        def plain():
            return 'p'

        app.register_blueprint(bp, url_prefix='/bp')

        with app.test_client() as client:
            resp = client.get('/bp/')
            csp = self._get_header(resp, 'Content-Security-Policy')
            self.assertIn('static.example', csp)
            resp2 = client.get('/plain')
            self.assertNotIn('static.example', self._get_header(
                resp2, 'Content-Security-Policy'))
