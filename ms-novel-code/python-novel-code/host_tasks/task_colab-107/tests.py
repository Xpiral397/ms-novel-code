# tests


import unittest

from main import generate_code_from_query, NeuralCodeGenerator


class TestCodeGenerationFramework(unittest.TestCase):
    """Comprehensive tests for code generation and NeuralCodeGenerator edge cases."""

    def setUp(self):
        # Contexts and examples for example tests
        self.context1 = {
            "tables": {
                "Customers": ["CustomerID", "Name"],
                "Orders": ["OrderID", "CustomerID", "Revenue"]
            },
            "foreign_keys": {
                "Orders.CustomerID": "Customers.CustomerID"
            }
        }
        self.examples1 = [
            {
                "query": "Show all orders with revenue above 500",
                "code": "fcol('Orders', 'OrderID')[fval('Orders', 'Revenue') > 500]"
            },
            {
                "query": "List names of customers from France",
                "code": "fcol('Customers', 'Name')[fval('Customers', 'Country') == 'France']"
            }
        ]
        self.query1 = "List the names of customers who placed orders above $1000."
        self.expected_code1 = (
            "fcol('Customers', 'Name')["
            "fjoin('Customers', 'Orders', on='CustomerID')['Revenue'] > 1000]"
        )

        self.context2 = {
            "tables": {
                "Orders": ["OrderID", "CustomerID", "OrderDate"]
            },
            "foreign_keys": {}
        }
        self.examples2 = [
            {
                "query": "Find orders placed in 2024",
                "code": "fcol('Orders', 'OrderID')[fval('Orders', 'OrderDate').year == 2024]"
            },
            {
                "query": "Total number of orders",
                "code": "len(fcol('Orders', 'OrderID'))"
            }
        ]
        self.query2 = "Count the number of orders made in 2024."
        self.expected_code2 = (
            "len(fcol('Orders', 'OrderID')["
            "fval('Orders', 'OrderDate').year == 2024])"
        )

    def test_generate_example1(self):
        """Example 1: join and filter by revenue > 1000."""
        result = generate_code_from_query(
            self.query1, self.context1, self.examples1
        )
        self.assertEqual(result["generated_code"], self.expected_code1)
        self.assertListEqual(result["used_tables"], ["Customers", "Orders"])
        self.assertDictEqual(
            result["used_columns"],
            {"Customers": ["Name", "CustomerID"],
             "Orders": ["Revenue", "CustomerID"]}
        )
        self.assertIn("Joins Customers and Orders", result["explanation"])

    def test_generate_example2(self):
        """Example 2: count orders in 2024."""
        result = generate_code_from_query(
            self.query2, self.context2, self.examples2
        )
        self.assertEqual(result["generated_code"], self.expected_code2)
        self.assertListEqual(result["used_tables"], ["Orders"])
        self.assertDictEqual(
            result["used_columns"],
            {"Orders": ["OrderID", "OrderDate"]}
        )
        self.assertIn("Counts the number of orders", result["explanation"])

    def test_parse_query_empty(self):
        """Empty USER_QUERY should raise ValueError."""
        gen = NeuralCodeGenerator(self.context2, self.examples2)
        with self.assertRaises(ValueError):
            gen.parse_query("")

    def test_parse_query_unknown_table(self):
        """Query referencing non-existent table should error."""
        gen = NeuralCodeGenerator(self.context1, self.examples1)
        with self.assertRaises(ValueError):
            gen.parse_query("Show me records from NonExistent")

    def test_extract_used_fields_simple(self):
        """extract_used_fields should list single table and its cols."""
        gen = NeuralCodeGenerator(self.context2, self.examples2)
        code = "fcol('Orders', 'OrderID')[fval('Orders', 'OrderDate').year == 2024]"
        tables, cols = gen.extract_used_fields(code)
        self.assertListEqual(tables, ["Orders"])
        self.assertDictEqual(cols, {"Orders": ["OrderID", "OrderDate"]})

    def test_extract_used_fields_join(self):
        """extract_used_fields should detect both tables in join code."""
        gen = NeuralCodeGenerator(self.context1, self.examples1)
        code = ("fcol('Customers', 'Name')["
                "fjoin('Customers', 'Orders', on='CustomerID')['Revenue'] > 1000]")
        tables, cols = gen.extract_used_fields(code)
        self.assertCountEqual(tables, ["Customers", "Orders"])
        self.assertDictEqual(
            cols,
            {"Customers": ["Name", "CustomerID"],
             "Orders": ["Revenue", "CustomerID"]}
        )

    def test_explain_code_counts(self):
        """explain_code should describe counting logic."""
        gen = NeuralCodeGenerator(self.context2, self.examples2)
        code = self.expected_code2
        explanation = gen.explain_code(code)
        self.assertTrue(explanation.lower().startswith("counts the number of orders"))
        self.assertIn("2024", explanation)

    def test_explain_code_joins(self):
        """explain_code should describe join-based filter."""
        gen = NeuralCodeGenerator(self.context1, self.examples1)
        code = self.expected_code1
        explanation = gen.explain_code(code)
        self.assertIn("Customers and Orders", explanation)
        self.assertIn("Revenue > 1000", explanation)

    def test_context_malformed(self):
        """Missing 'tables' key in context should raise ValueError."""
        bad_context = {"foreign_keys": {}}
        with self.assertRaises(ValueError):
            generate_code_from_query("Any query", bad_context, self.examples1)

    def test_ambiguous_column(self):
        """Ambiguous column name across tables should raise ValueError."""
        context = {
            "tables": {
                "A": ["ID", "Value"],
                "B": ["ID", "Other"]
            },
            "foreign_keys": {}
        }
        with self.assertRaises(ValueError):
            generate_code_from_query("Show me ID", context, self.examples1)

    def test_large_input_truncation(self):
        """Excessively long USER_QUERY should raise ValueError."""
        long_query = "A" * 3000
        with self.assertRaises(ValueError):
            generate_code_from_query(long_query, self.context1, self.examples1)

    def test_deterministic_output(self):
        """generate_code_from_query should be deterministic."""
        res1 = generate_code_from_query(
            self.query2, self.context2, self.examples2
        )
        res2 = generate_code_from_query(
            self.query2, self.context2, self.examples2
        )
        self.assertEqual(res1, res2)


if __name__ == "__main__":
    unittest.main()
