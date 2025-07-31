# tests

"""Test cases for Task 69980: AOP Log Error Handler."""

import unittest
from main import process_aspect_weaving


class TestAspectWeaving(unittest.TestCase):
    """Unit tests for AOP Aspect Weaving functionality."""

    def setUp(self):
        """Set up test fixtures."""
        self.maxDiff = None

    def tearDown(self):
        """Clean up resources."""
        pass

    def create_service(
        self, module_name, base_classes, class_definitions, method_aspects=None
    ):
        """Create a service definition."""
        return {
            "module_name": module_name,
            "base_classes": base_classes,
            "class_definitions": class_definitions,
            "method_aspects": method_aspects or {},
        }

    def create_pointcut(self, pointcut_id, expression, priority):
        """Create a pointcut definition."""
        return {
            "pointcut_id": pointcut_id,
            "expression": expression,
            "priority": priority,
        }

    def create_class_def(self, name, parents):
        """Create a class definition."""
        return {"name": name, "parents": parents}

    def assert_weave_result(self, result, expected):
        """Assert weaving results."""
        self.assertEqual(
            len(result),
            len(expected),
            f"Result length mismatch. Got {len(result)}, "
            f"expected {len(expected)}",
        )

        for i, (actual, expected_item) in enumerate(zip(result, expected)):
            self.assertEqual(
                actual,
                expected_item,
                f"Mismatch at index {i}: got '{actual}', "
                f"expected '{expected_item}'",
            )

    def get_auth_service_fixture(self):
        """Get authentication service fixture."""
        return self.create_service(
            module_name="auth_system",
            base_classes=["Authenticator", "Logger", "Validator"],
            class_definitions=[
                self.create_class_def(
                    "AuthHandler", ["Authenticator", "Logger"]
                ),
                self.create_class_def(
                    "SecureAuth", ["AuthHandler", "Validator"]
                ),
            ],
            method_aspects={
                "login": "security_aspect",
                "validate": "audit_aspect",
            },
        )

    def get_data_service_fixture(self):
        """Get data service fixture."""
        return self.create_service(
            module_name="data_system",
            base_classes=["DataAccess", "Monitor", "Cache"],
            class_definitions=[
                self.create_class_def("DataManager", ["DataAccess", "Monitor"])
            ],
            method_aspects={"read": "perf_aspect", "write": "perf_aspect"},
        )

    def get_standard_pointcuts(self):
        """Get standard pointcut fixtures."""
        return [
            self.create_pointcut("security_check", "auth_system.*login*", 1),
            self.create_pointcut("audit_trail", "*validate*", 2),
            self.create_pointcut(
                "performance_monitor", "data_system.*read*|*write*", 3
            ),
        ]

    def test_basic_functionality_with_multiple_services_and_priorities(self):
        """Test basic aspect weaving with multiple services."""
        services = [
            self.get_auth_service_fixture(),
            self.get_data_service_fixture(),
        ]
        pointcuts = self.get_standard_pointcuts()
        execution_events = [
            "auth_system.AuthHandler.login",
            "auth_system.SecureAuth.validate",
            "data_system.DataManager.read",
            "auth_system.SecureAuth.login",
            "data_system.DataManager.write",
        ]
        expected = [
            "WEAVE: security_check[1] -> TARGET[login]",
            "WEAVE: audit_trail[2] -> TARGET[validate]",
            "WEAVE: performance_monitor[3] -> TARGET[read]",
            "WEAVE: security_check[1] -> TARGET[login]",
            "WEAVE: performance_monitor[3] -> TARGET[write]",
        ]

        result = process_aspect_weaving(services, pointcuts, execution_events)

        self.assert_weave_result(result, expected)

    def test_multiple_aspects_with_different_priorities_ordered_correctly(
        self,
    ):
        """Test multiple aspects with different priorities."""
        services = [
            self.create_service(
                module_name="priority_system",
                base_classes=["TestBase"],
                class_definitions=[
                    self.create_class_def("TestService", ["TestBase"])
                ],
                method_aspects={"execute": "test_aspect"},
            )
        ]
        pointcuts = [
            self.create_pointcut("low_priority", "*execute*", 5),
            self.create_pointcut("high_priority", "*execute*", 1),
            self.create_pointcut("mid_priority", "*execute*", 3),
        ]
        execution_events = ["priority_system.TestService.execute"]
        expected = [
            "WEAVE: high_priority[1] -> mid_priority[3] -> "
            "low_priority[5] -> TARGET[execute]"
        ]

        result = process_aspect_weaving(services, pointcuts, execution_events)

        self.assert_weave_result(result, expected)

    def test_same_priority_aspects_use_alphabetical_order(self):
        """Test aspects with same priority alphabetical order."""
        services = [
            self.create_service(
                module_name="alpha_system",
                base_classes=["AlphaBase"],
                class_definitions=[
                    self.create_class_def("AlphaService", ["AlphaBase"])
                ],
                method_aspects={"process": "alpha_aspect"},
            )
        ]
        pointcuts = [
            self.create_pointcut("zebra_aspect", "*process*", 2),
            self.create_pointcut("alpha_aspect", "*process*", 2),
            self.create_pointcut("beta_aspect", "*process*", 2),
        ]
        execution_events = ["alpha_system.AlphaService.process"]
        expected = [
            "WEAVE: alpha_aspect[2] -> beta_aspect[2] -> "
            "zebra_aspect[2] -> TARGET[process]"
        ]

        result = process_aspect_weaving(services, pointcuts, execution_events)

        self.assert_weave_result(result, expected)

    def test_diamond_inheritance_resolves_mro_correctly(self):
        """Test diamond inheritance pattern resolves correctly."""
        services = [
            self.create_service(
                module_name="diamond_system",
                base_classes=["BaseA", "BaseB", "BaseC", "BaseD"],
                class_definitions=[
                    self.create_class_def("MiddleB", ["BaseA"]),
                    self.create_class_def("MiddleC", ["BaseA"]),
                    self.create_class_def(
                        "DiamondTop", ["MiddleB", "MiddleC"]
                    ),
                ],
                method_aspects={"process": "diamond_aspect"},
            )
        ]
        pointcuts = [
            self.create_pointcut(
                "diamond_weave", "diamond_system.*process*", 1
            )
        ]
        execution_events = ["diamond_system.DiamondTop.process"]
        expected = ["WEAVE: diamond_weave[1] -> TARGET[process]"]

        result = process_aspect_weaving(services, pointcuts, execution_events)

        self.assert_weave_result(result, expected)

    def test_method_override_in_inheritance_hierarchy(self):
        """Test method resolution when child overrides parent."""
        services = [
            self.create_service(
                module_name="override_system",
                base_classes=["ParentService", "ChildService"],
                class_definitions=[
                    self.create_class_def("ParentService", []),
                    self.create_class_def("ChildService", ["ParentService"]),
                ],
                method_aspects={"commonMethod": "override_aspect"},
            )
        ]
        pointcuts = [
            self.create_pointcut(
                "parent_advice", "override_system.ParentService.*", 1
            ),
            self.create_pointcut(
                "child_advice", "override_system.ChildService.*", 2
            ),
        ]
        execution_events = [
            "override_system.ParentService.commonMethod",
            "override_system.ChildService.commonMethod",
        ]
        expected = [
            "WEAVE: parent_advice[1] -> TARGET[commonMethod]",
            "WEAVE: child_advice[2] -> TARGET[commonMethod]",
        ]

        result = process_aspect_weaving(services, pointcuts, execution_events)

        self.assert_weave_result(result, expected)

    def test_complex_pointcut_expressions_with_wildcards_and_or(self):
        """Test complex pointcut expressions with wildcards."""
        services = [
            self.create_service(
                module_name="complex_system",
                base_classes=["ComplexBase"],
                class_definitions=[
                    self.create_class_def("ComplexService", ["ComplexBase"])
                ],
                method_aspects={
                    "auth_login": "auth_aspect",
                    "validate_user": "validation_aspect",
                    "user_authenticate": "auth_aspect",
                    "process_data": "data_aspect",
                },
            )
        ]
        pointcuts = [
            self.create_pointcut(
                "multi_pattern", "*auth*|*login*|validate_*", 1
            ),
            self.create_pointcut("wildcard_start", "complex_*", 2),
            self.create_pointcut("wildcard_end", "*_data", 3),
        ]
        execution_events = [
            "complex_system.ComplexService.auth_login",
            "complex_system.ComplexService.validate_user",
            "complex_system.ComplexService.process_data",
            "complex_system.ComplexService.user_authenticate",
        ]
        expected = [
            "WEAVE: multi_pattern[1] -> wildcard_start[2] -> "
            "TARGET[auth_login]",
            "WEAVE: multi_pattern[1] -> wildcard_start[2] -> "
            "TARGET[validate_user]",
            "WEAVE: wildcard_start[2] -> wildcard_end[3] -> "
            "TARGET[process_data]",
            "WEAVE: multi_pattern[1] -> wildcard_start[2] -> "
            "TARGET[user_authenticate]",
        ]

        result = process_aspect_weaving(services, pointcuts, execution_events)

        self.assert_weave_result(result, expected)

    def test_no_matching_pointcuts_returns_direct_execution(self):
        """Test method execution when no pointcuts match."""
        services = [
            self.create_service(
                module_name="direct_system",
                base_classes=["DirectBase"],
                class_definitions=[
                    self.create_class_def("DirectService", ["DirectBase"])
                ],
                method_aspects={"unmatchedMethod": "unused_aspect"},
            )
        ]
        pointcuts = [
            self.create_pointcut("other_pattern", "other_system.*login*", 1),
            self.create_pointcut("different_pattern", "*validate*", 2),
        ]
        execution_events = ["direct_system.DirectService.unmatchedMethod"]
        expected = ["DIRECT: TARGET[unmatchedMethod]"]

        result = process_aspect_weaving(services, pointcuts, execution_events)

        self.assert_weave_result(result, expected)

    def test_invalid_pointcut_expressions_are_skipped(self):
        """Test malformed pointcut expressions are skipped."""
        services = [
            self.create_service(
                module_name="invalid_system",
                base_classes=["TestBase"],
                class_definitions=[
                    self.create_class_def("TestService", ["TestBase"])
                ],
                method_aspects={"testMethod": "valid_aspect"},
            )
        ]
        pointcuts = [
            self.create_pointcut(
                "invalid_wildcard", "**invalid**pattern**", 1
            ),
            self.create_pointcut("malformed_or", "pattern1||pattern2", 2),
            self.create_pointcut("valid_pattern", "*test*", 3),
        ]
        execution_events = ["invalid_system.TestService.testMethod"]
        expected = ["WEAVE: valid_pattern[3] -> TARGET[testMethod]"]

        result = process_aspect_weaving(services, pointcuts, execution_events)

        self.assert_weave_result(result, expected)

    def test_missing_method_returns_error(self):
        """Test execution event for non-existent method."""
        services = [
            self.create_service(
                module_name="error_system",
                base_classes=["ErrorBase"],
                class_definitions=[
                    self.create_class_def("ErrorHandler", ["ErrorBase"])
                ],
                method_aspects={"valid_method": "test_aspect"},
            )
        ]
        pointcuts = [self.create_pointcut("any_method", "*", 1)]
        execution_events = ["error_system.ErrorHandler.nonexistent_method"]
        expected = ["ERROR: METHOD_NOT_FOUND"]

        result = process_aspect_weaving(services, pointcuts, execution_events)

        self.assert_weave_result(result, expected)

    def test_circular_inheritance_returns_error(self):
        """Test circular dependency in inheritance."""
        services = [
            self.create_service(
                module_name="circular_system",
                base_classes=["CircularA", "CircularB"],
                class_definitions=[
                    self.create_class_def("CircularA", ["CircularB"]),
                    self.create_class_def("CircularB", ["CircularA"]),
                ],
                method_aspects={"method": "circular_aspect"},
            )
        ]
        pointcuts = [self.create_pointcut("any_aspect", "*", 1)]
        execution_events = ["circular_system.CircularA.method"]
        expected = ["ERROR: CIRCULAR_INHERITANCE"]

        result = process_aspect_weaving(services, pointcuts, execution_events)

        self.assert_weave_result(result, expected)

    def test_maximum_constraints_within_limits(self):
        """Test system handles maximum constraint values."""
        services = [
            self.create_service(
                module_name="max_constraint_system_name",
                base_classes=[
                    "BaseA",
                    "BaseB",
                    "BaseC",
                    "BaseD",
                    "BaseE",
                ],
                class_definitions=[
                    self.create_class_def(
                        "MaxConstraintClass", ["BaseA", "BaseB", "BaseC"]
                    )
                ],
                method_aspects={
                    "method_with_15char": "aspect_with_25characters"
                },
            )
        ]
        pointcuts = [self.create_pointcut("high_priority", "*method*", 10)]
        execution_events = [
            "max_constraint_system_name.MaxConstraintClass.method_with_15char"
        ]
        expected = ["WEAVE: high_priority[10] -> TARGET[method_with_15char]"]

        result = process_aspect_weaving(services, pointcuts, execution_events)

        self.assert_weave_result(result, expected)

    def test_empty_input_lists_return_empty_result(self):
        """Test empty input lists return empty result."""
        services = []
        pointcuts = []
        execution_events = []
        expected = []

        result = process_aspect_weaving(services, pointcuts, execution_events)

        self.assert_weave_result(result, expected)

    def test_pointcut_with_maximum_or_patterns(self):
        """Test pointcut expressions with maximum OR patterns."""
        services = [
            self.create_service(
                module_name="max_or_system",
                base_classes=["MaxBase"],
                class_definitions=[
                    self.create_class_def("MaxService", ["MaxBase"])
                ],
                method_aspects={"pattern1_method": "max_aspect"},
            )
        ]
        pointcuts = [
            self.create_pointcut(
                "max_or_patterns",
                "pattern1*|pattern2*|pattern3*|pattern4*|pattern5*",
                1,
            )
        ]
        execution_events = ["max_or_system.MaxService.pattern1_method"]
        expected = ["WEAVE: max_or_patterns[1] -> TARGET[pattern1_method]"]

        result = process_aspect_weaving(services, pointcuts, execution_events)

        self.assert_weave_result(result, expected)


if __name__ == "__main__":
    unittest.main()
