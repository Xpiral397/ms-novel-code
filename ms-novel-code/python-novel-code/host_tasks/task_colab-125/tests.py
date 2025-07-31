# tests

"""
Control Flow Analyzer Test Suite.

Target Model: GPT-4o (Model Breaking)
Focus: Security vulnerability detection in code analysis
"""

import unittest
from main import analyze_control_flow


class TestControlFlowAnalyzer(unittest.TestCase):
    """Test suite for control flow analyzer with security focus."""

    def test_example_unreachable_code(self):
        """Example 1: Unreachable code after if/else returns."""
        source = [
            "def calculate(x):",
            "    if x > 0:",
            "        return x * 2",
            "    else:",
            "        return 0",
            "    print('unreachable')",
        ]
        self.assertEqual(analyze_control_flow(source), (5, 2, 2, 4, "FINITE"))

    def test_example_complex_nesting(self):
        """Example 2: Complex nested control structures."""
        source = [
            "def process_data(items):",
            "    for item in items:",
            "        if not item:",
            "            continue",
            "        try:",
            "            result = item.process()",
            "        except:",
            "            pass",
            "    return 'done'",
        ]
        self.assertEqual(
            analyze_control_flow(source), (8, 4, 3, "NONE", "FINITE")
        )

    def test_example_infinite_loop(self):
        """Example 3: Infinite loop with incrementing variable."""
        source = [
            "def loop_test():",
            "    x = 1",
            "    while x > 0:",
            "        x += 1",
            "    return x",
        ]
        self.assertEqual(
            analyze_control_flow(source), (5, 1, 2, "NONE", "INFINITE")
        )

    def test_basic_simple_function(self):
        """Basic function with no control structures."""
        source = ["def simple():", "    x = 42", "    return x"]
        self.assertEqual(
            analyze_control_flow(source), (3, 0, 1, "NONE", "FINITE")
        )

    def test_basic_empty_function(self):
        """Empty function with pass statement."""
        source = ["def empty():", "    pass"]
        self.assertEqual(
            analyze_control_flow(source), (2, 0, 1, "NONE", "FINITE")
        )

    def test_exception_bypass_paths(self):
        """Exception bypass paths detection (security vulnerability)."""
        source = [
            "def risky_function():",
            "    try:",
            "        dangerous_operation()",
            "        return 'success'",
            "    except:",
            "        pass",
            "    return 'failed'",
        ]
        result = analyze_control_flow(source)
        self.assertIsInstance(result, tuple)
        self.assertEqual(len(result), 5)

    def test_nested_exception_types(self):
        """Nested try/except blocks with different exception types."""
        source = [
            "def complex_exception():",
            "    try:",
            "        try:",
            "            risky_operation()",
            "        except ValueError:",
            "            handle_value_error()",
            "    except TypeError:",
            "        handle_type_error()",
            "    return 'done'",
        ]
        result = analyze_control_flow(source)
        decision_points, max_depth = result[1], result[2]
        self.assertGreaterEqual(decision_points, 2)
        self.assertGreaterEqual(max_depth, 3)

    def test_decision_if_elif_else(self):
        """If/elif/else decision points counting."""
        source = [
            "def grade(score):",
            "    if score >= 90:",
            "        return 'A'",
            "    elif score >= 80:",
            "        return 'B'",
            "    else:",
            "        return 'F'",
        ]
        result = analyze_control_flow(source)
        self.assertEqual(result[1], 3)

    def test_decision_nested_loops(self):
        """Nested for loops with depth calculation."""
        source = [
            "def nested():",
            "    for i in range(2):",
            "        for j in range(2):",
            "            print(i, j)",
            "    return 'done'",
        ]
        result = analyze_control_flow(source)
        self.assertEqual(result[2], 3)

        """Try/except/finally as decision points."""
        source = [
            "def error_handling():",
            "    try:",
            "        risky()",
            "    except ValueError:",
            "        handle_error()",
            "    finally:",
            "        cleanup()",
            "    return 'done'",
        ]
        result = analyze_control_flow(source)
        self.assertGreaterEqual(result[1], 2)

    def test_unreachable_after_return(self):
        """Code unreachable after return statement."""
        source = [
            "def early_return():",
            "    return 'early'",
            "    print('unreachable')",
        ]
        self.assertEqual(analyze_control_flow(source), (3, 0, 1, 2, "FINITE"))

        """Code unreachable after raise statement."""
        source = [
            "def error_func():",
            "    raise ValueError('error')",
            "    return 'unreachable'",
        ]
        self.assertEqual(analyze_control_flow(source), (3, 0, 1, 2, "FINITE"))

    def test_infinite_while_true(self):
        """While True infinite loop detection."""
        source = [
            "def infinite():",
            "    while True:",
            "        print('forever')",
            "    return 'never'",
        ]
        self.assertEqual(
            analyze_control_flow(source), (4, 1, 2, "NONE", "INFINITE")
        )

    def test_infinite_finite_decrementing(self):
        """Finite loop with decrementing variable (contrast test)."""
        source = [
            "def countdown():",
            "    x = 10",
            "    while x > 0:",
            "        x -= 1",
            "    return x",
        ]
        self.assertEqual(
            analyze_control_flow(source), (5, 1, 2, "NONE", "FINITE")
        )

    def test_edge_empty_classes(self):
        """Empty classes should be ignored."""
        source = [
            "class EmptyClass:",
            "    pass",
            "class AnotherClass:",
            "    def method(self):",
            "        pass",
            "def actual_function():",
            "    return 42",
        ]
        result = analyze_control_flow(source)
        self.assertLessEqual(result[0], 3)

    def test_edge_break_continue_control(self):
        """Break and continue loop control statements."""
        source = [
            "def loop_controls():",
            "    for i in range(10):",
            "        if i == 5:",
            "            break",
            "        if i % 2 == 0:",
            "            continue",
            "        print(i)",
        ]
        result = analyze_control_flow(source)
        self.assertGreaterEqual(result[1], 2)

    def test_edge_multiple_functions(self):
        """Multiple function definitions in same input."""
        source = [
            "def first_function():",
            "    return 1",
            "def second_function():",
            "    if True:",
            "        return 2",
            "    return 0",
        ]
        result = analyze_control_flow(source)
        self.assertGreaterEqual(result[0], 5)

    def test_edge_empty_input(self):
        """Empty input handling."""
        self.assertEqual(analyze_control_flow([]), (0, 0, 0, "NONE", "FINITE"))

    def test_edge_module_level_ignored(self):
        """Module-level code should be ignored."""
        source = [
            "import os",
            "x = 42",
            "print('module level')",
            "def actual_function():",
            "    return x",
        ]
        result = analyze_control_flow(source)
        self.assertLessEqual(result[0], 3)

    def test_edge_syntax_error(self):
        """Graceful handling of syntax errors."""
        source = ["def broken():", "    if x > 0", "        return x"]
        result = analyze_control_flow(source)

        self.assertIsInstance(result, tuple)
        self.assertEqual(len(result), 5)
        (
            blocks_count,
            decision_points,
            max_depth,
            unreachable_blocks,
            loop_status,
        ) = result
        self.assertIsInstance(blocks_count, int)
        self.assertIsInstance(decision_points, int)
        self.assertIsInstance(max_depth, int)
        self.assertIn(type(unreachable_blocks), [int, str])
        if isinstance(unreachable_blocks, str):
            self.assertEqual(unreachable_blocks, "NONE")
        self.assertIn(loop_status, ["INFINITE", "FINITE"])


if __name__ == "__main__":
    unittest.main(verbosity=2)
