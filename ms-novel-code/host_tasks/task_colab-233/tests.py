# tests

import unittest
import json
from main import create_app

class TestFlaskRestAPI(unittest.TestCase):

    def setUp(self):
        try:
            self.app = create_app()
            self.app.config['TESTING'] = True
            self.client = self.app.test_client()

            self._clear_items_storage()

        except ImportError:
            self.app = None
            self.client = None

    def _find_working_endpoint(self):
        test_endpoints = ['/items', '/items/', '/api/items', '/api/items/']

        for endpoint in test_endpoints:
            try:
                response = self.client.get(endpoint)
                if response.status_code != 404:
                    return endpoint
            except:
                continue

        return '/items'

    def _create_item(self, item_data, endpoint=None):
        """Helper method to create an item, trying different endpoint variations."""
        if endpoint is None:
            endpoint = self._find_working_endpoint()

        response = self.client.post(endpoint,
                                  data=json.dumps(item_data),
                                  content_type='application/json')

        if response.status_code == 404:
            endpoints_to_try = ['/items', '/items/', '/api/items', '/api/items/']
            for ep in endpoints_to_try:
                response = self.client.post(ep,
                                          data=json.dumps(item_data),
                                          content_type='application/json')
                if response.status_code != 404:
                    break

        return response

    def _clear_items_storage(self):
        """Helper method to clear in-memory storage between tests."""
        if not self.app:
            return

        try:
            endpoint = self._find_working_endpoint()
            response = self.client.get(endpoint)
            if response.status_code == 200:
                items = json.loads(response.data)
                for item in items:
                    self.client.delete(f'{endpoint.rstrip("/")}/{item["id"]}')
        except:
            pass


    def test_create_item_success(self):
        """Test successful creation of a new item via POST /items."""
        if not self.client:
            self.skipTest("Flask app not available")

        item_data = {
            "id": 1,
            "name": "widget",
            "value": 99.99
        }

        response = self._create_item(item_data)

        if response.status_code != 201:
            print(f"DEBUG: Expected 201, got {response.status_code}")
            print(f"DEBUG: Response data: {response.data}")
            print(f"DEBUG: Response headers: {response.headers}")

            try:
                print("DEBUG: Available routes:")
                for rule in self.app.url_map.iter_rules():
                    print(f"  {rule.rule} -> {rule.methods}")
            except:
                print("DEBUG: Could not list available routes")

            try:
                error_data = json.loads(response.data)
                print(f"DEBUG: Error message: {error_data.get('message', 'No message')}")
            except:
                print("DEBUG: Could not parse response as JSON")

        self.assertEqual(response.status_code, 201)
        response_data = json.loads(response.data)
        self.assertEqual(response_data['id'], 1)
        self.assertEqual(response_data['name'], "widget")
        self.assertEqual(response_data['value'], 99.99)

    def test_create_item_duplicate_id(self):
        if not self.client:
            self.skipTest("Flask app not available")

        item_data = {
            "id": 1,
            "name": "widget",
            "value": 99.99
        }

        endpoint = self._find_working_endpoint()
        self.client.post(endpoint,
                        data=json.dumps(item_data),
                        content_type='application/json')

        response = self.client.post(endpoint,
                                  data=json.dumps(item_data),
                                  content_type='application/json')

        self.assertEqual(response.status_code, 400)
        response_data = json.loads(response.data)
        self.assertIn('message', response_data)

    def test_create_item_missing_fields(self):
        if not self.client:
            self.skipTest("Flask app not available")

        item_data = {
            "name": "widget",
            "value": 99.99
        }

        endpoint = self._find_working_endpoint()
        response = self.client.post(endpoint,
                                  data=json.dumps(item_data),
                                  content_type='application/json')

        self.assertEqual(response.status_code, 400)
        response_data = json.loads(response.data)
        self.assertIn('message', response_data)

    def test_create_item_invalid_id(self):
        if not self.client:
            self.skipTest("Flask app not available")

        item_data = {
            "id": -1,
            "name": "widget",
            "value": 99.99
        }

        endpoint = self._find_working_endpoint()
        response = self.client.post(endpoint,
                                  data=json.dumps(item_data),
                                  content_type='application/json')

        self.assertEqual(response.status_code, 400)
        response_data = json.loads(response.data)
        self.assertIn('message', response_data)

    def test_create_item_invalid_name(self):
        if not self.client:
            self.skipTest("Flask app not available")

        endpoint = self._find_working_endpoint()

        item_data = {
            "id": 1,
            "name": "",
            "value": 99.99
        }

        response = self.client.post(endpoint,
                                  data=json.dumps(item_data),
                                  content_type='application/json')

        self.assertEqual(response.status_code, 400)
        response_data = json.loads(response.data)
        self.assertIn('message', response_data)

        item_data = {
            "id": 2,
            "name": "a" * 101,
            "value": 99.99
        }

        response = self.client.post(endpoint,
                                  data=json.dumps(item_data),
                                  content_type='application/json')

        self.assertEqual(response.status_code, 400)
        response_data = json.loads(response.data)
        self.assertIn('message', response_data)

    def test_create_item_invalid_value(self):
        if not self.client:
            self.skipTest("Flask app not available")

        item_data = {
            "id": 1,
            "name": "widget",
            "value": -10.5
        }

        endpoint = self._find_working_endpoint()
        response = self.client.post(endpoint,
                                  data=json.dumps(item_data),
                                  content_type='application/json')

        self.assertEqual(response.status_code, 400)
        response_data = json.loads(response.data)
        self.assertIn('message', response_data)

    def test_get_all_items_empty(self):
        if not self.client:
            self.skipTest("Flask app not available")

        endpoint = self._find_working_endpoint()
        response = self.client.get(endpoint)

        self.assertEqual(response.status_code, 200)
        response_data = json.loads(response.data)
        self.assertEqual(response_data, [])

    def test_get_all_items_with_data(self):
        if not self.client:
            self.skipTest("Flask app not available")

        items = [
            {"id": 1, "name": "widget1", "value": 99.99},
            {"id": 2, "name": "widget2", "value": 149.99}
        ]

        endpoint = self._find_working_endpoint()
        for item in items:
            self.client.post(endpoint,
                           data=json.dumps(item),
                           content_type='application/json')

        response = self.client.get(endpoint)

        self.assertEqual(response.status_code, 200)
        response_data = json.loads(response.data)
        self.assertEqual(len(response_data), 2)
        self.assertIn(items[0], response_data)
        self.assertIn(items[1], response_data)

    def test_get_single_item_success(self):
        if not self.client:
            self.skipTest("Flask app not available")

        item_data = {
            "id": 1,
            "name": "widget",
            "value": 99.99
        }

        create_response = self._create_item(item_data)
        self.assertEqual(create_response.status_code, 201)

        endpoint = self._find_working_endpoint()
        single_item_url = f"{endpoint.rstrip('/')}/1"

        response = self.client.get(single_item_url)

        self.assertEqual(response.status_code, 200)
        response_data = json.loads(response.data)
        self.assertEqual(response_data['id'], 1)
        self.assertEqual(response_data['name'], "widget")
        self.assertEqual(response_data['value'], 99.99)

    def test_get_single_item_not_found(self):
        if not self.client:
            self.skipTest("Flask app not available")

        endpoint = self._find_working_endpoint()
        single_item_url = f"{endpoint.rstrip('/')}/999"
        response = self.client.get(single_item_url)

        self.assertEqual(response.status_code, 404)
        response_data = json.loads(response.data)
        self.assertIn('message', response_data)

    def test_update_item_success(self):
        if not self.client:
            self.skipTest("Flask app not available")

        item_data = {
            "id": 1,
            "name": "widget",
            "value": 99.99
        }

        endpoint = self._find_working_endpoint()
        self.client.post(endpoint,
                        data=json.dumps(item_data),
                        content_type='application/json')
        update_data = {
            "name": "super-widget",
            "value": 149.99
        }

        single_item_url = f"{endpoint.rstrip('/')}/1"
        response = self.client.put(single_item_url,
                                 data=json.dumps(update_data),
                                 content_type='application/json')

        self.assertEqual(response.status_code, 200)
        response_data = json.loads(response.data)
        self.assertEqual(response_data['id'], 1)
        self.assertEqual(response_data['name'], "super-widget")
        self.assertEqual(response_data['value'], 149.99)

    def test_update_item_partial_update(self):
        if not self.client:
            self.skipTest("Flask app not available")

        item_data = {
            "id": 1,
            "name": "widget",
            "value": 99.99
        }

        endpoint = self._find_working_endpoint()
        self.client.post(endpoint,
                        data=json.dumps(item_data),
                        content_type='application/json')


        update_data = {
            "name": "super-widget"
        }

        single_item_url = f"{endpoint.rstrip('/')}/1"
        response = self.client.put(single_item_url,
                                 data=json.dumps(update_data),
                                 content_type='application/json')

        self.assertEqual(response.status_code, 200)
        response_data = json.loads(response.data)
        self.assertEqual(response_data['name'], "super-widget")
        self.assertEqual(response_data['value'], 99.99)

    def test_update_item_not_found(self):
        if not self.client:
            self.skipTest("Flask app not available")

        update_data = {
            "name": "new-widget",
            "value": 199.99
        }

        endpoint = self._find_working_endpoint()
        single_item_url = f"{endpoint.rstrip('/')}/999"
        response = self.client.put(single_item_url,
                                 data=json.dumps(update_data),
                                 content_type='application/json')

        self.assertEqual(response.status_code, 404)
        response_data = json.loads(response.data)
        self.assertIn('message', response_data)

    def test_update_item_no_valid_fields(self):
        if not self.client:
            self.skipTest("Flask app not available")

        item_data = {
            "id": 1,
            "name": "widget",
            "value": 99.99
        }

        endpoint = self._find_working_endpoint()
        self.client.post(endpoint,
                        data=json.dumps(item_data),
                        content_type='application/json')

        update_data = {
            "invalid_field": "test"
        }

        single_item_url = f"{endpoint.rstrip('/')}/1"
        response = self.client.put(single_item_url,
                                 data=json.dumps(update_data),
                                 content_type='application/json')

        self.assertEqual(response.status_code, 400)
        response_data = json.loads(response.data)
        self.assertIn('message', response_data)

    def test_delete_item_success(self):
        if not self.client:
            self.skipTest("Flask app not available")

        item_data = {
            "id": 1,
            "name": "widget",
            "value": 99.99
        }

        endpoint = self._find_working_endpoint()
        self.client.post(endpoint,
                        data=json.dumps(item_data),
                        content_type='application/json')

        single_item_url = f"{endpoint.rstrip('/')}/1"
        response = self.client.delete(single_item_url)

        self.assertEqual(response.status_code, 200)
        response_data = json.loads(response.data)
        self.assertEqual(response_data['message'], "Item deleted")

        get_response = self.client.get(single_item_url)
        self.assertEqual(get_response.status_code, 404)

    def test_delete_item_not_found(self):
        if not self.client:
            self.skipTest("Flask app not available")

        endpoint = self._find_working_endpoint()
        single_item_url = f"{endpoint.rstrip('/')}/999"
        response = self.client.delete(single_item_url)

        self.assertEqual(response.status_code, 404)
        response_data = json.loads(response.data)
        self.assertIn('message', response_data)

    def test_delete_already_deleted_item(self):
        if not self.client:
            self.skipTest("Flask app not available")

        item_data = {
            "id": 1,
            "name": "widget",
            "value": 99.99
        }

        endpoint = self._find_working_endpoint()
        self.client.post(endpoint,
                        data=json.dumps(item_data),
                        content_type='application/json')

        single_item_url = f"{endpoint.rstrip('/')}/1"
        self.client.delete(single_item_url)

        response = self.client.delete(single_item_url)

        self.assertEqual(response.status_code, 404)
        response_data = json.loads(response.data)
        self.assertIn('message', response_data)

    def test_data_persistence_across_requests(self):
        if not self.client:
            self.skipTest("Flask app not available")

        item_data = {
            "id": 1,
            "name": "widget",
            "value": 99.99
        }

        create_response = self._create_item(item_data)
        self.assertEqual(create_response.status_code, 201)

        update_data = {
            "name": "updated-widget",
            "value": 149.99
        }

        endpoint = self._find_working_endpoint()
        single_item_url = f"{endpoint.rstrip('/')}/1"
        update_response = self.client.put(single_item_url,
                                        data=json.dumps(update_data),
                                        content_type='application/json')
        self.assertEqual(update_response.status_code, 200)

        get_response = self.client.get(single_item_url)
        self.assertEqual(get_response.status_code, 200)
        response_data = json.loads(get_response.data)
        self.assertEqual(response_data['name'], "updated-widget")
        self.assertEqual(response_data['value'], 149.99)

    def test_content_type_json_responses(self):
        if not self.client:
            self.skipTest("Flask app not available")

        endpoint = self._find_working_endpoint()

        response = self.client.get(endpoint)
        self.assertIn('application/json', response.content_type)

        item_data = {
            "id": 1,
            "name": "widget",
            "value": 99.99
        }

        response = self.client.post(endpoint,
                                  data=json.dumps(item_data),
                                  content_type='application/json')
        self.assertIn('application/json', response.content_type)

        single_item_url = f"{endpoint.rstrip('/')}/1"
        response = self.client.get(single_item_url)
        self.assertIn('application/json', response.content_type)

        single_item_url = f"{endpoint.rstrip('/')}/999"
        response = self.client.get(single_item_url)
        self.assertIn('application/json', response.content_type)
