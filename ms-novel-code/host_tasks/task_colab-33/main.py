
import copy
import re

# In-memory storage for payload version snapshots
_snapshot_store = {}


def migrate_payload(payload: dict, migration_rules: dict, target_version: str, payload_id: str) -> dict:
    """
    Migrates the input payload to the target version using rule-based transformations.
    Stores intermediate states keyed by payload_id and version.

    Args:
        payload (dict): The input payload containing 'version' and 'data'.
        migration_rules (dict): Migration steps with rules for each adjacent version.
        target_version (str): The schema version to migrate to.
        payload_id (str): Unique identifier for storing snapshots.

    Returns:
        dict: The transformed payload at the target version.

    Raises:
        ValueError: If required migration steps are missing.
    """
    if not isinstance(payload, dict):
        raise ValueError("Payload must be a dictionary.")

    version_pattern = r"^v(\d+)$"
    current_match = re.match(version_pattern, payload.get("version", ""))
    target_match = re.match(version_pattern, target_version)

    if not current_match or not target_match:
        raise ValueError("Invalid version format. Must be like 'v1', 'v2', ...")

    current_version = int(current_match.group(1))
    target_version_num = int(target_match.group(1))

    if payload_id not in _snapshot_store:
        _snapshot_store[payload_id] = {}

    # Deep copy the original
    current_payload = copy.deepcopy(payload)
    _snapshot_store[payload_id][f"v{current_version}"] = copy.deepcopy(current_payload)

    step = 1 if target_version_num > current_version else -1

    for v in range(current_version, target_version_num, step):
        from_version = f"v{v}"
        to_version = f"v{v + step}"
        direction = f"{from_version}_to_{to_version}"

        if direction not in migration_rules:
            raise ValueError(f"Missing migration rule for: {direction}")

        rules = migration_rules[direction]
        current_payload = apply_rules(current_payload, rules)
        current_payload["version"] = to_version
        _snapshot_store[payload_id][to_version] = copy.deepcopy(current_payload)

    return current_payload


def rollback_payload(payload_id: str, target_version: str) -> dict:
    """
    Returns a previously stored version of a payload by ID and version.
    Does not perform any transformation.

    Args:
        payload_id (str): Unique identifier for the payload.
        target_version (str): The schema version to restore.

    Returns:
        dict: The stored payload snapshot.

    Raises:
        KeyError: If the version is not available for the given ID.
    """
    if payload_id not in _snapshot_store:
        raise KeyError(f"No payload found for ID: {payload_id}")

    if target_version not in _snapshot_store[payload_id]:
        raise KeyError(f"No version '{target_version}' stored for ID: {payload_id}")

    return copy.deepcopy(_snapshot_store[payload_id][target_version])


def apply_rules(payload, rules):
    """
    Applies a list of transformation rules to the payload data.

    Args:
        payload (dict): A payload containing 'data'.
        rules (list): A list of rule dictionaries.

    Returns:
        dict: The transformed payload.
    """
    data = copy.deepcopy(payload["data"])

    for rule in rules:
        op = rule.get("op")
        if op in {"rename", "add", "remove", "set"}:
            data = apply_field_rule(data, rule)
        elif op == "map":
            data = apply_map_rule(data, rule)
        else:
            raise ValueError(f"Unsupported operation: {op}")

    return {"version": payload["version"], "data": data}


def apply_field_rule(data, rule):
    """
    Applies a single field-level rule to a data dictionary.

    Args:
        data (dict): Data to modify.
        rule (dict): Rule dict.

    Returns:
        dict: Modified data.
    """
    new_data = copy.deepcopy(data)
    op = rule["op"]

    if op == "rename":
        from_field = rule["from"]
        to_field = rule["to"]
        if from_field in new_data:
            new_data[to_field] = new_data.pop(from_field)

    elif op == "add":
        field = rule["field"]
        if field not in new_data:
            new_data[field] = rule["value"]

    elif op == "remove":
        field = rule["field"]
        new_data.pop(field, None)

    elif op == "set":
        field = rule["field"]
        new_data[field] = rule["value"]

    return new_data


def apply_map_rule(data, rule):
    """
    Applies a map rule to each element in a list at the specified path.

    Args:
        data (dict): Payload data.
        rule (dict): Map rule with path and nested rules.

    Returns:
        dict: Modified data.
    """
    path = rule["path"]
    subrules = rule["rules"]
    keys = path.split(".")

    list_parent, list_key = resolve_list_parent(data, keys)
    if list_parent is None or list_key not in list_parent:
        return data

    list_items = list_parent[list_key]
    if not isinstance(list_items, list):
        return data

    new_list = []
    for item in list_items:
        new_item = copy.deepcopy(item)
        for subrule in subrules:
            new_item = apply_field_rule(new_item, subrule)
        new_list.append(new_item)

    list_parent[list_key] = new_list
    return data


def resolve_list_parent(data, keys):
    """
    Traverses the path and returns the parent object and final key of the list.

    Args:
        data (dict): Data dictionary.
        keys (list): Path split into keys.

    Returns:
        tuple: (parent_object, list_key) or (None, None) if path is invalid.
    """
    obj = data
    for key in keys[:-1]:
        if not isinstance(obj, dict) or key not in obj:
            return None, None
        obj = obj[key]

    return obj, keys[-1]
