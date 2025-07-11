
"""
Single-file, production-ready, event-driven order processing system in Python
with concurrency, exactly-once event processing, state machine transitions,
error handling, and test/demo driver function.
"""

import asyncio
import uuid
import random
from datetime import datetime
from typing import List, Dict, Any, Optional


class TimeProvider:
    """
    Simple time provider that cycles through a fixed list of ISO timestamps.
    This avoids using datetime.now() or any dynamic system time calls for
    predictable testing and deterministic behavior.
    """

    def __init__(self, times: Optional[List[str]] = None):
        self._times = times or [
            f"2023-01-01T00:{str(i).zfill(2)}:00Z" for i in range(21)
        ]
        self._index = 0

    def get_current_time(self) -> str:
        """Return a fixed ISO8601 string from the internal list."""
        current_time = self._times[self._index % len(self._times)]
        self._index += 1
        return current_time


class SystemTimeProvider:
    """Alternative time provider that uses actual system time."""

    def now(self) -> datetime:
        return datetime.now()


class OrderProcessingSystem:
    """
    Main order processing system that handles order lifecycle through
    event-driven state transitions with concurrency control.
    """

    MAX_PAYMENT_RETRIES = 3

    def __init__(self, time_provider: Optional[TimeProvider] = None):
        self.time_provider = time_provider or TimeProvider()
        self._orders: Dict[str, Dict[str, Any]] = {}
        self._order_events: Dict[str, List[Dict[str, Any]]] = {}
        self._processed_event_ids: set = set()
        self._order_locks: Dict[str, asyncio.Lock] = {}
        self._event_queue: asyncio.Queue = asyncio.Queue()
        self._shutdown_flag = False
        self._event_loop_task: Optional[asyncio.Task] = None
        self._payment_retry_count: Dict[str, int] = {}

    async def process_order(self, customer_data: dict,
                            items: List[dict]) -> dict:
        order_id = str(uuid.uuid4())
        created_at = self.time_provider.get_current_time()
        total_amount = sum(item['price'] * item['quantity'] for item in items)

        self._orders[order_id] = {
            "order_id": order_id,
            "status": "pending",
            "created_at": created_at,
            "updated_at": created_at,
            "customer_data": customer_data,
            "items": items,
            "total_amount": total_amount,
        }

        self._order_events[order_id] = []
        self._order_locks[order_id] = asyncio.Lock()
        self._payment_retry_count[order_id] = 0

        await self._publish_event(
            event_type="ORDER_CREATED",
            order_id=order_id,
            data={"reason": "New order created"}
        )

        return {
            "success": True,
            "order_id": order_id,
            "message": "Order created successfully",
            "timestamp": created_at,
        }

    async def get_order_status(self, order_id: str) -> dict:
        order = self._orders.get(order_id)
        if not order:
            return {"success": False, "order": {}}

        return {
            "success": True,
            "order": {
                "order_id": order["order_id"],
                "status": order["status"],
                "created_at": order["created_at"],
                "updated_at": order["updated_at"],
                "total_amount": order["total_amount"],
            }
        }

    async def get_order_events(self, order_id: str) -> dict:
        if order_id not in self._order_events:
            return {"success": False, "events": []}
        return {"success": True, "events": self._order_events[order_id]}

    async def get_health(self) -> dict:
        return {
            "success": True,
            "status": "shutdown" if self._shutdown_flag else "healthy"
        }

    async def startup(self):
        self._shutdown_flag = False
        self._event_loop_task = asyncio.create_task(
            self._event_consumer_loop())

    async def shutdown(self):
        self._shutdown_flag = True
        if self._event_loop_task:
            while not self._event_queue.empty():
                await asyncio.sleep(0.01)
            self._event_loop_task.cancel()
            try:
                await self._event_loop_task
            except asyncio.CancelledError:
                pass

    async def validate_order(self, order_id: str) -> bool:
        order = self._orders.get(order_id)
        if not order:
            return False
        if not order.get("items"):
            raise Exception("No items in order")
        for item in order["items"]:
            if item.get("price", 0) <= 0:
                raise Exception("Invalid item price")
        return True

    async def process_payment(self, order_id: str) -> bool:
        return await self._attempt_payment(order_id)

    async def _publish_event(
            self, event_type: str, order_id: str, data: dict = None):
        event_id = str(uuid.uuid4())
        timestamp = self.time_provider.get_current_time()
        event = {
            "event_id": event_id,
            "event_type": event_type,
            "order_id": order_id,
            "timestamp": timestamp,
            "data": data or {}
        }
        await self._event_queue.put(event)
        if order_id in self._order_events:
            self._order_events[order_id].append({
                "event_type": event_type,
                "timestamp": timestamp,
                "data": data or {},
                "processed": False
            })

    async def _mark_event_processed(self, order_id: str, event_id: str):
        if order_id not in self._order_events:
            return
        for event in self._order_events[order_id]:
            if not event.get("processed", False):
                event["processed"] = True
                break

    async def _event_consumer_loop(self):
        while not self._shutdown_flag or not self._event_queue.empty():
            try:
                event = await asyncio.wait_for(
                    self._event_queue.get(), timeout=0.1)
            except asyncio.TimeoutError:
                continue

            event_id = event["event_id"]
            if event_id in self._processed_event_ids:
                self._event_queue.task_done()
                continue

            self._processed_event_ids.add(event_id)
            order_id = event["order_id"]
            event_type = event["event_type"]
            data = event["data"]

            try:
                await self._handle_event(event_id, order_id, event_type, data)
            except Exception as ex:
                print(f"[ERROR] Event handling failed: {ex}")
                if order_id in self._orders:
                    await self._on_order_failed(order_id, {"reason": str(ex)})
            finally:
                self._event_queue.task_done()

    async def _handle_event(
            self, event_id: str, order_id: str, event_type: str, data: dict):
        lock = self._order_locks.get(order_id)
        if not lock or order_id not in self._orders:
            return
        async with lock:
            if order_id not in self._orders:
                return
            if event_type == "ORDER_CREATED":
                await self._on_order_created(order_id)
            elif event_type == "ORDER_VALIDATED":
                await self._on_order_validated(order_id)
            elif event_type == "PAYMENT_PROCESSED":
                await self._on_payment_processed(order_id)
            elif event_type == "ORDER_SHIPPED":
                await self._on_order_shipped(order_id)
            elif event_type == "ORDER_FAILED":
                await self._on_order_failed(order_id, data)
            await self._mark_event_processed(order_id, event_id)

    async def _on_order_created(self, order_id: str):
        order = self._orders[order_id]
        try:
            await self.validate_order(order_id)
            order["status"] = "validated"
            order["updated_at"] = self.time_provider.get_current_time()
            await self._publish_event(
                event_type="ORDER_VALIDATED",
                order_id=order_id,
                data={"reason": "Validation successful"}
            )
        except Exception as e:
            await self._publish_event(
                event_type="ORDER_FAILED",
                order_id=order_id,
                data={"reason": f"Validation failed: {str(e)}"}
            )

    async def _on_order_validated(self, order_id: str):
        order = self._orders[order_id]
        order["status"] = "payment_processing"
        order["updated_at"] = self.time_provider.get_current_time()
        try:
            if await self.process_payment(order_id):
                await self._publish_event(
                    event_type="PAYMENT_PROCESSED",
                    order_id=order_id,
                    data={"reason": "Payment OK"}
                )
            else:
                await self._publish_event(
                    event_type="ORDER_FAILED",
                    order_id=order_id,
                    data={"reason": "Payment failed"}
                )
        except Exception as e:
            await self._publish_event(
                event_type="ORDER_FAILED",
                order_id=order_id,
                data={"reason": f"Payment error: {str(e)}"}
            )

    async def _on_payment_processed(self, order_id: str):
        order = self._orders[order_id]
        order["status"] = "shipped"
        order["updated_at"] = self.time_provider.get_current_time()
        await self._publish_event(
            event_type="ORDER_SHIPPED",
            order_id=order_id,
            data={"reason": "Order shipped"}
        )

    async def _on_order_shipped(self, order_id: str):
        order = self._orders[order_id]
        order["status"] = "completed"
        order["updated_at"] = self.time_provider.get_current_time()
        await self._publish_event(
            event_type="ORDER_COMPLETED",
            order_id=order_id,
            data={"reason": "Order flow complete"}
        )

    async def _on_order_failed(self, order_id: str, data: dict):
        order = self._orders.get(order_id)
        if not order:
            return
        order["status"] = "failed"
        order["updated_at"] = self.time_provider.get_current_time()

    async def _attempt_payment(self, order_id: str) -> bool:
        success_chance = 0.9
        attempt_number = self._payment_retry_count.get(order_id, 0)
        self._payment_retry_count[order_id] = attempt_number + 1
        if attempt_number >= self.MAX_PAYMENT_RETRIES:
            return False
        if random.random() < success_chance:
            return True
        await asyncio.sleep(0.01)
        await self._publish_event(
            event_type="ORDER_VALIDATED",
            order_id=order_id,
            data={"reason": f"Payment attempt {attempt_number + 1} failed,\
                   scheduling retry"}
        )
        return False


