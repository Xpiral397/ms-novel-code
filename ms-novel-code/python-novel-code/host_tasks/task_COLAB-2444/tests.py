# tests
"""Unit tests for the ChatSystem module."""

import unittest
from main import ChatSystem, ChatEvent


class TestChatSystem(unittest.TestCase):
    """Test cases for the ChatSystem class."""

    def setUp(self):
        """Set up a fresh ChatSystem instance before each test."""
        self.chat = ChatSystem()

    def test_subscribe_success(self):
        """Test subscribing a user to a room."""
        event = ChatEvent("SUBSCRIBE", "room1", user_id="alice")
        result = self.chat.process_event(event)
        self.assertEqual(result, "OK")

    def test_subscribe_duplicate(self):
        """Test subscribing the same user twice returns ALREADY_SUBSCRIBED."""
        self.chat.process_event(
            ChatEvent("SUBSCRIBE", "room1", user_id="alice")
        )
        result = self.chat.process_event(
            ChatEvent("SUBSCRIBE", "room1", user_id="alice")
        )
        self.assertEqual(result, "ALREADY_SUBSCRIBED")

    def test_unsubscribe_success(self):
        """Test unsubscribing a user who is subscribed."""
        self.chat.process_event(
            ChatEvent("SUBSCRIBE", "room1", user_id="alice")
        )
        result = self.chat.process_event(
            ChatEvent("UNSUBSCRIBE", "room1", user_id="alice")
        )
        self.assertEqual(result, "OK")

    def test_unsubscribe_not_subscribed(self):
        """Test unsubscribing a user who is not subscribed."""
        result = self.chat.process_event(
            ChatEvent("UNSUBSCRIBE", "room1", user_id="bob")
        )
        self.assertEqual(result, "NOT_SUBSCRIBED")

    def test_publish_to_empty_room(self):
        """Test publishing a message to a room with no subscribers."""
        result = self.chat.process_event(
            ChatEvent("PUBLISH", "room1", sender_id="alice", message="Hi")
        )
        self.assertEqual(result, "DELIVERED_TO_0_USERS")

    def test_publish_to_subscribers(self):
        """Test publishing a message to subscribed users."""
        self.chat.process_event(
            ChatEvent("SUBSCRIBE", "room1", user_id="a")
        )
        self.chat.process_event(
            ChatEvent("SUBSCRIBE", "room1", user_id="b")
        )
        result = self.chat.process_event(
            ChatEvent("PUBLISH", "room1", sender_id="a", message="msg")
        )
        self.assertEqual(result, "DELIVERED_TO_2_USERS")

    def test_get_messages(self):
        """Test retrieving messages from a room."""
        self.chat.process_event(
            ChatEvent("SUBSCRIBE", "room1", user_id="a")
        )
        self.chat.process_event(
            ChatEvent("PUBLISH", "room1", sender_id="a", message="hello")
        )
        result = self.chat.process_event(
            ChatEvent("GET_MESSAGES", "room1", user_id="a")
        )
        self.assertEqual(result, "[a: hello]")

    def test_get_messages_empty(self):
        """Test retrieving messages from an empty room."""
        self.chat.process_event(
            ChatEvent("SUBSCRIBE", "room1", user_id="a")
        )
        result = self.chat.process_event(
            ChatEvent("GET_MESSAGES", "room1", user_id="a")
        )
        self.assertEqual(result, "[]")

    def test_get_messages_room_not_exist(self):
        """Test retrieving messages from a non-existent room."""
        result = self.chat.process_event(
            ChatEvent("GET_MESSAGES", "nope", user_id="x")
        )
        self.assertEqual(result, "[]")

    def test_get_active_users(self):
        """Test retrieving active users from a room."""
        self.chat.process_event(
            ChatEvent("SUBSCRIBE", "room1", user_id="b")
        )
        self.chat.process_event(
            ChatEvent("SUBSCRIBE", "room1", user_id="a")
        )
        result = self.chat.process_event(
            ChatEvent("GET_ACTIVE_USERS", "room1")
        )
        self.assertEqual(result, "[a, b]")

    def test_get_active_users_empty(self):
        """Test retrieving active users from an empty room."""
        self.chat.get_or_create_room("room1")
        result = self.chat.process_event(
            ChatEvent("GET_ACTIVE_USERS", "room1")
        )
        self.assertEqual(result, "[]")

    def test_get_active_users_room_not_exist(self):
        """Test retrieving users from a non-existent room."""
        result = self.chat.process_event(
            ChatEvent("GET_ACTIVE_USERS", "nope")
        )
        self.assertEqual(result, "[]")

    def test_clear_room(self):
        """Test clearing a room with subscribers and messages."""
        self.chat.process_event(
            ChatEvent("SUBSCRIBE", "room1", user_id="a")
        )
        self.chat.process_event(
            ChatEvent("PUBLISH", "room1", sender_id="a", message="x")
        )
        self.chat.process_event(ChatEvent("CLEAR_ROOM", "room1"))
        result = self.chat.process_event(
            ChatEvent("GET_MESSAGES", "room1", user_id="a")
        )
        self.assertEqual(result, "[]")

    def test_clear_room_not_exist(self):
        """Test clearing a room that does not exist."""
        result = self.chat.process_event(
            ChatEvent("CLEAR_ROOM", "ghost")
        )
        self.assertEqual(result, "OK")

    def test_publish_empty_message(self):
        """Test publishing an empty message."""
        self.chat.process_event(
            ChatEvent("SUBSCRIBE", "room1", user_id="u")
        )
        result = self.chat.process_event(
            ChatEvent("PUBLISH", "room1", sender_id="u", message="")
        )
        self.assertEqual(result, "DELIVERED_TO_1_USERS")

    def test_parse_operation_subscribe(self):
        """Test parsing a SUBSCRIBE operation string."""
        op = "SUBSCRIBE alice room42"
        event = self.chat.parse_operation(op)
        self.assertEqual(event.event_type, "SUBSCRIBE")
        self.assertEqual(event.user_id, "alice")
        self.assertEqual(event.room_id, "room42")

    def test_parse_operation_publish(self):
        """Test parsing a PUBLISH operation with a message."""
        op = "PUBLISH room42 userX Hello"
        event = self.chat.parse_operation(op)
        self.assertEqual(event.event_type, "PUBLISH")
        self.assertEqual(event.room_id, "room42")
        self.assertEqual(event.sender_id, "userX")
        self.assertEqual(event.message, "Hello")

    def test_parse_operation_publish_no_message(self):
        """Test parsing a PUBLISH operation with no message."""
        op = "PUBLISH room42 userX"
        event = self.chat.parse_operation(op)
        self.assertEqual(event.message, "")

    def test_parse_operation_get_messages(self):
        """Test parsing a GET_MESSAGES operation string."""
        op = "GET_MESSAGES bob roomX"
        event = self.chat.parse_operation(op)
        self.assertEqual(event.event_type, "GET_MESSAGES")
        self.assertEqual(event.user_id, "bob")
        self.assertEqual(event.room_id, "roomX")

    def test_parse_operation_get_active_users(self):
        """Test parsing a GET_ACTIVE_USERS operation string."""
        op = "GET_ACTIVE_USERS roomY"
        event = self.chat.parse_operation(op)
        self.assertEqual(event.event_type, "GET_ACTIVE_USERS")
        self.assertEqual(event.room_id, "roomY")

    def test_parse_operation_clear_room(self):
        """Test parsing a CLEAR_ROOM operation string."""
        op = "CLEAR_ROOM testRoom"
        event = self.chat.parse_operation(op)
        self.assertEqual(event.event_type, "CLEAR_ROOM")
        self.assertEqual(event.room_id, "testRoom")
