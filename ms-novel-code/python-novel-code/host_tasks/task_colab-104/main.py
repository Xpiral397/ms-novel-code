"""CRUD operations using SQLAlchemy ORM and SQLite."""

import re
import time
from typing import Any, Dict, List, Optional
from sqlalchemy import create_engine, Column, Integer, String
from sqlalchemy.orm import sessionmaker, declarative_base, Session
from sqlalchemy.exc import IntegrityError, OperationalError

Base = declarative_base()


class User(Base):
    """Represents a user in the database."""

    __tablename__ = "users"
    id = Column(Integer, primary_key=True)
    name = Column(String, nullable=False)
    email = Column(String, nullable=False, unique=True)

    def __repr__(self):
        """Return a string representation of the user."""
        return (
            f"<User(id={self.id}, name='{self.name}', "
            f"email='{self.email}')>"
        )

    def to_dict(self) -> Dict[str, Any]:
        """Convert the User object to a dictionary."""
        return {"id": self.id, "name": self.name, "email": self.email}


def _validate_user_data(name: str, email: str) -> bool:
    """Validate the name and email inputs."""
    if not name or not isinstance(name, str):
        print("Validation Error: Name cannot be empty.")
        return False
    if not email or not isinstance(email, str):
        print("Validation Error: Email cannot be empty.")
        return False
    if not re.match(r"[^@]+@[^@]+\.[^@]+", email):
        print(f"Validation Error: Invalid email format for '{email}'.")
        return False
    return True


def _perform_with_retry(
    session: Session,
    operation_func,
    *args,
    **kwargs
) -> Any:
    """
    Retry a database operation on transient errors.

    Retries the operation up to 3 times on OperationalError.
    """
    max_retries = 3
    retry_delay_seconds = 0.1
    for attempt in range(max_retries):
        try:
            result = operation_func(session, *args, **kwargs)
            session.commit()
            return result
        except IntegrityError as exc:
            session.rollback()
            print(
                "Database Error: Integrity constraint violated. "
                f"Details: {exc}"
            )
            return False
        except OperationalError as exc:
            session.rollback()
            print(
                f"Transient Database Error (attempt {attempt + 1}/"
                f"{max_retries}): {exc}"
            )
            if attempt < max_retries - 1:
                time.sleep(retry_delay_seconds)
            else:
                print("All retries failed.")
                return False
        except Exception as exc:
            session.rollback()
            print(f"An unexpected error occurred: {exc}")
            return False
    return False


def create_user(session: Session, name: str, email: str) -> bool:
    """Create a new user in the database."""
    if not _validate_user_data(name, email):
        return False

    def _create_internal(sess: Session) -> bool:
        new_user = User(name=name, email=email)
        sess.add(new_user)
        return True

    return _perform_with_retry(session, _create_internal)


def get_user(session: Session, user_id: int) -> Optional[Dict[str, Any]]:
    """Retrieve a user by their ID."""
    user = session.query(User).filter_by(id=user_id).first()
    return user.to_dict() if user else None


def get_users(session: Session) -> List[Dict[str, Any]]:
    """Retrieve all users in the database."""
    users = session.query(User).all()
    return [user.to_dict() for user in users]


def update_user(
    session: Session,
    user_id: int,
    new_name: str,
    new_email: str
) -> bool:
    """Update an existing user's name and email."""
    if not _validate_user_data(new_name, new_email):
        return False

    def _update_internal(sess: Session) -> bool:
        user = sess.query(User).filter_by(id=user_id).first()
        if not user:
            print(f"Update Error: User with ID {user_id} not found.")
            return False
        user.name = new_name
        user.email = new_email
        return True

    return _perform_with_retry(session, _update_internal)


def delete_user(session: Session, user_id: int) -> bool:
    """Delete a user from the database."""
    def _delete_internal(sess: Session) -> bool:
        user = sess.query(User).filter_by(id=user_id).first()
        if not user:
            print(f"Delete Error: User with ID {user_id} not found.")
            return False
        sess.delete(user)
        return True

    return _perform_with_retry(session, _delete_internal)


