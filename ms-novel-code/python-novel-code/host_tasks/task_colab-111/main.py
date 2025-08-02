
"""Event-driven system for user registration."""


class Event:
    """Simulate an event with subscription and trigger support."""

    def __init__(self):
        """Initialize handler list."""
        self.handlers = []

    def subscribe(self, handler):
        """Subscribe a handler to the event."""
        self.handlers.append(handler)

    def trigger(self, *args, **kwargs):
        """Trigger the event and collect results from handlers."""
        results = []
        for handler in self.handlers:
            results.append(handler(*args, **kwargs))
        return results


def is_professional_email(email):
    """Check if email is professional."""
    return email.lower().endswith("@company.com")


def is_personal_email(email):
    """Check if email is from common personal domains."""
    personal_domains = ["@gmail.com", "@yahoo.com", "@outlook.com"]
    email_lower = email.lower()
    return any(email_lower.endswith(d) for d in personal_domains)


def welcome_email_handler(event):
    """Handle user registration event and return welcome message."""
    required_keys = ["username", "email", "timestamp"]
    for key in required_keys:
        if key not in event:
            return "Invalid registration"

    username = event["username"]
    email = event["email"]

    if not isinstance(username, str) or username.strip() == "":
        return "Invalid registration"
    if not isinstance(email, str) or email.strip() == "":
        return "Invalid registration"

    email = email.strip()
    if email.count("@") != 1:
        return "Invalid registration"

    local, domain = email.split("@")
    if "." not in domain:
        return "Invalid registration"

    message = (
        f"Welcome, {username.strip()}! "
        "Your registration is successful."
    )

    user_type = event.get("user_type", None)
    if user_type == "admin":
        message += " You have admin privileges."
    elif user_type == "guest":
        message += " Enjoy your guest access."

    age = event.get("age", None)
    if isinstance(age, int) and age < 18:
        message += (
            " Note: Some features may be restricted for users under 18."
        )

    if is_professional_email(email):
        message += (
            " Thank you for registering with your professional email."
        )
    elif is_personal_email(email):
        message += (
            " Thank you for registering with your personal email."
        )

    return message


def process_user_registered_events(events):
    """Process list of registration events and return results."""
    user_registered_event = Event()
    user_registered_event.subscribe(welcome_email_handler)
    results = []
    for event in events:
        result = user_registered_event.trigger(event)[0]
        results.append(result)
    return results


if __name__ == "__main__":
    # Example 1: Customizations and professional/personal email
    events1 = [
        {
            "username": "Alice",
            "email": "alice@company.com",
            "timestamp": 1620000000,
            "user_type": "admin",
            "age": 30
        },
        {
            "username": "Bob",
            "email": "bob@gmail.com",
            "timestamp": 1620000100,
            "age": 16
        }
    ]
    print(process_user_registered_events(events1))

    # Example 2: Invalid registrations
    events2 = [
        {
            "username": "",
            "email": "eve@example.com",
            "timestamp": 1620000200
        },
        {
            "username": "Eve",
            "email": "",
            "timestamp": 1620000300
        },
        {
            "username": "Mallory",
            "email": "mallory_at_example.com",
            "timestamp": 1620000400
        }
    ]
    print(process_user_registered_events(events2))

    # Example 3: Guest, personal, and standard
    events3 = [
        {
            "username": "Oscar",
            "email": "oscar@company.com",
            "timestamp": 1620000500,
            "user_type": "guest"
        },
        {
            "username": "Trudy",
            "email": "trudy@yahoo.com",
            "timestamp": 1620000600
        },
        {
            "username": "Victor",
            "email": "victor@example.com",
            "timestamp": 1620000700
        }
    ]
    print(process_user_registered_events(events3))

    # Edge: Empty input
    print(process_user_registered_events([]))

    # Edge: Username is whitespace
    events4 = [
        {
            "username": "   ",
            "email": "user@example.com",
            "timestamp": 1620000800
        }
    ]
    print(process_user_registered_events(events4))

    # Edge: Email is whitespace
    events5 = [
        {
            "username": "User",
            "email": "   ",
            "timestamp": 1620000900
        }
    ]
    print(process_user_registered_events(events5))

    # Edge: Email with multiple @
    events6 = [
        {
            "username": "User",
            "email": "user@@company.com",
            "timestamp": 1620001000
        }
    ]
    print(process_user_registered_events(events6))

    # Edge: Email with no dot after @
    events7 = [
        {
            "username": "User",
            "email": "user@companycom",
            "timestamp": 1620001100
        }
    ]
    print(process_user_registered_events(events7))

    # Edge: Missing required key
    events8 = [
        {
            "username": "User",
            "timestamp": 1620001200
        }
    ]
    print(process_user_registered_events(events8))

    # Edge: Both professional and personal
    events9 = [
        {
            "username": "Pro",
            "email": "pro@company.com",
            "timestamp": 1620001300,
            "user_type": "admin",
            "age": 17
        }
    ]
    print(process_user_registered_events(events9))

    # Edge: Age is exactly 18
    events10 = [
        {
            "username": "Adult",
            "email": "adult@gmail.com",
            "timestamp": 1620001400,
            "age": 18
        }
    ]
    print(process_user_registered_events(events10))

    # Edge: Unknown user_type
    events11 = [
        {
            "username": "Mystery",
            "email": "mystery@gmail.com",
            "timestamp": 1620001500,
            "user_type": "superuser"
        }
    ]
    print(process_user_registered_events(events11))

