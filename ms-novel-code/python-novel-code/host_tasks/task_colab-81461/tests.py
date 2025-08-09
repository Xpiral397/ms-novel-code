# tests

"""Unit testcases for EcommerceSagaProcessor."""

import unittest
from main import ecommerce_saga_processor


class TestEcommerceSagaProcessor(unittest.TestCase):
    """Unit tests for the ecommerce_saga_processor function."""

    def setUp(self):
        """Common setup for all tests if needed."""


    def test_create_customer_and_query(self):
        """Test customer creation and querying updates credit limit properly."""
        ops = [
            ("CREATE_CUSTOMER", "C001", 1000),
            ("QUERY_CUSTOMER", "C001")
        ]
        result = ecommerce_saga_processor(ops)
        self.assertIn("C001", result["customers"])
        self.assertEqual(result["customers"]["C001"]["credit_limit"], 1000)
        self.assertEqual(result["customers"]["C001"]["credit_used"], 0)
        self.assertEqual(result["customers"]["C001"]["status"], "ACTIVE")

    def test_add_product_and_query(self):
        """Test product addition and querying updates stock and price correctly."""
        ops = [
            ("ADD_PRODUCT", "P001", 10, 200),
            ("QUERY_PRODUCT", "P001")  # Although QUERY_PRODUCT not defined, test ignored
        ]
        # QUERY_PRODUCT isn't defined, so only check internal state after adding product
        result = ecommerce_saga_processor(ops)
        self.assertIn("P001", result["products"])
        self.assertEqual(result["products"]["P001"]["stock"], 10)
        self.assertEqual(result["products"]["P001"]["price"], 200)
        self.assertEqual(result["products"]["P001"]["reserved"], 0)
        self.assertEqual(result["products"]["P001"]["status"], "AVAILABLE")

    def test_place_order_successful_flow(self):
        """Test a successful order placement and full saga completion."""
        ops = [
            ("CREATE_CUSTOMER", "C001", 1000),
            ("ADD_PRODUCT", "P001", 10, 150),
            ("PLACE_ORDER", "C001", "P001", 2),
            ("QUERY_ORDER", "O001")
        ]
        result = ecommerce_saga_processor(ops)
        order = result["orders"]["O001"]
        self.assertEqual(order["status"], "SHIPPED")
        self.assertEqual(order["total_amount"], 300)
        self.assertListEqual(
            order["events_completed"],
            ["ORDER_CREATED", "PAYMENT_PROCESSED", "INVENTORY_RESERVED",
             "ORDER_SHIPPED"]
        )
        self.assertListEqual(order["compensation_events"], [])
        self.assertEqual(result["customers"]["C001"]["credit_used"], 300)
        self.assertEqual(result["products"]["P001"]["stock"], 8)

    def test_order_fails_due_to_insufficient_stock(self):
        """Test order fails at inventory reservation due to insufficient stock."""
        ops = [
            ("CREATE_CUSTOMER", "C003", 1000),
            ("ADD_PRODUCT", "P003", 2, 200),
            ("PLACE_ORDER", "C003", "P003", 5),
            ("QUERY_ORDER", "O001")
        ]
        result = ecommerce_saga_processor(ops)
        order = result["orders"]["O001"]
        self.assertEqual(order["status"], "CANCELED")
        self.assertListEqual(order["events_completed"], ["ORDER_CREATED",
                                                        "PAYMENT_PROCESSED"])
        self.assertListEqual(order["compensation_events"],
                             ["PAYMENT_REFUNDED", "ORDER_CANCELED"])
        self.assertEqual(result["customers"]["C003"]["credit_used"], 0)
        self.assertEqual(result["products"]["P003"]["stock"], 2)

    def test_order_with_zero_quantity(self):
        """Test placing order with zero quantity completes successfully."""
        ops = [
            ("CREATE_CUSTOMER", "C004", 500),
            ("ADD_PRODUCT", "P004", 5, 100),
            ("PLACE_ORDER", "C004", "P004", 0),
            ("QUERY_ORDER", "O001")
        ]
        result = ecommerce_saga_processor(ops)
        order = result["orders"]["O001"]
        self.assertEqual(order["quantity"], 0)
        self.assertEqual(order["status"], "SHIPPED")
        self.assertEqual(order["total_amount"], 0)
        self.assertListEqual(order["events_completed"],
                             ["ORDER_CREATED", "PAYMENT_PROCESSED",
                              "INVENTORY_RESERVED", "ORDER_SHIPPED"])
        self.assertEqual(result["customers"]["C004"]["credit_used"], 0)
        self.assertEqual(result["products"]["P004"]["stock"], 5)

    def test_duplicate_customer_updates_credit_limit(self):
        """Test that duplicate customer creation updates existing credit limit."""
        ops = [
            ("CREATE_CUSTOMER", "C005", 1000),
            ("CREATE_CUSTOMER", "C005", 1500),
            ("QUERY_CUSTOMER", "C005")
        ]
        result = ecommerce_saga_processor(ops)
        self.assertEqual(result["customers"]["C005"]["credit_limit"], 1500)
        self.assertEqual(result["customers"]["C005"]["credit_used"], 0)

    def test_inject_failure_in_inventory_triggers_compensation(self):
        """Test injected failure at inventory triggers rollback compensation."""
        ops = [
            ("CREATE_CUSTOMER", "C006", 1000),
            ("ADD_PRODUCT", "P006", 3, 200),
            ("PLACE_ORDER", "C006", "P006", 2),
            ("INJECT_FAILURE", "INVENTORY", "O001"),
            ("QUERY_ORDER", "O001"),
            ("QUERY_CUSTOMER", "C006"),
            ("QUERY_PRODUCT", "P006")
        ]
        result = ecommerce_saga_processor(ops)
        order = result["orders"]["O001"]
        self.assertEqual(order["status"], "CANCELED")
        self.assertListEqual(order["events_completed"], ["ORDER_CREATED",
                                                        "PAYMENT_PROCESSED"])
        self.assertListEqual(order["compensation_events"],
                             ["PAYMENT_REFUNDED", "ORDER_CANCELED"])
        self.assertEqual(result["customers"]["C006"]["credit_used"], 0)
        self.assertEqual(result["products"]["P006"]["stock"], 3)

    def test_inject_failure_non_existent_order_id_ignored(self):
        """Test that injecting failure to unknown order ID is ignored silently."""
        ops = [
            ("CREATE_CUSTOMER", "C007", 500),
            ("ADD_PRODUCT", "P007", 10, 50),
            ("INJECT_FAILURE", "PAYMENT", "O999"),  # Non-existent order
            ("PLACE_ORDER", "C007", "P007", 1),
            ("QUERY_ORDER", "O001")
        ]
        result = ecommerce_saga_processor(ops)
        order = result["orders"]["O001"]
        self.assertEqual(order["status"], "SHIPPED")

    def test_order_for_non_existent_customer_fails_immediately(self):
        """Test order for missing customer fails with no saga initiated."""
        ops = [
            ("ADD_PRODUCT", "P008", 10, 100),
            ("PLACE_ORDER", "C999", "P008", 1),
            ("QUERY_ORDER", "O001")
        ]
        result = ecommerce_saga_processor(ops)
        self.assertNotIn("O001", result["orders"])

    def test_order_for_non_existent_product_fails_immediately(self):
        """Test order for missing product fails with no saga initiated."""
        ops = [
            ("CREATE_CUSTOMER", "C009", 1000),
            ("PLACE_ORDER", "C009", "P999", 1),
            ("QUERY_ORDER", "O001")
        ]
        result = ecommerce_saga_processor(ops)
        self.assertNotIn("O001", result["orders"])

    def test_multiple_orders_processed_independently(self):
        """Test that multiple orders process independently with correct states."""
        ops = [
            ("CREATE_CUSTOMER", "C010", 1000),
            ("CREATE_CUSTOMER", "C011", 500),
            ("ADD_PRODUCT", "P010", 10, 100),
            ("PLACE_ORDER", "C010", "P010", 5),
            ("PLACE_ORDER", "C011", "P010", 3),
            ("QUERY_ORDER", "O001"),
            ("QUERY_ORDER", "O002")
        ]
        result = ecommerce_saga_processor(ops)
        order1 = result["orders"]["O001"]
        order2 = result["orders"]["O002"]
        self.assertEqual(order1["status"], "SHIPPED")
        self.assertEqual(order2["status"], "SHIPPED")
        self.assertEqual(result["products"]["P010"]["stock"], 2)
        self.assertEqual(result["customers"]["C010"]["credit_used"], 500)
        self.assertEqual(result["customers"]["C011"]["credit_used"], 300)

    def test_credit_usage_releases_on_compensation(self):
        """Test that credit used is released on compensation after failure."""
        ops = [
            ("CREATE_CUSTOMER", "C012", 1000),
            ("ADD_PRODUCT", "P012", 2, 400),
            ("PLACE_ORDER", "C012", "P012", 5),
            ("INJECT_FAILURE", "INVENTORY", "O001"),
            ("QUERY_CUSTOMER", "C012")
        ]
        result = ecommerce_saga_processor(ops)
        self.assertEqual(result["customers"]["C012"]["credit_used"], 0)

    def test_order_ids_auto_increment(self):
        """Test that order IDs increment automatically as O001, O002, O003."""
        ops = [
            ("CREATE_CUSTOMER", "C014", 1000),
            ("ADD_PRODUCT", "P014", 10, 100),
            ("PLACE_ORDER", "C014", "P014", 1),
            ("PLACE_ORDER", "C014", "P014", 2),
            ("PLACE_ORDER", "C014", "P014", 3),
        ]
        result = ecommerce_saga_processor(ops)
        self.assertIn("O001", result["orders"])
        self.assertIn("O002", result["orders"])
        self.assertIn("O003", result["orders"])
        self.assertEqual(len(result["orders"]), 3)
