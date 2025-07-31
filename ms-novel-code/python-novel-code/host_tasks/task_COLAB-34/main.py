
from typing import List, Dict, Tuple, Any
from dataclasses import dataclass
from abc import ABC, abstractmethod


@dataclass
class BankEvent:
    """Immutable event representing a bank transaction."""

    transaction_id: int
    type: str
    amount: int
    resulting_balance: int


class EventStore:
    """Stores and manages immutable events."""

    def __init__(self):
        self._events: List[BankEvent] = []

    def append_event(self, event: BankEvent) -> None:
        """Add a new event to the store."""
        self._events.append(event)

    def get_all_events(self) -> List[BankEvent]:
        """Retrieve all events in chronological order."""
        return self._events.copy()

    def get_event_count(self) -> int:
        """Get total number of events."""
        return len(self._events)


class Command(ABC):
    """Abstract base class for commands."""

    @abstractmethod
    def execute(self, current_balance: int) -> Tuple[int, str]:
        """Execute the command and return new balance and event type."""
        pass


class DepositCommand(Command):
    """Command for deposit transactions."""

    def __init__(self, amount: int):
        self.amount = amount

    def execute(self, current_balance: int) -> Tuple[int, str]:
        return current_balance + self.amount, "deposit"


class WithdrawCommand(Command):
    """Command for withdrawal transactions."""

    def __init__(self, amount: int):
        self.amount = amount

    def execute(self, current_balance: int) -> Tuple[int, str]:
        return current_balance - self.amount, "withdraw"


class BankAccount:
    """Event-driven bank account that maintains state through event replay."""

    def __init__(self):
        self.event_store = EventStore()

    def process_transaction(self, transaction_type: str, amount: int,
                            transaction_id: int) -> None:
        """Process a single transaction and store the resulting event."""
        # Create appropriate command
        if transaction_type == "deposit":
            command = DepositCommand(amount)
        elif transaction_type == "withdraw":
            command = WithdrawCommand(amount)
        else:
            raise ValueError(f"Unknown transaction type: {transaction_type}")

        # Get current balance through event replay
        current_balance = self._replay_events()

        # Execute command to get new balance
        new_balance, event_type = command.execute(current_balance)

        # Create and store immutable event
        event = BankEvent(
            transaction_id=transaction_id,
            type=event_type,
            amount=amount,
            resulting_balance=new_balance
        )

        self.event_store.append_event(event)

    def _replay_events(self) -> int:
        """Replay all events to calculate current balance."""
        balance = 0
        for event in self.event_store.get_all_events():
            balance = event.resulting_balance
        return balance

    def get_final_balance(self) -> int:
        """Get current balance by replaying all events."""
        return self._replay_events()

    def get_transaction_count(self) -> int:
        """Get total number of processed transactions."""
        return self.event_store.get_event_count()

    def get_event_log(self) -> List[Dict[str, Any]]:
        """Get complete event log as list of dictionaries."""
        events = self.event_store.get_all_events()
        return [
            {
                "transaction_id": event.transaction_id,
                "type": event.type,
                "amount": event.amount,
                "resulting_balance": event.resulting_balance
            }
            for event in events
        ]

    def get_balance_history(self) -> List[int]:
        """Get balance history after each transaction."""
        events = self.event_store.get_all_events()
        return [event.resulting_balance for event in events]


def process_bank_transactions(
        transactions: List[Tuple[str, int, int]]) -> Dict[str, Any]:
    """
    Process bank transactions using event-driven architecture.

    Args:
        transactions: List of tuples (type, amount, transaction_id)

    Returns:
        Dictionary with final_balance, transaction_count, event_log,
        balance_history
    """
    # Create bank account instance
    account = BankAccount()

    # Process each transaction
    for transaction_type, amount, transaction_id in transactions:
        account.process_transaction(transaction_type, amount, transaction_id)

    # Build and return result
    return {
        "final_balance": account.get_final_balance(),
        "transaction_count": account.get_transaction_count(),
        "event_log": account.get_event_log(),
        "balance_history": account.get_balance_history()
    }


# Example usage and testing
if __name__ == "__main__":
    # Test Example 1
    transactions1 = [("deposit", 1000, 1), ("withdraw", 300, 2)]
    result1 = process_bank_transactions(transactions1)
    print(result1)
    print()

    # Test Example 2
    transactions2 = [("deposit", 500, 1), ("deposit", 200, 2), ("withdraw", 100, 3)]
    result2 = process_bank_transactions(transactions2)
    print(result2)
    print()

