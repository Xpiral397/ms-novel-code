
"""Message processing pipeline using event-driven architecture."""

from typing import List, Dict, Set, Optional
from abc import ABC, abstractmethod
import re
import copy


class EventDispatcher:
    """Handles event subscriptions and notifies processors."""

    def __init__(self):
        """Initializes event dispatcher with observer dictionary."""
        self._observers = {}

    def subscribe(self, event_type: str, observer: 'MessageProcessor'):
        """Registers a processor for a specific event type."""
        if event_type not in self._observers:
            self._observers[event_type] = []
        self._observers[event_type].append(observer)

    def notify(self, event_type: str, message: Dict) -> (List[str], Dict):
        """Notifies processors subscribed to an event type."""
        if event_type not in self._observers:
            return [], message["payload"]
        processor_ids = []
        payload_copy = copy.deepcopy(message["payload"])
        for observer in self._observers[event_type]:
            result, payload_copy = observer.process(message, payload_copy)
            if result:
                processor_ids.append(observer.processor_id)
            else:
                break
        return processor_ids, payload_copy


class MessageProcessor(ABC):
    """Abstract base class for all message processors."""

    def __init__(self, processor_id: str):
        """Initializes processor with processor ID."""
        self.processor_id = processor_id

    @abstractmethod
    def validate(self, message: Dict, payload: Dict) -> bool:
        """Validates incoming message and payload."""
        pass

    @abstractmethod
    def process(self, message: Dict, payload: Dict) -> (bool, Dict):
        """Processes and optionally modifies payload."""
        pass


class RoutingProcessor(MessageProcessor):
    """Routes messages without changing them."""

    def validate(self, message: Dict, payload: Dict) -> bool:
        """Validates message for routing."""
        return True

    def process(self, message: Dict, payload: Dict) -> (bool, Dict):
        """Returns the payload."""
        return True, payload


class ValidationProcessor(MessageProcessor):
    """Validates required fields in the payload."""

    def validate(self, message: Dict, payload: Dict) -> bool:
        """Checks if required fields exist in payload."""
        required_fields = {"content", "checksum"}
        return all(field in payload for field in required_fields)

    def process(self, message: Dict, payload: Dict) -> (bool, Dict):
        """Marks payload as validated if valid."""
        if not self.validate(message, payload):
            return False, payload
        payload = payload.copy()
        payload["validated"] = True
        return True, payload


class TransformProcessor(MessageProcessor):
    """Transforms message content to uppercase."""

    def validate(self, message: Dict, payload: Dict) -> bool:
        """Checks if content is a string."""
        return isinstance(payload.get("content"), str)

    def process(self, message: Dict, payload: Dict) -> (bool, Dict):
        """Converts content to uppercase."""
        if not self.validate(message, payload):
            return False, payload
        payload = payload.copy()
        payload["content"] = payload["content"].upper()
        return True, payload


class ControlProcessor(MessageProcessor):
    """Processes control messages with commands."""

    def validate(self, message: Dict, payload: Dict) -> bool:
        """Checks for command and target in payload."""
        return all(k in payload for k in ["command", "target"])

    def process(self, message: Dict, payload: Dict) -> (bool, Dict):
        """Returns command status if valid."""
        if not self.validate(message, payload):
            return False, payload
        return True, {"command_status": "completed"}


class StatusProcessor(MessageProcessor):
    """Echoes status message payload."""

    def validate(self, message: Dict, payload: Dict) -> bool:
        """Checks if status message is valid."""
        return True

    def process(self, message: Dict, payload: Dict) -> (bool, Dict):
        """Returns a copy of the payload."""
        return True, payload.copy()


