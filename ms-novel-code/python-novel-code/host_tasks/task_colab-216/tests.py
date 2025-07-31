# tests

"""Module consists test cases to validate 'validate_and_store_product'."""

import unittest
from main import app, db, validate_and_store_product, Category
import json


class TestProductValidation(unittest.TestCase):
    """Unit tests for validate_and_store_product function."""

    def setUp(self):
        """Set up test fixtures before each test method."""
        self.app = app
        self.app_context = self.app.app_context()
        self.app_context.push()

        db.drop_all()
        db.create_all()

        db.session.add_all([
            Category(name="Electronics", locale="en_US"),
            Category(name="Books", locale="en_US"),
            Category(name="Clothing", locale="en_US"),
            Category(name="Elektronik", locale="de_DE"),
            Category(name="Bücher", locale="de_DE"),
            Category(name="Kleidung", locale="de_DE"),
        ])
        db.session.commit()

    def tearDown(self):
        """Clean up after each test method."""
        db.session.remove()
        self.app_context.pop()

    def test_valid_us_product(self):
        """Test valid product submission for US market."""
        payload = {
            "name": "USB Cable",
            "price": "15.99",
            "category": "Electronics",
            "launch_date": "08/20/2024"
        }
        result = validate_and_store_product(json.dumps(payload), "en_US")
        self.assertEqual(result["status"], "success")

    def test_valid_german_product_with_cert(self):
        """Test valid product with CE cert for German market."""
        payload = {
            "name": "Router",
            "price": "199.99",
            "category": "Elektronik",
            "launch_date": "15.07.2024",
            "certification": "CE-1234"
        }
        result = validate_and_store_product(json.dumps(payload), "de_DE")
        self.assertEqual(result["status"], "success")

    def test_missing_certification_german(self):
        """Test missing certification for German product."""
        payload = {
            "name": "Smartphone",
            "price": "599.99",
            "category": "Elektronik",
            "launch_date": "01.06.2024"
        }
        result = validate_and_store_product(json.dumps(payload), "de_DE")
        self.assertEqual(result["status"], "validation_error")
        self.assertIn("certification", result["errors"])

    def test_invalid_price_us(self):
        """Test US product with price below allowed range."""
        payload = {
            "name": "Book",
            "price": "5.00",
            "category": "Books",
            "launch_date": "03/10/2024"
        }
        result = validate_and_store_product(json.dumps(payload), "en_US")
        self.assertEqual(result["status"], "validation_error")
        self.assertIn("price", result["errors"])

    def test_invalid_price_de(self):
        """Test German product with price above allowed range."""
        payload = {
            "name": "TV",
            "price": "4999.00",
            "category": "Elektronik",
            "launch_date": "10.06.2024",
            "certification": "CE-0001"
        }
        result = validate_and_store_product(json.dumps(payload), "de_DE")
        self.assertEqual(result["status"], "validation_error")
        self.assertIn("price", result["errors"])

    def test_invalid_category_us(self):
        """Test invalid category for US product."""
        payload = {
            "name": "Gadget",
            "price": "29.99",
            "category": "Gadgets",
            "launch_date": "02/12/2024"
        }
        result = validate_and_store_product(json.dumps(payload), "en_US")
        self.assertEqual(result["status"], "validation_error")
        self.assertIn("category", result["errors"])

    def test_invalid_category_de(self):
        """Test invalid category for German product."""
        payload = {
            "name": "Camera",
            "price": "299.00",
            "category": "Fotografie",
            "launch_date": "01.05.2024",
            "certification": "CE-9000"
        }
        result = validate_and_store_product(json.dumps(payload), "de_DE")
        self.assertEqual(result["status"], "validation_error")
        self.assertIn("category", result["errors"])

    def test_invalid_date_format_us(self):
        """Test invalid US date format."""
        payload = {
            "name": "Laptop",
            "price": "999.99",
            "category": "Electronics",
            "launch_date": "2024-03-10"
        }
        result = validate_and_store_product(json.dumps(payload), "en_US")
        self.assertEqual(result["status"], "validation_error")
        self.assertIn("launch_date", result["errors"])

    def test_invalid_date_format_de(self):
        """Test invalid German date format."""
        payload = {
            "name": "Tablet",
            "price": "450.00",
            "category": "Elektronik",
            "launch_date": "2024/06/01",
            "certification": "CE-1111"
        }
        result = validate_and_store_product(json.dumps(payload), "de_DE")
        self.assertEqual(result["status"], "validation_error")
        self.assertIn("launch_date", result["errors"])

    def test_invalid_json_input(self):
        """Test malformed JSON input handling."""
        bad_json = '{"name": "Speaker", "price": "99.99",}'
        result = validate_and_store_product(bad_json, "en_US")
        self.assertEqual(result["status"], "storage_error")

    def test_missing_required_field(self):
        """Test product missing required name field."""
        payload = {
            "price": "25.00",
            "category": "Books",
            "launch_date": "04/01/2024"
        }
        result = validate_and_store_product(json.dumps(payload), "en_US")
        self.assertEqual(result["status"], "validation_error")
        self.assertIn("name", result["errors"])

    def test_invalid_price_format(self):
        """Test product with invalid price string."""
        payload = {
            "name": "Charger",
            "price": "twenty",
            "category": "Electronics",
            "launch_date": "06/10/2024"
        }
        result = validate_and_store_product(json.dumps(payload), "en_US")
        self.assertEqual(result["status"], "validation_error")
        self.assertIn("price", result["errors"])

    def test_certification_invalid_code(self):
        """Test German product with invalid certification code."""
        payload = {
            "name": "Scanner",
            "price": "300.00",
            "category": "Elektronik",
            "launch_date": "12.12.2024",
            "certification": "X-0001"
        }
        result = validate_and_store_product(json.dumps(payload), "de_DE")
        self.assertEqual(result["status"], "validation_error")
        self.assertIn("certification", result["errors"])

    def test_name_length_too_long(self):
        """Test product name exceeding 100 characters."""
        payload = {
            "name": "x" * 101,
            "price": "30.00",
            "category": "Books",
            "launch_date": "03/03/2024"
        }
        result = validate_and_store_product(json.dumps(payload), "en_US")
        self.assertEqual(result["status"], "validation_error")
        self.assertIn("name", result["errors"])

    def test_name_minimum_length(self):
        """Test product name at minimum length."""
        payload = {
            "name": "X",
            "price": "12.00",
            "category": "Books",
            "launch_date": "04/12/2024"
        }
        result = validate_and_store_product(json.dumps(payload), "en_US")
        self.assertEqual(result["status"], "success")
