# tests
"""Test suite for the ProductCatalog class."""

import unittest
from main import ProductCatalog


class TestProductCatalog(unittest.TestCase):
    """Unit tests for the ProductCatalog class."""

    def setUp(self):
        """Create a fresh in-memory catalog before each test."""
        self.catalog = ProductCatalog("sqlite:///:memory:")

    def tearDown(self):
        """Dispose the database engine after each test."""
        self.catalog.engine.dispose()

    def test_create_valid_product(self):
        """Test creating a product with valid data."""
        product = self.catalog.create_product({
            "name": "Widget",
            "description": "A basic widget",
            "price": 9.99,
            "stock": 100
        })
        self.assertIn("id", product)
        self.assertEqual(product["name"], "Widget")

    def test_create_product_missing_name(self):
        """Test creating product with missing name."""
        result = self.catalog.create_product({
            "description": "No name",
            "price": 9.99,
            "stock": 100
        })
        self.assertIn("error", result)

    def test_create_product_blank_name(self):
        """Test creating product with blank name."""
        result = self.catalog.create_product({
            "name": "   ",
            "price": 9.99,
            "stock": 100
        })
        self.assertIn("error", result)

    def test_create_product_name_too_long(self):
        """Test product name exceeding character limit."""
        result = self.catalog.create_product({
            "name": "x" * 101,
            "price": 9.99,
            "stock": 100
        })
        self.assertIn("error", result)

    def test_create_product_invalid_price(self):
        """Test creating product with negative price."""
        result = self.catalog.create_product({
            "name": "BadPrice",
            "price": -5,
            "stock": 100
        })
        self.assertIn("error", result)

    def test_create_product_invalid_stock(self):
        """Test creating product with negative stock."""
        result = self.catalog.create_product({
            "name": "BadStock",
            "price": 9.99,
            "stock": -1
        })
        self.assertIn("error", result)

    def test_get_existing_product(self):
        """Test fetching an existing product."""
        created = self.catalog.create_product({
            "name": "Gadget",
            "price": 5.55,
            "stock": 10
        })
        fetched = self.catalog.get_product(created["id"])
        self.assertEqual(fetched["name"], "Gadget")

    def test_get_nonexistent_product(self):
        """Test fetching a nonexistent product."""
        result = self.catalog.get_product(999)
        self.assertIn("error", result)

    def test_update_product_name_and_price(self):
        """Test updating name and price of a product."""
        created = self.catalog.create_product({
            "name": "OldName",
            "price": 1.99,
            "stock": 10
        })
        updated = self.catalog.update_product(created["id"], {
            "name": "NewName",
            "price": 2.99
        })
        self.assertEqual(updated["name"], "NewName")
        self.assertEqual(updated["price"], 2.99)

    def test_update_product_invalid_price(self):
        """Test updating product with invalid price."""
        created = self.catalog.create_product({
            "name": "Thing",
            "price": 5.0,
            "stock": 5
        })
        result = self.catalog.update_product(created["id"], {"price": -10})
        self.assertIn("error", result)

    def test_update_product_invalid_name(self):
        """Test updating product with blank name."""
        created = self.catalog.create_product({
            "name": "Something",
            "price": 3.5,
            "stock": 5
        })
        result = self.catalog.update_product(created["id"], {"name": ""})
        self.assertIn("error", result)

    def test_update_nonexistent_product(self):
        """Test updating a nonexistent product."""
        result = self.catalog.update_product(999, {"name": "Ghost"})
        self.assertIn("error", result)

    def test_delete_existing_product(self):
        """Test deleting an existing product."""
        created = self.catalog.create_product({
            "name": "ToDelete",
            "price": 1.99,
            "stock": 1
        })
        result = self.catalog.delete_product(created["id"])
        self.assertEqual(result["message"], "Product deleted successfully")

    def test_delete_nonexistent_product(self):
        """Test deleting a nonexistent product."""
        result = self.catalog.delete_product(999)
        self.assertIn("error", result)

    def test_list_products_empty(self):
        """Test listing products when catalog is empty."""
        result = self.catalog.list_products()
        self.assertEqual(result["products"], [])
        self.assertEqual(result["total_products"], 0)

    def test_list_products_pagination(self):
        """Test listing products with pagination."""
        for i in range(25):
            self.catalog.create_product({
                "name": f"Item{i}",
                "price": i,
                "stock": i
            })
        page1 = self.catalog.list_products(page=1, page_size=10)
        page3 = self.catalog.list_products(page=3, page_size=10)
        self.assertEqual(len(page1["products"]), 10)
        self.assertEqual(len(page3["products"]), 5)

    def test_list_products_filter_min_price(self):
        """Test listing products with minimum price filter."""
        self.catalog.create_product({
            "name": "Cheap",
            "price": 1,
            "stock": 5
        })
        self.catalog.create_product({
            "name": "Expensive",
            "price": 100,
            "stock": 5
        })
        result = self.catalog.list_products(min_price=50)
        self.assertEqual(len(result["products"]), 1)
        self.assertEqual(result["products"][0]["name"], "Expensive")

    def test_list_products_filter_name_contains(self):
        """Test listing products by name substring match."""
        self.catalog.create_product({
            "name": "Foobar",
            "price": 10,
            "stock": 5
        })
        self.catalog.create_product({
            "name": "Bazqux",
            "price": 10,
            "stock": 5
        })
        result = self.catalog.list_products(name_contains="bar")
        self.assertEqual(len(result["products"]), 1)
        self.assertEqual(result["products"][0]["name"], "Foobar")

    def test_list_products_sort_by_price_desc(self):
        """Test sorting products by descending price."""
        self.catalog.create_product({"name": "A", "price": 10, "stock": 1})
        self.catalog.create_product({"name": "B", "price": 5, "stock": 1})
        result = self.catalog.list_products(sort_by="price", ascending=False)
        self.assertEqual(result["products"][0]["price"], 10)

    def test_list_products_invalid_sort_field(self):
        """Test listing with an invalid sort field."""
        result = self.catalog.list_products(sort_by="nonexistent")
        self.assertIn("error", result)

    def test_list_products_invalid_page_number(self):
        """Test listing with invalid page number."""
        result = self.catalog.list_products(page=0)
        self.assertIn("error", result)

    def test_list_products_invalid_page_size(self):
        """Test listing with invalid page size."""
        result = self.catalog.list_products(page_size=1000)
        self.assertIn("error", result)
