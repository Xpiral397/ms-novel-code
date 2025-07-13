
""" AI Rate Limiter. """

import time
from typing import Dict, List, Any, Callable


class AIRateLimiter:
    """Factory for creating AI platform rate limiters with priority queuing."""

    def __init__(
        self,
        tier_configs: Dict[str, Dict],
        time_windows: List[int],
        operation_costs: Dict[str, int],
        limiter_type: str,
    ):
        """
        Initialize rate limiter factory.

        Args:
            tier_configs: {tier: {limits/token_limits: [w1, w2, w3],
                          priority: int}}
            time_windows: [seconds] for each window
            operation_costs: {operation: cost_multiplier}
            limiter_type: "request" or "token"
        """
        self.tier_configs = tier_configs
        self.time_windows = time_windows
        self.operation_costs = operation_costs
        self.limiter_type = limiter_type


        self.user_usage: Dict[str, Dict[int, List[tuple]]] = (
            {}
        )  # user -> window -> [(timestamp, consumption)]
        self.queue: List[Dict] = []  # Priority queue for blocked requests
        self._queue_id_counter = 0  # Unique ID for each queue entry

    def get_token_count(self, content: str) -> int:
        """Calculate token count from content by splitting on whitespace."""
        if not content or not content.strip():
            return 1
        return len(content.strip().split())

    def create_limiter(self) -> Callable:
        """Return decorator based on limiter_type."""

        def decorator(func: Callable) -> Callable:
            def wrapper(
                user_id: str,
                tier: str,
                operation: str,
                content: str,
                *args,
                **kwargs
            ):
                current_time = time.time()

                # Calculate consumption based on mode
                if self.limiter_type == "request":
                    consumption = 1
                else:  # token mode
                    token_count = self.get_token_count(content)
                    op_cost = self.operation_costs.get(operation, 1)
                    consumption = token_count * op_cost

                # Check if request can proceed
                if self._can_proceed(user_id, tier, consumption, current_time):
                    # Record usage and execute
                    self._record_usage(user_id, consumption, current_time)
                    result = func(
                        user_id, tier, operation, content, *args, **kwargs
                    )

                    # Return with rate limit metadata
                    return self._format_success_response(
                        user_id, tier, result, consumption, current_time
                    )
                else:
                    # Queue the request
                    return self._add_to_queue(
                        user_id, tier, operation, content, current_time
                    )

            return wrapper

        return decorator

    def _can_proceed(
        self, user_id: str, tier: str, consumption: int, current_time: float
    ) -> bool:
        """Check if request can proceed within all time window limits."""
        # Clean expired entries first
        self._cleanup_expired_entries(user_id, current_time)

        # Get tier limits
        tier_config = self.tier_configs.get(tier, {})
        limits_key = (
            "token_limits" if self.limiter_type == "token" else "limits"
        )
        limits = tier_config.get(limits_key, [])

        # Check each window - if ANY window would be exceeded, queue the
        # request
        for window_idx, limit in enumerate(limits):
            current_usage = self._get_window_usage(user_id, window_idx)
            if current_usage + consumption > limit:
                return False

        return True

    def _cleanup_expired_entries(
        self, user_id: str, current_time: float
    ) -> None:
        """Remove expired entries from user usage tracking."""
        if user_id not in self.user_usage:
            return

        for window_idx, window_seconds in enumerate(self.time_windows):
            if window_idx in self.user_usage[user_id]:
                cutoff_time = current_time - window_seconds
                self.user_usage[user_id][window_idx] = [
                    (timestamp, consumption)
                    for timestamp, consumption in self.user_usage[user_id][
                        window_idx
                    ]
                    if timestamp
                    > cutoff_time  # Changed from >= to > for proper reset
                ]

    def _get_window_usage(self, user_id: str, window_idx: int) -> int:
        """Get current usage for specific time window."""
        if (
            user_id not in self.user_usage
            or window_idx not in self.user_usage[user_id]
        ):
            return 0

        return sum(
            consumption
            for _, consumption in self.user_usage[user_id][window_idx]
        )

    def _record_usage(
        self, user_id: str, consumption: int, timestamp: float
    ) -> None:
        """Record usage across all time windows."""
        if user_id not in self.user_usage:
            self.user_usage[user_id] = {}

        for window_idx in range(len(self.time_windows)):
            if window_idx not in self.user_usage[user_id]:
                self.user_usage[user_id][window_idx] = []

            self.user_usage[user_id][window_idx].append(
                (timestamp, consumption)
            )

    def _format_success_response(
        self,
        user_id: str,
        tier: str,
        result: Any,
        consumption: int,
        current_time: float,
    ) -> Dict[str, Any]:
        """Format successful response with rate limit metadata."""
        remaining = self._calculate_remaining_capacity(
            user_id, tier, current_time
        )

        if self.limiter_type == "request":
            return {
                "result": result,
                "rate_limit_info": {
                    "requests_consumed": consumption,
                    "remaining_requests": remaining,
                },
            }
        else:  # token mode
            return {
                "result": result,
                "tokens_consumed": consumption,
                "remaining_tokens": remaining,
            }

    def _calculate_remaining_capacity(
        self, user_id: str, tier: str, current_time: float
    ) -> List[int]:
        """Calculate remaining capacity for each time window."""
        # Clean expired entries
        self._cleanup_expired_entries(user_id, current_time)

        # Get tier limits
        tier_config = self.tier_configs.get(tier, {})
        limits_key = (
            "token_limits" if self.limiter_type == "token" else "limits"
        )
        limits = tier_config.get(limits_key, [])

        remaining = []
        for window_idx, limit in enumerate(limits):
            current_usage = self._get_window_usage(user_id, window_idx)
            remaining.append(max(0, limit - current_usage))

        return remaining

    def _add_to_queue(
        self,
        user_id: str,
        tier: str,
        operation: str,
        content: str,
        current_time: float,
    ) -> Dict[str, Any]:
        """Add request to priority queue and return queue status."""
        # Get tier priority
        tier_config = self.tier_configs.get(tier, {})
        priority = tier_config.get("priority", 1)

        # Generate unique ID for this queue entry
        self._queue_id_counter += 1
        queue_id = self._queue_id_counter

        # Add to queue
        queue_entry = {
            "queue_id": queue_id,
            "user_id": user_id,
            "tier": tier,
            "operation": operation,
            "content": content,
            "priority": priority,
            "timestamp": current_time,
        }

        self.queue.append(queue_entry)

        # Sort queue by priority (descending) then by queue_id (ascending)
        # for FIFO
        self.queue.sort(key=lambda x: (-x["priority"], x["queue_id"]))

        # Find position in queue using unique ID - AFTER sorting
        queue_position = 1
        for i, entry in enumerate(self.queue):
            if entry["queue_id"] == queue_id:
                queue_position = i + 1
                break

        return {
            "status": "queued",
            "queue_position": queue_position,
            "estimated_wait_time": self._estimate_wait_time(queue_position),
            "priority_level": priority,
        }

    def _estimate_wait_time(self, queue_position: int) -> int:
        """Estimate wait time based on queue position."""
        # Simple estimation: 1 second per position ahead
        return max(1, queue_position - 1)

