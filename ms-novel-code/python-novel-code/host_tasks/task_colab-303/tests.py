# tests

"""Comprehensive test suite for CQRS restaurant order management system."""

import unittest
from main import process_restaurant_operations


class TestRestaurantOperations(unittest.TestCase):
    """Test cases for restaurant operations management system."""

    def test_example_1_from_problem(self):
        """Test the first example from problem statement."""
        operations = [
            ("PLACE_ORDER", "ORD001", "Alice", "Margherita", 2),
            ("GET_PENDING_ORDERS"),
            ("COMPLETE_ORDER", "ORD001"),
            ("GET_TOTAL_REVENUE"),
        ]
        result = process_restaurant_operations(operations)
        self.assertEqual(result, [["ORD001"], 25.98])

    def test_example_2_from_problem(self):
        """Test the second example from problem statement."""
        operations = [
            ("PLACE_ORDER", "ORD001", "Bob", "Pepperoni", 1),
            ("PLACE_ORDER", "ORD002", "Carol", "Vegetarian", 3),
            ("GET_ORDER_COUNT"),
            ("COMPLETE_ORDER", "ORD001"),
            ("GET_PENDING_ORDERS"),
            ("GET_TOTAL_REVENUE"),
        ]
        result = process_restaurant_operations(operations)
        self.assertEqual(result, [2, ["ORD002"], 15.99])

    def test_empty_system_queries(self):
        """Test query operations on empty system."""
        operations = [
            ("GET_PENDING_ORDERS"),
            ("GET_TOTAL_REVENUE"),
            ("GET_ORDER_COUNT"),
        ]
        result = process_restaurant_operations(operations)
        self.assertEqual(result, [[], 0.0, 0])

    def test_all_pizza_types_pricing(self):
        """Test each pizza type has correct pricing."""
        test_cases = [
            ("Margherita", 12.99, "ORD_MAR"),
            ("Pepperoni", 15.99, "ORD_PEP"),
            ("Vegetarian", 14.99, "ORD_VEG"),
            ("Hawaiian", 16.99, "ORD_HAW"),
        ]

        for pizza_type, expected_price, order_id in test_cases:
            operations = [
                ("PLACE_ORDER", order_id, "TestCustomer", pizza_type, 1),
                ("COMPLETE_ORDER", order_id),
                ("GET_TOTAL_REVENUE"),
            ]
            result = process_restaurant_operations(operations)
            self.assertEqual(
                result,
                [expected_price],
                f"Failed for {pizza_type}: expected {expected_price}, "
                f"got {result[0]}",
            )

    def test_quantity_multiplication(self):
        """Test revenue calculation with different quantities."""
        operations = [
            ("PLACE_ORDER", "ORD001", "Alice", "Margherita", 3),
            ("COMPLETE_ORDER", "ORD001"),
            ("GET_TOTAL_REVENUE"),
        ]
        result = process_restaurant_operations(operations)
        self.assertAlmostEqual(result[0], 38.97, places=2)

    def test_duplicate_order_id_raises_error(self):
        """Test that duplicate order IDs raise ValueError."""
        operations = [
            ("PLACE_ORDER", "ORD001", "Alice", "Margherita", 1),
            ("PLACE_ORDER", "ORD001", "Bob", "Pepperoni", 2),
        ]
        with self.assertRaises(ValueError):
            process_restaurant_operations(operations)

    def test_invalid_pizza_type_raises_error(self):
        """Test that invalid pizza type raises ValueError."""
        operations = [("PLACE_ORDER", "ORD001", "Alice", "InvalidPizza", 1)]
        with self.assertRaises(ValueError):
            process_restaurant_operations(operations)

    def test_complete_nonexistent_order_raises_error(self):
        """Test completing non-existent order raises ValueError."""
        operations = [("COMPLETE_ORDER", "NONEXISTENT")]
        with self.assertRaises(ValueError):
            process_restaurant_operations(operations)

    def test_complete_already_completed_order_raises_error(self):
        """Test completing already completed order raises ValueError."""
        operations = [
            ("PLACE_ORDER", "ORD001", "Alice", "Margherita", 1),
            ("COMPLETE_ORDER", "ORD001"),
            ("COMPLETE_ORDER", "ORD001"),
        ]
        with self.assertRaises(ValueError):
            process_restaurant_operations(operations)

    def test_zero_quantity_raises_error(self):
        """Test zero quantity raises ValueError."""
        operations = [("PLACE_ORDER", "ORD001", "Alice", "Margherita", 0)]
        with self.assertRaises(ValueError):
            process_restaurant_operations(operations)

    def test_negative_quantity_raises_error(self):
        """Test negative quantity raises ValueError."""
        operations = [("PLACE_ORDER", "ORD001", "Bob", "Pepperoni", -1)]
        with self.assertRaises(ValueError):
            process_restaurant_operations(operations)

    def test_quantity_exceeding_limit_raises_error(self):
        """Test quantity exceeding limit (5) raises ValueError."""
        operations = [("PLACE_ORDER", "ORD001", "Carol", "Vegetarian", 6)]
        with self.assertRaises(ValueError):
            process_restaurant_operations(operations)

    def test_valid_quantity_range(self):
        """Test valid quantity range (1-5)."""
        for quantity in range(1, 6):
            operations = [
                (
                    "PLACE_ORDER",
                    f"ORD{quantity}",
                    "Test",
                    "Margherita",
                    quantity,
                ),
                ("GET_ORDER_COUNT"),
            ]
            result = process_restaurant_operations(operations)
            self.assertEqual(result, [1])

    def test_pending_orders_dont_affect_revenue(self):
        """Test that only completed orders contribute to revenue."""
        operations = [
            ("PLACE_ORDER", "ORD001", "Alice", "Margherita", 2),
            ("PLACE_ORDER", "ORD002", "Bob", "Pepperoni", 1),
            ("GET_TOTAL_REVENUE"),
            ("COMPLETE_ORDER", "ORD001"),
            ("GET_TOTAL_REVENUE"),
            ("COMPLETE_ORDER", "ORD002"),
            ("GET_TOTAL_REVENUE"),
        ]
        result = process_restaurant_operations(operations)
        self.assertEqual(result, [0.0, 25.98, 41.97])

    def test_order_count_includes_all_orders(self):
        """Test order count includes both pending and completed orders."""
        operations = [
            ("PLACE_ORDER", "ORD001", "Alice", "Margherita", 1),
            ("PLACE_ORDER", "ORD002", "Bob", "Pepperoni", 1),
            ("GET_ORDER_COUNT"),
            ("COMPLETE_ORDER", "ORD001"),
            ("GET_ORDER_COUNT"),
        ]
        result = process_restaurant_operations(operations)
        self.assertEqual(result, [2, 2])

    def test_pending_orders_tracking(self):
        """Test pending orders are tracked correctly."""
        operations = [
            ("PLACE_ORDER", "ORD001", "Alice", "Margherita", 1),
            ("PLACE_ORDER", "ORD002", "Bob", "Pepperoni", 1),
            ("PLACE_ORDER", "ORD003", "Carol", "Hawaiian", 1),
            ("GET_PENDING_ORDERS"),
            ("COMPLETE_ORDER", "ORD002"),
            ("GET_PENDING_ORDERS"),
            ("COMPLETE_ORDER", "ORD001"),
            ("GET_PENDING_ORDERS"),
        ]
        result = process_restaurant_operations(operations)
        self.assertEqual(
            result,
            [["ORD001", "ORD002", "ORD003"], ["ORD001", "ORD003"], ["ORD003"]],
        )

    def test_complex_workflow(self):
        """Test complex workflow with multiple operations."""
        operations = [
            ("PLACE_ORDER", "ORD001", "Alice", "Margherita", 2),
            ("PLACE_ORDER", "ORD002", "Bob", "Hawaiian", 1),
            ("PLACE_ORDER", "ORD003", "Carol", "Vegetarian", 3),
            ("GET_ORDER_COUNT"),
            ("GET_PENDING_ORDERS"),
            ("COMPLETE_ORDER", "ORD001"),
            ("GET_TOTAL_REVENUE"),
            ("COMPLETE_ORDER", "ORD003"),
            ("GET_PENDING_ORDERS"),
            ("GET_TOTAL_REVENUE"),
            ("GET_ORDER_COUNT"),
        ]
        result = process_restaurant_operations(operations)
        expected = [
            3,
            ["ORD001", "ORD002", "ORD003"],
            25.98,
            ["ORD002"],
            70.95,
            3,
        ]
        self.assertEqual(result, expected)

    def test_decimal_precision(self):
        """Test decimal precision in revenue calculations."""
        operations = [
            ("PLACE_ORDER", "ORD001", "Alice", "Hawaiian", 5),
            ("COMPLETE_ORDER", "ORD001"),
            ("GET_TOTAL_REVENUE"),
        ]
        result = process_restaurant_operations(operations)
        self.assertEqual(result, [84.95])

    def test_no_write_operations_returns_empty_list(self):
        """Test that operations with only write commands return empty list."""
        operations = [
            ("PLACE_ORDER", "ORD001", "Alice", "Margherita", 1),
            ("COMPLETE_ORDER", "ORD001"),
        ]
        result = process_restaurant_operations(operations)
        self.assertEqual(result, [])


if __name__ == "__main__":
    unittest.main()
