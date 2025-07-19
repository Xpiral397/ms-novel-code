# tests

"""
Test cases for the Flask Books RESTful API endpoints.

This module contains comprehensive test cases for testing the Flask Books API
endpoints that manage a collection of Book resources with HTTP Basic
Authentication and JSON file persistence.
"""

import unittest
import json
import os
import tempfile
import base64

# Assuming the main application is in app.py
from main import create_app


class TestBooksAPIEndpoints(unittest.TestCase):
    """Test cases for the Books REST API endpoints."""

    def setUp(self):
        """Set up test fixtures before each test method."""
        self.temp_dir = tempfile.mkdtemp()
        self.test_file = os.path.join(self.temp_dir, 'test_books.json')
        self.test_users = {'admin': 'password', 'user': 'secret'}
        self.app = create_app(self.test_file, self.test_users)
        self.client = self.app.test_client()

        # Create valid auth headers
        self.valid_auth = self._create_auth_header('admin', 'password')
        self.invalid_auth = self._create_auth_header('admin', 'wrong')

        # Sample book data
        self.sample_book = {
            'title': 'Test Book',
            'author': 'Test Author',
            'year': 2023
        }

    def tearDown(self):
        """Clean up after each test method."""
        if os.path.exists(self.test_file):
            os.remove(self.test_file)
        os.rmdir(self.temp_dir)

    def _create_auth_header(self, username, password):
        """Create HTTP Basic Auth header."""
        credentials = base64.b64encode(
            f'{username}:{password}'.encode('utf-8')
        ).decode('utf-8')
        return {'Authorization': f'Basic {credentials}'}

    def _create_test_book(self, book_data=None):
        """Helper method to create a test book via POST endpoint."""
        if book_data is None:
            book_data = self.sample_book

        response = self.client.post(
            '/books',
            data=json.dumps(book_data),
            content_type='application/json',
            headers=self.valid_auth
        )
        return response

    def test_get_books_endpoint_no_auth(self):
        """Test GET /books without authentication returns 401."""
        response = self.client.get('/books')
        self.assertEqual(response.status_code, 401)

    def test_get_books_endpoint_invalid_auth(self):
        """Test GET /books with invalid credentials returns 401."""
        response = self.client.get('/books', headers=self.invalid_auth)
        self.assertEqual(response.status_code, 401)

    def test_get_books_endpoint_empty_collection(self):
        """Test GET /books returns empty list when no books exist."""
        response = self.client.get('/books', headers=self.valid_auth)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json, [])
        self.assertEqual(response.content_type, 'application/json')

    def test_get_books_endpoint_with_data(self):
        """Test GET /books returns list of books when data exists."""
        # Create two test books
        book1 = {'title': '1984', 'author': 'Orwell', 'year': 1949}
        book2 = {'title': 'Dune', 'author': 'Herbert', 'year': 1965}

        self._create_test_book(book1)
        self._create_test_book(book2)

        response = self.client.get('/books', headers=self.valid_auth)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.json), 2)
        self.assertIsInstance(response.json, list)

    def test_get_book_by_id_endpoint_success(self):
        """Test GET /books/<id> returns specific book."""
        # Create a test book first
        create_response = self._create_test_book()
        book_id = create_response.json['id']

        response = self.client.get(f'/books/{book_id}',
                                   headers=self.valid_auth)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json['title'], self.sample_book['title'])
        self.assertEqual(response.json['id'], book_id)

    def test_get_book_by_id_endpoint_not_found(self):
        """Test GET /books/<id> returns 404 for non-existent book."""
        response = self.client.get('/books/non-existent-id',
                                   headers=self.valid_auth)
        self.assertEqual(response.status_code, 404)

    def test_get_book_by_id_endpoint_no_auth(self):
        """Test GET /books/<id> without authentication returns 401."""
        response = self.client.get('/books/some-id')
        self.assertEqual(response.status_code, 401)

    def test_post_books_endpoint_success(self):
        """Test POST /books creates new book successfully."""
        response = self._create_test_book()

        self.assertEqual(response.status_code, 201)
        self.assertIn('id', response.json)
        self.assertEqual(response.json['title'], self.sample_book['title'])
        self.assertEqual(response.json['author'], self.sample_book['author'])
        self.assertEqual(response.json['year'], self.sample_book['year'])
        self.assertEqual(response.content_type, 'application/json')

    def test_post_books_endpoint_no_auth(self):
        """Test POST /books without authentication returns 401."""
        response = self.client.post(
            '/books',
            data=json.dumps(self.sample_book),
            content_type='application/json'
        )
        self.assertEqual(response.status_code, 401)

    def test_post_books_endpoint_invalid_json(self):
        """Test POST /books with invalid JSON returns 400."""
        response = self.client.post(
            '/books',
            data='invalid json',
            content_type='application/json',
            headers=self.valid_auth
        )
        self.assertEqual(response.status_code, 400)

    def test_post_books_endpoint_missing_title(self):
        """Test POST /books with missing title returns 400."""
        incomplete_book = {'author': 'Test Author', 'year': 2023}
        response = self.client.post(
            '/books',
            data=json.dumps(incomplete_book),
            content_type='application/json',
            headers=self.valid_auth
        )
        self.assertEqual(response.status_code, 400)

    def test_post_books_endpoint_missing_author(self):
        """Test POST /books with missing author returns 400."""
        incomplete_book = {'title': 'Test Book', 'year': 2023}
        response = self.client.post(
            '/books',
            data=json.dumps(incomplete_book),
            content_type='application/json',
            headers=self.valid_auth
        )
        self.assertEqual(response.status_code, 400)

    def test_post_books_endpoint_missing_year(self):
        """Test POST /books with missing year returns 400."""
        incomplete_book = {'title': 'Test Book', 'author': 'Test Author'}
        response = self.client.post(
            '/books',
            data=json.dumps(incomplete_book),
            content_type='application/json',
            headers=self.valid_auth
        )
        self.assertEqual(response.status_code, 400)

    def test_post_books_endpoint_empty_title(self):
        """Test POST /books with empty title returns 400."""
        invalid_book = {
            'title': '',
            'author': 'Test Author',
            'year': 2023
        }
        response = self.client.post(
            '/books',
            data=json.dumps(invalid_book),
            content_type='application/json',
            headers=self.valid_auth
        )
        self.assertEqual(response.status_code, 400)

    def test_post_books_endpoint_empty_author(self):
        """Test POST /books with empty author returns 400."""
        invalid_book = {
            'title': 'Test Book',
            'author': '',
            'year': 2023
        }
        response = self.client.post(
            '/books',
            data=json.dumps(invalid_book),
            content_type='application/json',
            headers=self.valid_auth
        )
        self.assertEqual(response.status_code, 400)

    def test_post_books_endpoint_invalid_year_string(self):
        """Test POST /books with year as string returns 400."""
        invalid_book = {
            'title': 'Test Book',
            'author': 'Test Author',
            'year': 'not a number'
        }
        response = self.client.post(
            '/books',
            data=json.dumps(invalid_book),
            content_type='application/json',
            headers=self.valid_auth
        )
        self.assertEqual(response.status_code, 400)

    def test_post_books_endpoint_year_not_four_digits(self):
        """Test POST /books with year not four digits returns 400."""
        invalid_book = {
            'title': 'Test Book',
            'author': 'Test Author',
            'year': 999
        }
        response = self.client.post(
            '/books',
            data=json.dumps(invalid_book),
            content_type='application/json',
            headers=self.valid_auth
        )
        self.assertEqual(response.status_code, 400)

    def test_post_books_endpoint_year_too_many_digits(self):
        """Test POST /books with year having too many digits returns 400."""
        invalid_book = {
            'title': 'Test Book',
            'author': 'Test Author',
            'year': 12345
        }
        response = self.client.post(
            '/books',
            data=json.dumps(invalid_book),
            content_type='application/json',
            headers=self.valid_auth
        )
        self.assertEqual(response.status_code, 400)

    def test_put_books_endpoint_success(self):
        """Test PUT /books/<id> updates existing book successfully."""
        # Create a book first
        create_response = self._create_test_book()
        book_id = create_response.json['id']

        updated_book = {
            'title': 'Updated Title',
            'author': 'Updated Author',
            'year': 2024
        }

        response = self.client.put(
            f'/books/{book_id}',
            data=json.dumps(updated_book),
            content_type='application/json',
            headers=self.valid_auth
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json['title'], 'Updated Title')
        self.assertEqual(response.json['author'], 'Updated Author')
        self.assertEqual(response.json['year'], 2024)
        self.assertEqual(response.json['id'], book_id)

    def test_put_books_endpoint_not_found(self):
        """Test PUT /books/<id> returns 404 for non-existent book."""
        response = self.client.put(
            '/books/non-existent-id',
            data=json.dumps(self.sample_book),
            content_type='application/json',
            headers=self.valid_auth
        )
        self.assertEqual(response.status_code, 404)

    def test_put_books_endpoint_no_auth(self):
        """Test PUT /books/<id> without authentication returns 401."""
        response = self.client.put(
            '/books/some-id',
            data=json.dumps(self.sample_book),
            content_type='application/json'
        )
        self.assertEqual(response.status_code, 401)

    def test_put_books_endpoint_invalid_data(self):
        """Test PUT /books/<id> with invalid data returns 400."""
        # Create a book first
        create_response = self._create_test_book()
        book_id = create_response.json['id']

        invalid_update = {
            'title': '',
            'author': 'Test Author',
            'year': 2023
        }

        response = self.client.put(
            f'/books/{book_id}',
            data=json.dumps(invalid_update),
            content_type='application/json',
            headers=self.valid_auth
        )
        self.assertEqual(response.status_code, 400)

    def test_delete_books_endpoint_success(self):
        """Test DELETE /books/<id> removes book successfully."""
        # Create a book first
        create_response = self._create_test_book()
        book_id = create_response.json['id']

        response = self.client.delete(f'/books/{book_id}',
                                      headers=self.valid_auth)
        self.assertEqual(response.status_code, 204)
        self.assertEqual(response.data, b'')

        # Verify book is actually deleted
        get_response = self.client.get(f'/books/{book_id}',
                                       headers=self.valid_auth)
        self.assertEqual(get_response.status_code, 404)

    def test_delete_books_endpoint_not_found(self):
        """Test DELETE /books/<id> returns 404 for non-existent book."""
        response = self.client.delete('/books/non-existent-id',
                                      headers=self.valid_auth)
        self.assertEqual(response.status_code, 404)

    def test_delete_books_endpoint_no_auth(self):
        """Test DELETE /books/<id> without authentication returns 401."""
        response = self.client.delete('/books/some-id')
        self.assertEqual(response.status_code, 401)

    def test_post_books_endpoint_with_extra_fields(self):
        """Test POST /books ignores extra fields in request."""
        book_with_extra = {
            'title': 'Test Book',
            'author': 'Test Author',
            'year': 2023,
            'extra_field': 'should be ignored',
            'another_field': 42
        }

        response = self.client.post(
            '/books',
            data=json.dumps(book_with_extra),
            content_type='application/json',
            headers=self.valid_auth
        )

        self.assertEqual(response.status_code, 201)
        self.assertNotIn('extra_field', response.json)
        self.assertNotIn('another_field', response.json)

    def test_duplicate_books_allowed(self):
        """Test that duplicate book titles and authors are allowed."""
        # Create first book
        response1 = self._create_test_book()
        self.assertEqual(response1.status_code, 201)

        # Create second book with same data
        response2 = self._create_test_book()
        self.assertEqual(response2.status_code, 201)

        # Verify different IDs but same content
        self.assertNotEqual(response1.json['id'], response2.json['id'])
        self.assertEqual(response1.json['title'], response2.json['title'])

        # Verify both books exist in collection
        get_response = self.client.get('/books', headers=self.valid_auth)
        self.assertEqual(len(get_response.json), 2)

    def test_alternative_user_authentication(self):
        """Test authentication with alternative user credentials."""
        alt_auth = self._create_auth_header('user', 'secret')

        # Test with alternative credentials
        response = self.client.get('/books', headers=alt_auth)
        self.assertEqual(response.status_code, 200)

        # Test creating book with alternative credentials
        response = self.client.post(
            '/books',
            data=json.dumps(self.sample_book),
            content_type='application/json',
            headers=alt_auth
        )
        self.assertEqual(response.status_code, 201)

    def test_books_persistence_across_requests(self):
        """Test that books persist across multiple HTTP requests."""
        # Create a book
        create_response = self._create_test_book()
        book_id = create_response.json['id']

        # Verify it exists in a separate request
        get_response = self.client.get(f'/books/{book_id}',
                                       headers=self.valid_auth)
        self.assertEqual(get_response.status_code, 200)
        self.assertEqual(get_response.json['title'],
                         self.sample_book['title'])

        # Create another book
        book2 = {'title': 'Book 2', 'author': 'Author 2', 'year': 2024}
        self._create_test_book(book2)

        # Verify both books exist
        list_response = self.client.get('/books', headers=self.valid_auth)
        self.assertEqual(len(list_response.json), 2)

    def test_endpoint_content_type_validation(self):
        """Test that POST and PUT endpoints handle content type properly."""
        # Test POST with wrong content type
        response = self.client.post(
            '/books',
            data=json.dumps(self.sample_book),
            content_type='text/plain',
            headers=self.valid_auth
        )
        self.assertIn(response.status_code, [400, 415])

        # Test POST with no content type
        response = self.client.post(
            '/books',
            data=json.dumps(self.sample_book),
            headers=self.valid_auth
        )
        self.assertIn(response.status_code, [400, 415])

    def test_endpoint_method_not_allowed(self):
        """Test that unsupported HTTP methods return 405."""
        # Test PATCH method (not supported)
        response = self.client.patch('/books', headers=self.valid_auth)
        self.assertEqual(response.status_code, 405)

        # Test POST on specific book ID (not supported)
        response = self.client.post('/books/some-id',
                                    headers=self.valid_auth)
        self.assertEqual(response.status_code, 405)
