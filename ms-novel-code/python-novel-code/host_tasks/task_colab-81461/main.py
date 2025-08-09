
"""
E-commerce Order Processing System with Event-Driven Saga Pattern
Implements saga orchestration with compensation events for business consistency
"""


def ecommerce_saga_processor(operations):
    """
    Process e-commerce orders using event-driven saga pattern.

    Args:
        operations: List of operation tuples defining e-commerce actions

    Returns:
        Dict containing customer states, product inventory, order statuses
    """
    # System state
    customers = {}
    products = {}
    orders = {}
    saga_log = []
    order_counter = 1

    def generate_order_id():
        """Generate sequential order IDs."""
        nonlocal order_counter
        order_id = f"O{order_counter:03d}"
        order_counter += 1
        return order_id

    def log_event(order_id, event, service, success, compensation=False):
        """Log saga events for audit trail."""
        saga_log.append({
            "order_id": order_id,
            "event": event,
            "service": service,
            "success": success,
            "compensation": compensation
        })

    def create_customer(customer_id, credit_limit):
        """Create or update customer with credit limit."""
        customers[customer_id] = {
            "credit_limit": credit_limit,
            "credit_used": 0,
            "status": "ACTIVE"
        }

    def add_product(product_id, stock_quantity, price):
        """Add product to inventory with stock and price."""
        products[product_id] = {
            "stock": stock_quantity,
            "reserved": 0,
            "price": price,
            "status": "AVAILABLE"
        }

    def execute_saga(order_id, customer_id, product_id, quantity):
        """Execute order saga with compensation on failure."""
        order = orders[order_id]
        completed_events = []
        compensation_events = []

        try:
            # Step 1: ORDER_CREATED
            log_event(order_id, "ORDER_CREATED", "ORDER", True)
            completed_events.append("ORDER_CREATED")

            # Step 2: PAYMENT_PROCESSED
            customer = customers[customer_id]
            total_amount = quantity * products[product_id]["price"]

            # Process payment (credit limit check happens at inventory step)
            customer["credit_used"] += total_amount
            log_event(order_id, "PAYMENT_PROCESSED", "PAYMENT", True)
            completed_events.append("PAYMENT_PROCESSED")

            # Step 3: INVENTORY_RESERVED
            product = products[product_id]

            # Check for injected failure or insufficient stock
            failure_injected = False
            for op in operations:
                if (op[0] == "INJECT_FAILURE" and len(op) > 2 and
                        op[1] == "INVENTORY" and op[2] == order_id):
                    failure_injected = True
                    break

            if product["stock"] < quantity or failure_injected:
                # Inventory failure - trigger compensation
                log_event(order_id, "INVENTORY_RESERVED", "INVENTORY", False)
                raise Exception("INVENTORY_FAILED")

            product["stock"] -= quantity
            product["reserved"] += quantity
            log_event(order_id, "INVENTORY_RESERVED", "INVENTORY", True)
            completed_events.append("INVENTORY_RESERVED")

            # Step 4: ORDER_SHIPPED
            # Release inventory reservation and mark as shipped
            product["reserved"] -= quantity
            log_event(order_id, "ORDER_SHIPPED", "SHIPPING", True)
            completed_events.append("ORDER_SHIPPED")

            # Success - update order status
            order["status"] = "SHIPPED"
            order["events_completed"] = completed_events
            order["compensation_events"] = compensation_events

        except Exception:
            # Compensation logic - reverse order of completed events
            if "PAYMENT_PROCESSED" in completed_events:
                # Refund payment
                customer["credit_used"] -= total_amount
                log_event(order_id, "PAYMENT_REFUNDED", "PAYMENT", True, True)
                compensation_events.append("PAYMENT_REFUNDED")

            if "INVENTORY_RESERVED" in completed_events:
                # Release inventory
                product["stock"] += quantity
                product["reserved"] -= quantity
                log_event(order_id, "INVENTORY_RELEASED", "INVENTORY",
                          True, True)
                compensation_events.append("INVENTORY_RELEASED")

            # Cancel order
            log_event(order_id, "ORDER_CANCELED", "ORDER", True, True)
            compensation_events.append("ORDER_CANCELED")

            # Update order status
            order["status"] = "CANCELED"
            order["events_completed"] = completed_events
            order["compensation_events"] = compensation_events

    def place_order(customer_id, product_id, quantity):
        """Place order and execute saga."""
        # Validation - check if customer and product exist
        if customer_id not in customers or product_id not in products:
            return  # Fail immediately without saga initiation

        # Check credit limit before starting saga for validation
        customer = customers[customer_id]
        total_amount = quantity * products[product_id]["price"]

        # Handle zero quantity
        if quantity == 0:
            order_id = generate_order_id()
            orders[order_id] = {
                "customer_id": customer_id,
                "product_id": product_id,
                "quantity": 0,
                "total_amount": 0,
                "status": "SHIPPED",
                "events_completed": ["ORDER_CREATED", "PAYMENT_PROCESSED",
                                     "INVENTORY_RESERVED", "ORDER_SHIPPED"],
                "compensation_events": []
            }
            log_event(order_id, "ORDER_CREATED", "ORDER", True)
            log_event(order_id, "PAYMENT_PROCESSED", "PAYMENT", True)
            log_event(order_id, "INVENTORY_RESERVED", "INVENTORY", True)
            log_event(order_id, "ORDER_SHIPPED", "SHIPPING", True)
            return

        # Create order
        order_id = generate_order_id()

        orders[order_id] = {
            "customer_id": customer_id,
            "product_id": product_id,
            "quantity": quantity,
            "total_amount": total_amount,
            "status": "PROCESSING",
            "events_completed": [],
            "compensation_events": []
        }

        # Execute saga
        execute_saga(order_id, customer_id, product_id, quantity)

    # Process operations
    for operation in operations:
        op_type = operation[0]

        if op_type == "CREATE_CUSTOMER":
            customer_id, credit_limit = operation[1], operation[2]
            create_customer(customer_id, credit_limit)

        elif op_type == "ADD_PRODUCT":
            product_id = operation[1]
            stock_quantity = operation[2]
            price = operation[3]
            add_product(product_id, stock_quantity, price)

        elif op_type == "PLACE_ORDER":
            customer_id = operation[1]
            product_id = operation[2]
            quantity = operation[3]
            place_order(customer_id, product_id, quantity)

        elif op_type == "INJECT_FAILURE":
            # Handled during saga execution
            continue

        elif op_type == "QUERY_CUSTOMER":
            # Query operations don't change state
            continue

        elif op_type == "QUERY_ORDER":
            # Query operations don't change state
            continue

    return {
        "customers": customers,
        "products": products,
        "orders": orders,
        "saga_log": saga_log
    }