class MessageRouter:
    """Handles validation, routing, and processing of messages."""

    def __init__(self):
        """Initializes dispatcher, processors, and tracking fields."""
        self.dispatcher = EventDispatcher()
        self._setup_processors()
        self.processed_msgs: Set[str] = set()
        self.results: Dict[str, Dict] = {}

    def _setup_processors(self):
        """Subscribes processors to event types."""
        d = self.dispatcher
        d.subscribe("DATA", ValidationProcessor("validate_p1"))
        d.subscribe("DATA", TransformProcessor("transform_p1"))
        d.subscribe("DATA", RoutingProcessor("route_p1"))
        d.subscribe("CONTROL", ControlProcessor("control_p1"))
        d.subscribe("CONTROL", RoutingProcessor("route_p2"))
        d.subscribe("STATUS", StatusProcessor("status_p1"))

    def _validate_message(self, message: Dict, all_ids: Set[str]) -> Optional[str]:
        """Validates structure, ID, dependencies, and payload."""
        if not isinstance(message.get("id"), str):
            return "Invalid message ID"
        if not re.match("^[a-zA-Z0-9]{1,32}$", message["id"]):
            return "Invalid message ID format"
        if message["id"] in self.processed_msgs:
            return "Duplicate message ID"
        if not isinstance(message.get("dependencies"), list):
            return "Invalid dependencies format"
        if len(message["dependencies"]) > 10:
            return "Too many dependencies"
        for dep in message["dependencies"]:
            if dep not in all_ids:
                return "Non-existent dependency"

        def dict_depth(d, level=1):
            """Computes dictionary depth."""
            if not isinstance(d, dict) or not d:
                return level
            return max(
                dict_depth(v, level + 1) if isinstance(v, dict)
                else level + 1 for v in d.values()
            )

        if dict_depth(message.get("payload", {})) > 3:
            return "Payload too deep"
        return None

    def _has_circular_dependency(
        self, msg_id: str, deps: Set[str], visited: Set[str]
    ) -> bool:
        """Detects cycles in message dependencies."""
        if msg_id in visited:
            return True
        visited.add(msg_id)
        for dep_id in deps:
            if dep_id in self.results:
                dep_msg = self.results[dep_id]
                if self._has_circular_dependency(
                    dep_id, set(dep_msg["dependencies"]), visited
                ):
                    return True
        visited.remove(msg_id)
        return False

    def _can_process_message(self, message: Dict) -> bool:
        """Checks if dependencies are already processed."""
        return all(
            dep in self.processed_msgs for dep in message["dependencies"]
        )

    def _create_result(
        self,
        msg_id: str,
        status: str,
        processors: List[str] = None,
        result: Dict = None,
    ) -> Dict:
        """Constructs a result dictionary."""
        return {
            "id": msg_id,
            "status": status,
            "processors": processors or [],
            "result": result or {},
        }

    def process_messages(self, messages: List[Dict]) -> List[Dict]:
        """Processes messages via validation and dispatch."""
        if not messages or len(messages) > 100:
            return []
        seen = set()
        filtered = []
        for msg in messages:
            if msg["id"] not in seen:
                filtered.append(msg)
                seen.add(msg["id"])
        messages = filtered
        all_ids = set(msg["id"] for msg in messages)
        msg_status = {msg["id"]: None for msg in messages}
        msg_result = {msg["id"]: None for msg in messages}
        msg_processors = {msg["id"]: [] for msg in messages}
        msg_map = {msg["id"]: msg for msg in messages}
        processed = set()
        results = []
        pending = set(msg["id"] for msg in messages)
        while pending:
            progress = False
            to_remove = set()
            for mid in list(pending):
                msg = msg_map[mid]
                error = self._validate_message(msg, all_ids)
                if error == "Duplicate message ID":
                    to_remove.add(mid)
                    continue
                if error == "Non-existent dependency":
                    msg_status[mid] = "SKIPPED"
                    to_remove.add(mid)
                    continue
                if error:
                    msg_status[mid] = "FAILED"
                    to_remove.add(mid)
                    continue
                if self._has_circular_dependency(
                    mid, set(msg["dependencies"]), set()
                ):
                    msg_status[mid] = "FAILED"
                    to_remove.add(mid)
                    continue
                dep_statuses = [
                    msg_status.get(dep) for dep in msg["dependencies"]
                ]
                if any(s is None for s in dep_statuses):
                    continue
                if any(s in ("FAILED", "SKIPPED") for s in dep_statuses):
                    msg_status[mid] = "SKIPPED"
                    to_remove.add(mid)
                    continue
                if msg["type"] not in ["DATA", "CONTROL", "STATUS"]:
                    msg_status[mid] = "SKIPPED"
                    to_remove.add(mid)
                    continue
                processor_ids = []
                payload_copy = copy.deepcopy(msg["payload"])
                success = True
                failed_at = None
                for observer in self.dispatcher._observers[msg["type"]]:
                    result, payload_copy_new = observer.process(
                        msg, payload_copy
                    )
                    processor_ids.append(observer.processor_id)
                    if not result:
                        failed_at = len(processor_ids) - 1
                        success = False
                        break
                    payload_copy = payload_copy_new
                if not success and failed_at is not None:
                    msg_processors[mid] = processor_ids[:failed_at + 1]
                else:
                    msg_processors[mid] = processor_ids if success else []
                if success:
                    msg_status[mid] = "SUCCESS"
                    if msg["type"] == "DATA":
                        msg_result[mid] = {
                            k: v for k, v in payload_copy.items()
                            if k in ["content", "validated"]
                        }
                    else:
                        msg_result[mid] = payload_copy
                else:
                    msg_status[mid] = "FAILED"
                to_remove.add(mid)
                progress = True
            pending -= to_remove
            if not progress:
                for mid in pending:
                    msg_status[mid] = "FAILED"
                break
        for msg in messages:
            results.append(
                self._create_result(
                    msg["id"],
                    msg_status[msg["id"]] or "FAILED",
                    msg_processors[msg["id"]],
                    msg_result[msg["id"]],
                )
            )
        return results


def process_message_pipeline(messages: List[Dict]) -> List[Dict]:
    """Processes messages using router pipeline."""
    router = MessageRouter()
    return router.process_messages(messages)


if __name__ == "__main__":
    test_messages = [
        {
            "id": "msg1",
            "type": "DATA",
            "payload": {"content": "hello", "checksum": "abc123"},
            "dependencies": [],
        },
        {
            "id": "msg2",
            "type": "CONTROL",
            "payload": {"command": "validate", "target": "msg1"},
            "dependencies": ["msg1"],
        },
    ]
    results = process_message_pipeline(test_messages)
    for result in results:
        print(result)

