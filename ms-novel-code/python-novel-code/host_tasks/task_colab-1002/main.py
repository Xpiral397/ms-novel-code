"""Process webhook events with deduplication and basic validation."""

import os
import re


def process_webhook_events(
    events: list,
    storage_file: str = "processed_events.txt"
) -> None:
    """
    Process webhook events and store unique event IDs to avoid duplicates.

    Args:
        events: A list of webhook event objects (dictionaries).
        storage_file: The name of the local file to store processed event IDs.
    """
    processed_event_ids = set()

    # Load already processed event IDs from the storage file
    if os.path.exists(storage_file):
        try:
            with open(storage_file, 'r') as f:
                for line in f:
                    event_id = line.strip()
                    if event_id:
                        processed_event_ids.add(event_id)
        except IOError as e:
            print(f"Error reading storage file '{storage_file}': {e}")
            return
        except Exception as e:
            print(
                f"An unexpected error occurred"
                f" while reading '{storage_file}': {e}"
            )
            return

    # Open the storage file in append mode for writing new event IDs
    try:
        with (open(storage_file, 'a') as f_append):
            for i, event in enumerate(events):
                event_id = event.get("event_id")
                event_type = event.get("event_type")
                timestamp = event.get("timestamp")
                payload = event.get("payload")

                if not all([
                    event_id, event_type, timestamp, payload is not None
                ]):
                    print(
                        f"Skipping malformed event at index {i}: "
                        f"Missing required fields."
                    )
                    continue

                if not isinstance(event_id, str
                                  ) or not (1 <= len(event_id) <= 100):
                    print(
                        f"Skipping malformed event at index {i}: "
                        f"'event_id' is invalid."
                    )
                    continue

                if not isinstance(event_type, str) or not event_type:
                    print(
                        f"Skipping malformed event at index {i}: "
                        f"'event_type' is invalid."
                    )
                    continue

                # Basic ISO 8601 format check
                if (
                    not isinstance(timestamp, str) or
                    not re.fullmatch(
                        r'\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}Z',
                        timestamp
                    )
                ):
                    print(
                        f"Skipping malformed event at index {i}: "
                        f"'timestamp' is not in valid ISO 8601 format "
                        f"(YYYY-MM-DDTHH:MM:SSZ)."
                    )
                    continue

                if not isinstance(payload, dict):
                    print(
                        f"Skipping malformed event at index {i}: "
                        f"'payload' is not a dictionary."
                    )
                    continue

                if event_id in processed_event_ids:
                    print(f"Duplicate event skipped: {event_id}")
                else:
                    print(f"Processed event: {event_id}")
                    processed_event_ids.add(event_id)
                    f_append.write(f"{event_id}\n")
                    f_append.flush()

    except IOError as e:
        print(f"Error writing to storage file '{storage_file}': {e}")
    except Exception as e:
        print(
            f"An unexpected error occurred during event processing: {e}"
        )


if __name__ == "__main__":
    if os.path.exists("processed_events.txt"):
        os.remove("processed_events.txt")
        print("Cleaned up 'processed_events.txt' from previous run.")
    print("-" * 30)

    print("--- First Run ---")
    events_run1 = [
        {
            "event_id": "evt_001",
            "event_type": "user.created",
            "timestamp": "2025-07-22T08:00:00Z",
            "payload": {"user_id": 1, "name": "Alice"}
        },
        {
            "event_id": "evt_002",
            "event_type": "user.updated",
            "timestamp": "2025-07-22T08:05:00Z",
            "payload": {"user_id": 1, "name": "Alice Smith"}
        },
        {
            "event_id": "evt_001",
            "event_type": "user.created",
            "timestamp": "2025-07-22T08:10:00Z",
            "payload": {"user_id": 1, "name": "Duplicate Alice"}
        },
        {
            "event_id": "evt_003",
            "event_type": "product.added",
            "timestamp": "2025-07-22T09:00:00Z",
            "payload": {"product_id": 101, "name": "Laptop"}
        }
    ]
    process_webhook_events(events_run1)
    print("-" * 30)

    print("--- Second Run ---")
    events_run2 = [
        {
            "event_id": "evt_002",
            "event_type": "user.deleted",
            "timestamp": "2025-07-22T10:00:00Z",
            "payload": {"user_id": 1}
        },
        {
            "event_id": "evt_004",
            "event_type": "order.placed",
            "timestamp": "2025-07-22T10:15:00Z",
            "payload": {"order_id": 5001, "amount": 100.00}
        },
        {
            "event_id": "evt_001",
            "event_type": "user.login",
            "timestamp": "2025-07-22T10:20:00Z",
            "payload": {"user_id": 1}
        }
    ]
    process_webhook_events(events_run2)
    print("-" * 30)

    print("--- Malformed Events Test ---")
    malformed_events = [
        {
            "event_type": "missing.id",
            "timestamp": "2025-07-22T11:00:00Z",
            "payload": {}
        },
        {
            "event_id": "evt_005",
            "event_type": "",
            "timestamp": "2025-07-22T11:05:00Z",
            "payload": {}
        },
        {
            "event_id": "evt_006",
            "event_type": "invalid.timestamp",
            "timestamp": "2025/07/22 11:10:00",
            "payload": {}
        },
        {
            "event_id": "evt_007",
            "event_type": "invalid.payload",
            "timestamp": "2025-07-22T11:15:00Z",
            "payload": "not_a_dict"
        },
        {
            "event_id": "evt_008" * 15,
            "event_type": "long.id.test",
            "timestamp": "2025-07-22T11:20:00Z",
            "payload": {}
        }
    ]
    process_webhook_events(malformed_events)
    print("-" * 30)

    print("--- Empty Input Test ---")
    process_webhook_events([])
    print("-" * 30)

    print("\nContent of processed_events.txt:")
    if os.path.exists("processed_events.txt"):
        with open("processed_events.txt", 'r') as f:
            print(f.read().strip())
    else:
        print("File 'processed_events.txt' does not exist.")

