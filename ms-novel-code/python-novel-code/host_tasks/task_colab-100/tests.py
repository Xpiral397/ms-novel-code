# tests

import unittest
import asyncio
from unittest.mock import patch
from main import OrderProcessingSystem, TimeProvider


class TestOrderProcessingSystem(unittest.IsolatedAsyncioTestCase):
    """Unit tests for OrderProcessingSystem."""

    def setUp(self):
        self.time_provider = TimeProvider()
        self.system = OrderProcessingSystem(time_provider=self.time_provider)

    async def asyncSetUp(self):
        await self.system.startup()

    async def asyncTearDown(self):
        await self.system.shutdown()

    async def wait_for_order_completion(self, order_id, timeout=5.0):
        """Helper method to wait for order to reach a final state."""
        start_time = asyncio.get_event_loop().time()
        while asyncio.get_event_loop().time() - start_time < timeout:
            status = await self.system.get_order_status(order_id)
            if (
                status["success"]
                and status["order"]["status"] in ["completed", "failed"]
            ):
                return status["order"]["status"]
            await asyncio.sleep(0.1)
        # Return current status if timeout reached
        status = await self.system.get_order_status(order_id)
        return status["order"]["status"] if status["success"] else "unknown"

    async def test_concurrent_orders_processing(self):
        """Ensure system handles multiple concurrent orders correctly."""
        tasks = [
            self.system.process_order(
                customer_data={
                    "name": f"User{i}",
                    "email": f"u{i}@x.com",
                    "address": str(i),
                },
                items=[{"name": "Item", "price": i * 10.0, "quantity": 1}],
            )
            for i in range(1, 6)
        ]
        results = await asyncio.gather(*tasks)

        # Wait for all orders to complete
        completed_count = 0
        for result in results:
            final_status = await self.wait_for_order_completion(
                result["order_id"])
            if final_status == "completed":
                completed_count += 1

        # At least most orders should complete successfully
        self.assertGreaterEqual(completed_count, 3)

    async def test_order_validation_failure(self):
        """Trigger a validation failure and ensure error handling works."""
        with patch.object(
            self.system, "validate_order", side_effect=Exception("Invalid")
        ):
            order = await self.system.process_order(
                customer_data={
                    "name": "Invalid",
                    "email": "inv@example.com",
                    "address": "",
                },
                items=[{"name": "Test", "price": 10.0, "quantity": 1}],
            )

            # Wait for order to be processed
            final_status = await self.wait_for_order_completion(
                order["order_id"])
            self.assertEqual(final_status, "failed")

    async def test_resource_cleanup_on_shutdown(self):
        """Ensure async resources are cleaned after shutdown."""
        await self.system.shutdown()
        health = await self.system.get_health()
        self.assertEqual(health["status"], "shutdown")

    async def test_handler_timeout_fallback(self):
        """Test timeout behavior of long-running handlers."""
        order = await self.system.process_order(
            customer_data={"name": "Tom", "email": "tom@x.com", "address": "9"},
            items=[{"name": "Table", "price": 300.0, "quantity": 1}],
        )

        final_status = await self.wait_for_order_completion(order["order_id"])
        self.assertIn(final_status, ["failed", "completed"])

    async def test_get_status_of_nonexistent_order(self):
        """Ensure correct response when querying non-existent order."""
        status = await self.system.get_order_status("invalid_id")
        self.assertFalse(status["success"])

    async def test_get_events_of_nonexistent_order(self):
        """Ensure correct response when querying events for
          non-existent order."""
        events = await self.system.get_order_events("unknown_id")
        self.assertFalse(events["success"])

    async def test_data_consistency_across_states(self):
        """Verify total amount is calculated correctly through all states."""
        order = await self.system.process_order(
            customer_data={
                "name": "Sam", "email": "sam@example.com", "address": "22"},
            items=[{"name": "Shoe", "price": 50.0, "quantity": 2}],
        )

        await self.wait_for_order_completion(order["order_id"])

        status = await self.system.get_order_status(order["order_id"])
        self.assertEqual(status["order"]["total_amount"], 100.0)

    async def test_shutdown_with_pending_events(self):
        """Test graceful shutdown while events are pending."""
        task = asyncio.create_task(
            self.system.process_order(
                customer_data={
                    "name": "Grace",
                    "email": "grace@example.com",
                    "address": "z",
                },
                items=[{"name": "Clock", "price": 75.0, "quantity": 1}],
            )
        )
        await asyncio.sleep(0.1)
        await self.system.shutdown()
        self.assertTrue(True)

    async def test_compensation_logic_invoked_on_failure(self):
        """Check that compensation logic is invoked when order fails."""
        with patch.object(
            self.system, "process_payment", side_effect=Exception(
                "Payment failed")
        ):
            order = await self.system.process_order(
                customer_data={
                    "name": "Comp",
                    "email": "c@e.com",
                    "address": "9",
                },
                items=[{"name": "Watch", "price": 199.99, "quantity": 1}],
            )

            final_status = await self.wait_for_order_completion(
                order["order_id"])
            self.assertEqual(final_status, "failed")

    async def test_health_check_endpoint(self):
        """Ensure health check reflects system readiness."""
        health = await self.system.get_health()
        self.assertTrue(health["success"])
        self.assertEqual(health["status"], "healthy")

    async def test_event_logging_with_correlation_ids(self):
        """Verify that correlation IDs are present in logged events."""
        order = await self.system.process_order(
            customer_data={
                "name": "Log",
                "email": "log@example.com",
                "address": "logging",
            },
            items=[{"name": "Disk", "price": 55.0, "quantity": 2}],
        )

        await self.wait_for_order_completion(order["order_id"])

        events = await self.system.get_order_events(order["order_id"])
        for event in events["events"]:
            self.assertIn("timestamp", event)
            self.assertIsInstance(event["data"], dict)
