
"""CQRS restaurant order management system implementation."""

from typing import List, Tuple, Any, Dict


class EventBus:
    """Event bus for decoupling OrderProcessor and OrderAnalytics."""

    def __init__(self):
        """Initialize the event bus."""
        self._listeners = []

    def subscribe(self, listener):
        """Subscribe a listener to receive events."""
        self._listeners.append(listener)

    def publish(self, event_type: str, data: Dict):
        """Publish an event to all subscribed listeners."""
        for listener in self._listeners:
            listener.handle_event(event_type, data)


class OrderProcessor:
    """Handles write operations - placing and completing orders."""

    MENU_PRICES = {
        "Margherita": 12.99,
        "Pepperoni": 15.99,
        "Vegetarian": 14.99,
        "Hawaiian": 16.99,
    }

    def __init__(self, event_bus: EventBus):
        """Initialize the order processor with an event bus."""
        self._event_bus = event_bus
        self._orders = {}  # order_id -> order_data
        self._order_statuses = {}  # order_id -> "pending" or "completed"

    def place_order(
        self, order_id: str, customer_name: str, pizza_type: str, quantity: int
    ) -> None:
        """Place a new pizza order."""
        # Validate order ID uniqueness
        if order_id in self._orders:
            raise ValueError(f"Order {order_id} already exists")

        # Validate pizza type
        if pizza_type not in self.MENU_PRICES:
            raise ValueError(f"Invalid pizza type: {pizza_type}")

        # Validate quantity
        if not isinstance(quantity, int) or quantity <= 0 or quantity > 5:
            raise ValueError(
                "Quantity must be a positive integer between 1 and 5"
            )

        # Calculate total price
        total_price = self.MENU_PRICES[pizza_type] * quantity

        # Store order
        order_data = {
            "order_id": order_id,
            "customer_name": customer_name,
            "pizza_type": pizza_type,
            "quantity": quantity,
            "total_price": total_price,
        }

        self._orders[order_id] = order_data
        self._order_statuses[order_id] = "pending"

        # Publish event
        self._event_bus.publish("ORDER_PLACED", order_data)

    def complete_order(self, order_id: str) -> None:
        """Mark an order as completed."""
        # Validate order exists
        if order_id not in self._orders:
            raise ValueError(f"Order {order_id} does not exist")

        # Validate order is not already completed
        if self._order_statuses[order_id] == "completed":
            raise ValueError(f"Order {order_id} is already completed")

        # Update status
        self._order_statuses[order_id] = "completed"

        # Get order data for event
        order_data = self._orders[order_id].copy()

        # Publish event
        self._event_bus.publish("ORDER_COMPLETED", order_data)


class OrderAnalytics:
    """Handles read operations - analytics and queries."""

    def __init__(self, event_bus: EventBus):
        """Initialize analytics with event bus subscription."""
        self._event_bus = event_bus
        self._event_bus.subscribe(self)

        # Cached analytics data
        self._pending_orders = []  # List of order_ids
        self._total_revenue = 0.0
        self._order_count = 0

    def handle_event(self, event_type: str, data: Dict):
        """Handle events from OrderProcessor."""
        if event_type == "ORDER_PLACED":
            self._pending_orders.append(data["order_id"])
            self._order_count += 1

        elif event_type == "ORDER_COMPLETED":
            # Remove from pending orders
            if data["order_id"] in self._pending_orders:
                self._pending_orders.remove(data["order_id"])

            # Add to total revenue
            self._total_revenue += data["total_price"]

    def get_pending_orders(self) -> List[str]:
        """Get list of pending order IDs."""
        return self._pending_orders.copy()

    def get_total_revenue(self) -> float:
        """Get total revenue from completed orders."""
        return round(self._total_revenue, 2)

    def get_order_count(self) -> int:
        """Get total number of orders placed."""
        return self._order_count