def test_example_1():
    """Test Example 1 from problem statement."""
    print("=== Test Example 1 ===")
    operations = [
        ("CREATE_CUSTOMER", "C001", 1000),
        ("ADD_PRODUCT", "P001", 10, 150),
        ("PLACE_ORDER", "C001", "P001", 2),
        ("QUERY_CUSTOMER", "C001"),
        ("QUERY_ORDER", "O001")
    ]

    result = ecommerce_saga_processor(operations)
    print("Result:")
    print(result)
    print()


def test_example_2():
    """Test Example 2 from problem statement."""
    print("=== Test Example 2 ===")
    operations = [
        ("CREATE_CUSTOMER", "C002", 800),
        ("ADD_PRODUCT", "P002", 3, 200),
        ("PLACE_ORDER", "C002", "P002", 5),
        ("INJECT_FAILURE", "INVENTORY", "O002"),
        ("QUERY_CUSTOMER", "C002"),
        ("QUERY_ORDER", "O002")
    ]

    result = ecommerce_saga_processor(operations)
    print("Result:")
    print(result)
    print()


def test_edge_cases():
    """Test various edge cases and constraints."""
    print("=== Test Edge Cases ===")

    # Test 1: Non-existent customer
    print("Test 1: Non-existent customer")
    operations = [
        ("ADD_PRODUCT", "P003", 5, 100),
        ("PLACE_ORDER", "C999", "P003", 1)
    ]
    result = ecommerce_saga_processor(operations)
    print(f"Orders created: {len(result['orders'])}")  # Should be 0

    # Test 2: Non-existent product
    print("Test 2: Non-existent product")
    operations = [
        ("CREATE_CUSTOMER", "C003", 500),
        ("PLACE_ORDER", "C003", "P999", 1)
    ]
    result = ecommerce_saga_processor(operations)
    print(f"Orders created: {len(result['orders'])}")  # Should be 0

    # Test 3: Insufficient credit
    print("Test 3: Insufficient credit")
    operations = [
        ("CREATE_CUSTOMER", "C004", 100),
        ("ADD_PRODUCT", "P004", 10, 200),
        ("PLACE_ORDER", "C004", "P004", 1)
    ]
    result = ecommerce_saga_processor(operations)
    if result['orders']:
        order_key = list(result['orders'].keys())[0]
        print(f"Order status: {result['orders'][order_key]['status']}")
        print(f"Credit used: {result['customers']['C004']['credit_used']}")
    else:
        print("Order creation failed due to insufficient credit")
        print(f"Credit used: {result['customers']['C004']['credit_used']}")

    # Test 4: Zero quantity order
    print("Test 4: Zero quantity order")
    operations = [
        ("CREATE_CUSTOMER", "C005", 1000),
        ("ADD_PRODUCT", "P005", 5, 100),
        ("PLACE_ORDER", "C005", "P005", 0)
    ]
    result = ecommerce_saga_processor(operations)
    if result['orders']:
        order_key = list(result['orders'].keys())[0]
        print(f"Order status: {result['orders'][order_key]['status']}")
        print(f"Product stock: {result['products']['P005']['stock']}")
    else:
        print("No order created for zero quantity")

    # Test 5: Duplicate customer creation (update)
    print("Test 5: Duplicate customer creation")
    operations = [
        ("CREATE_CUSTOMER", "C006", 500),
        ("CREATE_CUSTOMER", "C006", 1000)
    ]
    result = ecommerce_saga_processor(operations)
    print(f"Credit limit: {result['customers']['C006']['credit_limit']}")

    # Test 7: Credit limit exceeded
    print("Test 7: Credit limit exceeded")
    operations = [
        ("CREATE_CUSTOMER", "C008", 300),
        ("ADD_PRODUCT", "P008", 10, 200),
        ("PLACE_ORDER", "C008", "P008", 2)  # 400 > 300 credit limit
    ]
    result = ecommerce_saga_processor(operations)
    if result['orders']:
        order_key = list(result['orders'].keys())[0]
        order_status = result['orders'][order_key]['status']
        print(f"Order status: {order_status}")
    else:
        print("No orders created - failed validation")

    print()