def main():
    """Demonstrate the full CRUD lifecycle."""
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    session_local = sessionmaker(
        autocommit=False,
        autoflush=False,
        bind=engine
    )

    with session_local() as session:
        print("--- CRUD Lifecycle Demonstration ---")

        print("\n--- Create Operations ---")
        print("Attempting to create Alice...")
        if create_user(session, "Alice", "alice@example.com"):
            print("Alice created successfully.")
        else:
            print("Failed to create Alice.")
        print("Current users after Alice creation:")
        print(get_users(session))

        print("\nAttempting to create Bob...")
        if create_user(session, "Bob", "bob@example.com"):
            print("Bob created successfully.")
        else:
            print("Failed to create Bob.")
        print("Current users after Bob creation:")
        print(get_users(session))

        print("\nAttempting to create Charlie with Alice's email...")
        if create_user(session, "Charlie", "alice@example.com"):
            print("Charlie created successfully (unexpected).")
        else:
            print("Failed to create Charlie due to duplicate email.")
        print("Current users after Charlie attempt:")
        print(get_users(session))

        print("\nAttempting to create David with invalid email...")
        if create_user(session, "David", "invalid-email"):
            print("David created successfully (unexpected).")
        else:
            print("Failed to create David due to invalid email.")
        print("Current users after David attempt:")
        print(get_users(session))

        print("\nAttempting to create Eve with empty name...")
        if create_user(session, "", "eve@example.com"):
            print("Eve created successfully (unexpected).")
        else:
            print("Failed to create Eve due to empty name.")
        print("Current users after Eve attempt:")
        print(get_users(session))

        print("\n--- Read Operations ---")
        all_users = get_users(session)
        print("All users:")
        print(all_users)

        user_id_alice = all_users[0]['id'] if all_users else None
        if user_id_alice:
            print(f"Retrieving user with ID {user_id_alice}:")
            print(get_user(session, user_id_alice))
        else:
            print("No users to retrieve by ID.")

        print("Retrieving user with ID 99 (should be None):")
        print(get_user(session, 99))

        print("\n--- Update Operations ---")
        if user_id_alice:
            print(f"Updating Alice (ID {user_id_alice})...")
            if update_user(
                session,
                user_id_alice,
                "Alice Smith",
                "alice.smith@example.com"
            ):
                print("Alice updated successfully.")
            else:
                print("Failed to update Alice.")
            print("Current users after Alice update:")
            print(get_users(session))

        print("\nAttempting to update non-existent user (ID 99)...")
        if not update_user(session, 99, "Ghost", "ghost@example.com"):
            print("Expected failure: user not found.")
        print("Current users after failed update:")
        print(get_users(session))

        user_id_bob = all_users[1]['id'] if len(all_users) > 1 else None
        if user_id_bob and user_id_alice:
            print(f"\nUpdating Bob (ID {user_id_bob}) with Alice's email...")
            if not update_user(
                session,
                user_id_bob,
                "Bob",
                "alice.smith@example.com"
            ):
                print("Expected failure: duplicate email.")
            print("Current users after Bob update attempt:")
            print(get_users(session))

        print("\n--- Delete Operations ---")
        if user_id_alice:
            print(f"Deleting Alice (ID {user_id_alice})...")
            if delete_user(session, user_id_alice):
                print("Alice deleted successfully.")
            else:
                print("Failed to delete Alice.")
            print("Current users after Alice deletion:")
            print(get_users(session))

        if user_id_bob:
            print(f"\nDeleting Bob (ID {user_id_bob})...")
            if delete_user(session, user_id_bob):
                print("Bob deleted successfully.")
            else:
                print("Failed to delete Bob.")
            print("Current users after Bob deletion:")
            print(get_users(session))

        print("\nAttempting to delete user with ID 99...")
        if not delete_user(session, 99):
            print("Expected failure: user not found.")
        print("Final users in database:")
        print(get_users(session))


if __name__ == "__main__":
    main()

