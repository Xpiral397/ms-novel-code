
class ChatEvent:
    """Represents an event in the chat system."""

    def __init__(self, event_type, room_id, user_id=None,
                 message=None, sender_id=None):
        """
        Initialize the event with type, room ID, user ID, message,
        and sender ID.
        """
        self.event_type = event_type
        self.room_id = room_id
        self.user_id = user_id
        self.message = message
        self.sender_id = sender_id


class ChatRoom:
    """Represents a chat room with subscribers and messages."""

    def __init__(self, room_id):
        """
        Initialize the chat room with a room ID,
        an empty set of subscribers, and an empty message.
        """
        self.room_id = room_id
        self.subscribers = set()
        self.messages = []

    def add_subscriber(self, user_id):
        """Add a subscriber to the room."""
        if user_id in self.subscribers:
            return False
        self.subscribers.add(user_id)
        return True

    def remove_subscriber(self, user_id):
        """Remove a subscriber from the room."""
        if user_id not in self.subscribers:
            return False
        self.subscribers.remove(user_id)
        return True

    def add_message(self, sender_id, message):
        """Add a message to the room."""
        self.messages.append((sender_id, message))

    def get_messages(self):
        """Get all messages in the room."""
        return self.messages.copy()

    def get_active_users(self):
        """Get sorted list of active subscribers."""
        return sorted(list(self.subscribers))

    def clear(self):
        """Clear all messages and subscribers."""
        self.subscribers.clear()
        self.messages.clear()


class EventHandler:
    """Handles different types of events."""

    def __init__(self, chat_system):
        """Initialize with a reference to the chat system."""
        self.chat_system = chat_system

    def handle_event(self, event):
        """Route events to appropriate handlers"""
        if event.event_type == "SUBSCRIBE":
            return self.handle_subscribe(event)
        elif event.event_type == "UNSUBSCRIBE":
            return self.handle_unsubscribe(event)
        elif event.event_type == "PUBLISH":
            return self.handle_publish(event)
        elif event.event_type == "GET_MESSAGES":
            return self.handle_get_messages(event)
        elif event.event_type == "GET_ACTIVE_USERS":
            return self.handle_get_active_users(event)
        elif event.event_type == "CLEAR_ROOM":
            return self.handle_clear_room(event)

    def handle_subscribe(self, event):
        """Handle subscription event."""
        room = self.chat_system.get_or_create_room(event.room_id)
        success = room.add_subscriber(event.user_id)
        return "OK" if success else "ALREADY_SUBSCRIBED"

    def handle_unsubscribe(self, event):
        """Handle unsubscription event."""
        room = self.chat_system.get_room(event.room_id)
        if room is None:
            return "NOT_SUBSCRIBED"
        success = room.remove_subscriber(event.user_id)
        return "OK" if success else "NOT_SUBSCRIBED"

    def handle_publish(self, event):
        """Handle message publish event."""
        room = self.chat_system.get_or_create_room(event.room_id)
        room.add_message(event.sender_id, event.message)
        subscriber_count = len(room.subscribers)
        return f"DELIVERED_TO_{subscriber_count}_USERS"

    def handle_get_messages(self, event):
        """Handle get messages event."""
        room = self.chat_system.get_room(event.room_id)
        if room is None:
            return "[]"

        messages = room.get_messages()
        if not messages:
            return "[]"

        message_strings = [f"{sender}: {msg}" for sender, msg in messages]
        return f"[{', '.join(message_strings)}]"

    def handle_get_active_users(self, event):
        """Handle get active users event."""
        room = self.chat_system.get_room(event.room_id)
        if room is None:
            return "[]"

        users = room.get_active_users()
        if not users:
            return "[]"

        return f"[{', '.join(users)}]"

    def handle_clear_room(self, event):
        """Handle clear room event."""
        room = self.chat_system.get_room(event.room_id)
        if room is not None:
            room.clear()
        return "OK"


class ChatSystem:
    """Main chat system that manages rooms and processes events."""

    def __init__(self):
        """
        Initialize the chat system with an empty room dictionary
        and event handler.
        """
        self.rooms = {}
        self.event_handler = EventHandler(self)

    def get_room(self, room_id):
        """Get existing room or None if doesn't exist."""
        return self.rooms.get(room_id)

    def get_or_create_room(self, room_id):
        """Get existing room or create new one."""
        if room_id not in self.rooms:
            self.rooms[room_id] = ChatRoom(room_id)
        return self.rooms[room_id]

    def process_event(self, event):
        """Process a single event and return result."""
        return self.event_handler.handle_event(event)

    def parse_operation(self, operation):
        """Parse operation string into ChatEvent."""
        parts = operation.split(' ', 3)

        if parts[0] == "SUBSCRIBE":
            return ChatEvent("SUBSCRIBE", parts[2], user_id=parts[1])
        elif parts[0] == "UNSUBSCRIBE":
            return ChatEvent("UNSUBSCRIBE", parts[2], user_id=parts[1])
        elif parts[0] == "PUBLISH":
            room_id = parts[1]
            sender_id = parts[2]
            message = parts[3] if len(parts) > 3 else ""
            return ChatEvent(
                "PUBLISH", room_id, sender_id=sender_id, message=message)
        elif parts[0] == "GET_MESSAGES":
            return ChatEvent("GET_MESSAGES", parts[2], user_id=parts[1])
        elif parts[0] == "GET_ACTIVE_USERS":
            return ChatEvent("GET_ACTIVE_USERS", parts[1])
        elif parts[0] == "CLEAR_ROOM":
            return ChatEvent("CLEAR_ROOM", parts[1])


def process_chat_operations(operations):
    """
    Process a list of chat room operations and return results.

    Args:
        operations (list): List of operation strings

    Returns:
        list: List of result strings corresponding to each operation
    """
    chat_system = ChatSystem()
    results = []

    for operation in operations:
        # Parse operation into event
        event = chat_system.parse_operation(operation)

        # Process event and get result
        result = chat_system.process_event(event)
        results.append(result)

    return results


# Driver function with test cases
def main():
    """
    To run test cases for the chat system.
    It processes predefined operations and prints results.
    """
    # Test Case 1
    print("Test Case 1:")
    operations1 = [
        "SUBSCRIBE alice room1",
        "SUBSCRIBE bob room1",
        "PUBLISH room1 alice Hello everyone",
        "GET_MESSAGES alice room1",
        "GET_MESSAGES bob room1"
    ]

    results1 = process_chat_operations(operations1)
    print(results1)

    # Test Case 2
    print("Test Case 2:")
    operations2 = [
        "SUBSCRIBE user1 room1",
        "SUBSCRIBE user2 room1",
        "PUBLISH room1 user1 First message",
        "SUBSCRIBE user3 room1",
        "PUBLISH room1 user2 Second message",
        "GET_MESSAGES user3 room1",
        "GET_ACTIVE_USERS room1",
        "UNSUBSCRIBE user1 room1",
        "GET_ACTIVE_USERS room1"
    ]

    results2 = process_chat_operations(operations2)
    print(results2)

    # Test Case 3 - Edge Cases
    print("Test Case 3 - Edge Cases:")
    operations3 = [
        "GET_MESSAGES user1 nonexistent",
        "GET_ACTIVE_USERS nonexistent",
        "SUBSCRIBE user1 room1",
        "SUBSCRIBE user1 room1",
        "UNSUBSCRIBE user2 room1",
        "PUBLISH room1 user1 ",
        "CLEAR_ROOM room1",
        "GET_MESSAGES user1 room1"
    ]

    results3 = process_chat_operations(operations3)
    print(results3)


if __name__ == "__main__":
    main()