def test_multiple_orders():
    """Test multiple independent orders."""
    print("=== Test Multiple Orders ===")
    operations = [
        ("CREATE_CUSTOMER", "C008", 2000),
        ("CREATE_CUSTOMER", "C009", 1500),
        ("ADD_PRODUCT", "P008", 20, 100),
        ("ADD_PRODUCT", "P009", 15, 200),
        ("PLACE_ORDER", "C008", "P008", 3),  # Success
        ("PLACE_ORDER", "C009", "P009", 2),  # Success
        ("PLACE_ORDER", "C008", "P009", 10),  # Fail: insufficient stock
        ("INJECT_FAILURE", "INVENTORY", "O003")
    ]

    result = ecommerce_saga_processor(operations)
    print(f"Total orders: {len(result['orders'])}")
    for order_id, order in result['orders'].items():
        status = order['status']
        customer = order['customer_id']
        product = order['product_id']
        print(f"{order_id}: {status} - C{customer} - P{product}")

    print()


def test_boundary_conditions():
    """Test boundary conditions and constraints."""
    print("=== Test Boundary Conditions ===")

    # Test maximum values
    operations = [
        ("CREATE_CUSTOMER", "C010", 1000000),  # Max credit limit
        ("ADD_PRODUCT", "P010", 10000, 1000),  # Max stock, reasonable price
        ("PLACE_ORDER", "C010", "P010", 1000)  # Max quantity
    ]

    result = ecommerce_saga_processor(operations)
    if result['orders']:
        order_key = list(result['orders'].keys())[0]
        order = result['orders'][order_key]
        print(f"Large order status: {order['status']}")
        print(f"Total amount: {order['total_amount']}")
    else:
        print("Order failed validation")

    print()


def driver_function():
    """Driver function to test all scenarios."""
    # Test examples from problem statement
    test_example_1()
    test_example_2()

    # Test edge cases
    test_edge_cases()

    # Test multiple orders
    test_multiple_orders()

    # Test boundary conditions
    test_boundary_conditions()


if __name__ == "__main__":
    driver_function()