def process_restaurant_operations(operations: List[Tuple]) -> List[Any]:
    """Process restaurant operations and return query results."""
    # Initialize event bus and components
    event_bus = EventBus()
    processor = OrderProcessor(event_bus)
    analytics = OrderAnalytics(event_bus)

    results = []

    for operation in operations:
        # Handle both tuple and string operations
        if isinstance(operation, str):
            op_type = operation
        else:
            op_type = operation[0]

        if op_type == "PLACE_ORDER":
            _, order_id, customer_name, pizza_type, quantity = operation
            processor.place_order(
                order_id, customer_name, pizza_type, quantity
            )

        elif op_type == "COMPLETE_ORDER":
            _, order_id = operation
            processor.complete_order(order_id)

        elif op_type == "GET_PENDING_ORDERS":
            results.append(analytics.get_pending_orders())

        elif op_type == "GET_TOTAL_REVENUE":
            results.append(analytics.get_total_revenue())

        elif op_type == "GET_ORDER_COUNT":
            results.append(analytics.get_order_count())

    return results


# Driver function for testing
def main():
    """Driver function to test the implementation."""
    # Test Example 1
    print("Example 1:")
    operations1 = [
        ("PLACE_ORDER", "ORD001", "Alice", "Margherita", 2),
        ("GET_PENDING_ORDERS"),
        ("COMPLETE_ORDER", "ORD001"),
        ("GET_TOTAL_REVENUE"),
    ]
    result1 = process_restaurant_operations(operations1)
    print(f"Input: {operations1}")
    print(f"Output: {result1}")
    print("Expected: [['ORD001'], 25.98]")
    print()

    # Test Example 2
    print("Example 2:")
    operations2 = [
        ("PLACE_ORDER", "ORD001", "Bob", "Pepperoni", 1),
        ("PLACE_ORDER", "ORD002", "Carol", "Vegetarian", 3),
        ("GET_ORDER_COUNT"),
        ("COMPLETE_ORDER", "ORD001"),
        ("GET_PENDING_ORDERS"),
        ("GET_TOTAL_REVENUE"),
    ]
    result2 = process_restaurant_operations(operations2)
    print(f"Input: {operations2}")
    print(f"Output: {result2}")
    print("Expected: [2, ['ORD002'], 15.99]")
    print()

    # Test edge cases
    print("Testing edge cases:")

    # Test empty system
    empty_ops = [
        ("GET_PENDING_ORDERS"),
        ("GET_TOTAL_REVENUE"),
        ("GET_ORDER_COUNT"),
    ]
    empty_result = process_restaurant_operations(empty_ops)
    print(f"Empty system: {empty_result}")
    print("Expected: [[], 0.0, 0]")
    print()

    # Test error cases
    try:
        # Duplicate order ID
        ops = [
            ("PLACE_ORDER", "ORD001", "Alice", "Margherita", 2),
            ("PLACE_ORDER", "ORD001", "Bob", "Pepperoni", 1),
        ]
        process_restaurant_operations(ops)
        print("ERROR: Should have raised ValueError for duplicate order")
    except ValueError as e:
        print(f"Correctly caught duplicate order error: {e}")

    try:
        # Invalid pizza type
        ops = [("PLACE_ORDER", "ORD001", "Alice", "InvalidPizza", 1)]
        process_restaurant_operations(ops)
        print("ERROR: Should have raised ValueError for invalid pizza type")
    except ValueError as e:
        print(f"Correctly caught invalid pizza error: {e}")

    try:
        # Invalid quantity
        ops = [("PLACE_ORDER", "ORD001", "Alice", "Margherita", 0)]
        process_restaurant_operations(ops)
        print("ERROR: Should have raised ValueError for invalid quantity")
    except ValueError as e:
        print(f"Correctly caught invalid quantity error: {e}")

    try:
        # Complete non-existent order
        ops = [("COMPLETE_ORDER", "NONEXISTENT")]
        process_restaurant_operations(ops)
        print("ERROR: Should have raised ValueError for non-existent order")
    except ValueError as e:
        print(f"Correctly caught non-existent order error: {e}")

    try:
        # Complete already completed order
        ops = [
            ("PLACE_ORDER", "ORD001", "Alice", "Margherita", 1),
            ("COMPLETE_ORDER", "ORD001"),
            ("COMPLETE_ORDER", "ORD001"),
        ]
        process_restaurant_operations(ops)
        print(
            "ERROR: Should have raised ValueError for already completed order"
        )
    except ValueError as e:
        print(f"Correctly caught already completed order error: {e}")


if __name__ == "__main__":
    main()

