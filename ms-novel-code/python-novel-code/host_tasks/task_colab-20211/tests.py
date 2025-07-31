# tests

"""Test module for RBAC system"""

import unittest
from main import load_authorization_rules, is_action_allowed


class TestRBACAuthorization(unittest.TestCase):
    """Unit tests for role-based access control functionality."""

    def setUp(self):
        """Load a base configuration for common tests."""
        self.config = {
            "admin": ["create", "read", "update", "delete"],
            "editor": ["read", "update"],
            "viewer": ["read"],
            "guest": []
        }
        load_authorization_rules(self.config)

    def test_admin_has_all_permissions(self):
        """Test that admin can perform all CRUD operations."""
        self.assertTrue(is_action_allowed("admin", "create"))
        self.assertTrue(is_action_allowed("admin", "read"))
        self.assertTrue(is_action_allowed("admin", "update"))
        self.assertTrue(is_action_allowed("admin", "delete"))

    def test_editor_has_read_and_update(self):
        """Test that editor has access to read and update only."""
        self.assertTrue(is_action_allowed("editor", "read"))
        self.assertTrue(is_action_allowed("editor", "update"))

    def test_editor_cannot_create_or_delete(self):
        """Test that editor cannot create or delete."""
        self.assertFalse(is_action_allowed("editor", "create"))
        self.assertFalse(is_action_allowed("editor", "delete"))

    def test_viewer_can_only_read(self):
        """Test that viewer can only perform the read action."""
        self.assertTrue(is_action_allowed("viewer", "read"))
        self.assertFalse(is_action_allowed("viewer", "update"))
        self.assertFalse(is_action_allowed("viewer", "delete"))

    def test_guest_has_no_permissions(self):
        """Test that a role with empty permissions returns False."""
        self.assertFalse(is_action_allowed("guest", "read"))
        self.assertFalse(is_action_allowed("guest", "create"))

    def test_undefined_role_returns_false(self):
        """Test that an undefined role always returns False."""
        self.assertFalse(is_action_allowed("superuser", "read"))

    def test_undefined_action_for_valid_role_returns_false(self):
        """Test that a valid role cannot perform undefined action."""
        self.assertFalse(is_action_allowed("viewer", "publish"))

    def test_case_sensitivity_of_role_names(self):
        """Test that role names are case-sensitive."""
        self.assertFalse(is_action_allowed("Admin", "read"))
        self.assertTrue(is_action_allowed("admin", "read"))

    def test_case_sensitivity_of_action_names(self):
        """Test that action names are case-sensitive."""
        self.assertFalse(is_action_allowed("admin", "Read"))
        self.assertTrue(is_action_allowed("admin", "read"))

    def test_empty_configuration_denies_all_access(self):
        """Test behavior when empty configuration is loaded."""
        load_authorization_rules({})
        self.assertFalse(is_action_allowed("admin", "read"))
        self.assertFalse(is_action_allowed("editor", "update"))

    def test_new_config_overwrites_previous_one(self):
        """Test that loading a new config replaces the old one."""
        new_config = {"user": ["view"]}
        load_authorization_rules(new_config)
        self.assertTrue(is_action_allowed("user", "view"))
        self.assertFalse(is_action_allowed("admin", "read"))

    def test_role_with_only_one_action(self):
        """Test a role that is allowed to perform only one action."""
        config = {"analyst": ["read"]}
        load_authorization_rules(config)
        self.assertTrue(is_action_allowed("analyst", "read"))
        self.assertFalse(is_action_allowed("analyst", "update"))

    def test_action_is_empty_string(self):
        """Test that empty string as action returns False."""
        self.assertFalse(is_action_allowed("admin", ""))

    def test_role_is_empty_string(self):
        """Test that empty string as role returns False."""
        self.assertFalse(is_action_allowed("", "read"))

    def test_invalid_role_and_action_combination(self):
        """Test a combination of undefined role and action."""
        self.assertFalse(is_action_allowed("random", "execute"))