async def driver():
    custom_times = [
        f"2023-01-01T12:00:{str(i).zfill(2)}Z" for i in range(12)
    ]
    time_provider = TimeProvider(times=custom_times * 50)
    system = OrderProcessingSystem(time_provider=time_provider)
    await system.startup()

    print("Creating a single order:")
    order_data = {
        "customer_data": {
            "name": "John Doe",
            "email": "john@example.com",
            "address": "123 Main St"
        },
        "items": [
            {"name": "Laptop", "price": 999.99, "quantity": 1}
        ]
    }
    response = await system.process_order(
        order_data["customer_data"], order_data["items"])
    print("process_order response:", response)
    order_id = response["order_id"]
    await asyncio.sleep(0.5)
    status = await system.get_order_status(order_id)
    print("Order Status after 0.5s:", status)
    events = await system.get_order_events(order_id)
    print("Order Events after 0.5s:", events)

    print("\nCreating 10 concurrent orders to test concurrency...")

    async def create_and_monitor(index: int):
        customer_data = {
            "name": f"Customer {index}",
            "email": f"customer{index}@example.com",
            "address": f"{index} Concurrency Lane"
        }
        items = [
            {"name": f"Item{index}", "price": round(10 + index * 2.5, 2),\
             "quantity": 2}
        ]
        order_response = await system.process_order(customer_data, items)
        order_id = order_response["order_id"]
        max_attempts = 100
        attempts = 0
        while attempts < max_attempts:
            status_response = await system.get_order_status(order_id)
            if not status_response["success"]:
                break
            order_status = status_response["order"]["status"]
            if order_status in ["completed", "failed"]:
                break
            await asyncio.sleep(0.1)
            attempts += 1
        final_status = await system.get_order_status(order_id)
        print(
            f"[Order {index}, Order ID: {order_id}] Final status: "
            f"{final_status['order']['status'].capitalize()}"
        )

    tasks = [asyncio.create_task(create_and_monitor(i)) for i in range(1, 11)]
    await asyncio.gather(*tasks)

    health_status = await system.get_health()
    print("\nSystem Health before shutdown:", health_status)
    await system.shutdown()
    print("System has been shutdown gracefully.")
    health_status_post_shutdown = await system.get_health()
    print("System Health after shutdown:", health_status_post_shutdown)


def main():
    asyncio.run(driver())


if __name__ == "__main__":
    main()

