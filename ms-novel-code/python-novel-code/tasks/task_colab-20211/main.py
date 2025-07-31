"""This module provides role-based access control (RBAC) validation."""


_access_rules_data: dict[str, list[str]] = {}


def load_authorization_rules(config: dict) -> None:
    """Load the authorization rules from the given configuration.

    Args:
        config (dict): A dictionary mapping role names (strings) to lists of
            allowed actions (strings).

    Raises:
        TypeError: If the configuration or any of its components are of an
            incorrect type.
        ValueError: If any role name or action is an empty string.
    """
    if not isinstance(config, dict):
        raise TypeError("Configuration must be a dictionary.")

    staging_rules: dict[str, list[str]] = {}

    for role_key, actions_value in config.items():
        if not isinstance(role_key, str) or not role_key:
            raise ValueError(
                f"Role name must be a non-empty string. "
                f"Invalid role: '{role_key}'"
            )

        if not isinstance(actions_value, list):
            raise TypeError(
                f"Actions for role '{role_key}' must be a list. "
                f"Received: {type(actions_value).__name__}"
            )

        valid_actions_for_current_role: list[str] = []

        for individual_action in actions_value:
            if not isinstance(individual_action, str) or not individual_action:
                raise ValueError(
                    f"Action for role '{role_key}'"
                    f" must be a non-empty string. "
                    f"Invalid action: '{individual_action}'"
                )
            valid_actions_for_current_role.append(individual_action)

        staging_rules[role_key] = valid_actions_for_current_role

    global _access_rules_data
    _access_rules_data = staging_rules


def is_action_allowed(role: str, action: str) -> bool:
    """Check if a given role is permitted to perform a specific action.

    Args:
        role (str): The name of the user role.
        action (str): The action to be checked.

    Returns:
        bool: True if the role is allowed to
        perform the action, False otherwise.

    Raises:
        TypeError: If the 'role' or 'action' arguments are not strings.
    """
    if not isinstance(role, str):
        raise TypeError(
            f"The 'role' argument must be a string. "
            f"Received type: {type(role).__name__}"
        )

    if not isinstance(action, str):
        raise TypeError(
            f"The 'action' argument must be a string. "
            f"Received type: {type(action).__name__}"
        )

    if not role or not action:
        return False

    allowed_actions_for_role = _access_rules_data.get(role, [])
    return action in allowed_actions_for_role


if __name__ == "__main__":
    config = {
        "admin": ["create", "read", "update", "delete"],
        "editor": ["read", "update"],
        "viewer": ["read"]
    }

    load_authorization_rules(config)

    print(is_action_allowed("editor", "update"))       # True
    print(is_action_allowed("viewer", "update"))       # False
    print(is_action_allowed("nonexistent", "read"))    # False
    print(is_action_allowed("admin", "delete"))        # True
    print(is_action_allowed("admin", "nonexistent"))   # False
    print(is_action_allowed("", "read"))               # False
    print(is_action_allowed("editor", ""))             # False

