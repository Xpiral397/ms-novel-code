
import copy


def execute_batch(initial_state: dict[int, str], operations: list[str]) -> dict[int, str]:
    """
    Executes a batch of database operations on a user table. The table is
    represented as a dictionary with user ID as key and user name as value.

    If any operation fails due to a constraint violation or the explicit
    "FAIL" command, all changes are rolled back and the original state
    is returned.

    Parameters:
        initial_state (dict[int, str]): The original state of the user table.
        operations (list[str]): A list of string operations to apply.

    Returns:
        dict[int, str]: The final state after all operations if successful,
                        or the original state if any operation fails.
    """
    current_state = copy.deepcopy(initial_state)

    for operation in operations:
        parts = operation.strip().split()
        if not parts:
            return initial_state  # Empty operation is invalid

        command = parts[0]

        if command == "INSERT":
            if len(parts) != 3:
                return initial_state
            try:
                user_id = int(parts[1])
                name = parts[2]
            except (ValueError, IndexError):
                return initial_state
            if user_id in current_state:
                return initial_state
            current_state[user_id] = name

        elif command == "UPDATE":
            if len(parts) != 3:
                return initial_state
            try:
                user_id = int(parts[1])
                name = parts[2]
            except (ValueError, IndexError):
                return initial_state
            if user_id not in current_state:
                return initial_state
            current_state[user_id] = name

        elif command == "DELETE":
            if len(parts) != 2:
                return initial_state
            try:
                user_id = int(parts[1])
            except ValueError:
                return initial_state
            if user_id not in current_state:
                return initial_state
            del current_state[user_id]

        elif command == "FAIL":
            return initial_state

        else:
            return initial_state  # Unknown command triggers rollback

    return current_state
