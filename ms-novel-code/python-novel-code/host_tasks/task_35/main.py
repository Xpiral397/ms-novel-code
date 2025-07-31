
"""AI Rate Limiter Implementation for Task 69308."""

import time
import heapq
from functools import wraps
from typing import Dict, List, Tuple, Any, Callable


class AIRateLimiter:
    """Factory class for creating AI platform rate limiters."""

    def __init__(
        self,
        tier_configs: Dict[str, Dict],
        time_windows: List[int],
        operation_costs: Dict[str, int],
        limiter_type: str,
    ):
        """Initialize the rate limiter factory."""
        self.tier_configs = tier_configs
        self.time_windows = time_windows
        self.operation_costs = operation_costs
        self.limiter_type = limiter_type
        self.user_state: Dict[str, Dict[int, List[Tuple[float, int]]]] = {}
        self.request_queue: List[Tuple[int, float, str, Dict]] = []
        self._priority_map = {
            tier: config["priority"] for tier, config in tier_configs.items()
        }
        self.user_tiers: Dict[str, str] = {}

    def _validate_inputs(
        self, user_id: str, tier: str, operation: str, content: str
    ) -> None:
        """Validate all inputs before processing."""
        if not isinstance(user_id, str) or not user_id.strip():
            raise ValueError("user_id must be a non-empty string")

        if not isinstance(tier, str) or tier not in self.tier_configs:
            raise ValueError(
                f"Unknown tier: {tier}. Available tiers: "
                f"{list(self.tier_configs.keys())}"
            )

        if not isinstance(operation, str) or not operation.strip():
            raise ValueError("operation must be a non-empty string")

        if not isinstance(content, str):
            raise ValueError("content must be a string")

        tier_config = self.tier_configs[tier]
        required_key = "token_limits" if self.limiter_type == "token" else "limits"
        if required_key not in tier_config:
            raise ValueError(f"Tier {tier} missing {required_key} configuration")

        limits = tier_config[required_key]
        if len(limits) != len(self.time_windows):
            raise ValueError(
                f"Tier {tier} has {len(limits)} limits but "
                f"{len(self.time_windows)} time windows"
            )

    def get_token_count(self, content: str) -> int:
        """Calculate token count from content."""
        if not content or not content.strip():
            return 1
        return len(content.split())

    def create_limiter(self) -> Callable:
        """Create appropriate decorator based on limiter_type."""
        if self.limiter_type == "token":
            return self._create_token_limiter()
        elif self.limiter_type == "request":
            return self._create_request_limiter()
        else:
            raise ValueError(f"Unknown limiter type: {self.limiter_type}")

    def _create_token_limiter(self) -> Callable:
        """Create token-based rate limiter decorator."""

        @wraps(self._create_token_limiter)
        def token_limiter(func: Callable) -> Callable:
            @wraps(func)
            def wrapper(
                user_id: str, tier: str, operation: str, content: str
            ) -> Dict[str, Any]:
                self._validate_inputs(user_id, tier, operation, content)
                current_time = time.time()
                self.user_tiers[user_id] = tier
                token_count = self.get_token_count(content)
                consumption = token_count * self.operation_costs.get(operation, 1)

                if self._check_rate_limits(user_id, tier, consumption, current_time):
                    self._record_consumption(user_id, consumption, current_time)
                    result = func(user_id, tier, operation, content)
                    remaining_tokens = self._calculate_remaining_capacity(
                        user_id, tier, current_time
                    )
                    return {
                        "result": result,
                        "rate_limit_info": {
                            "tokens_consumed": consumption,
                            "remaining_tokens": remaining_tokens,
                        },
                    }
                else:
                    return self._add_to_queue(
                        user_id,
                        tier,
                        {
                            "operation": operation,
                            "content": content,
                            "consumption": consumption,
                        },
                    )

            return wrapper

        return token_limiter

    def _create_request_limiter(self) -> Callable:
        """Create request-based rate limiter decorator."""

        @wraps(self._create_request_limiter)
        def request_limiter(func: Callable) -> Callable:
            @wraps(func)
            def wrapper(
                user_id: str, tier: str, operation: str, content: str
            ) -> Dict[str, Any]:
                self._validate_inputs(user_id, tier, operation, content)
                current_time = time.time()
                self.user_tiers[user_id] = tier
                consumption = 1

                if self._check_rate_limits(user_id, tier, consumption, current_time):
                    self._record_consumption(user_id, consumption, current_time)
                    result = func(user_id, tier, operation, content)
                    remaining_requests = self._calculate_remaining_capacity(
                        user_id, tier, current_time
                    )
                    return {
                        "result": result,
                        "rate_limit_info": {
                            "requests_consumed": consumption,
                            "remaining_requests": remaining_requests,
                        },
                    }
                else:
                    return self._add_to_queue(
                        user_id,
                        tier,
                        {
                            "operation": operation,
                            "content": content,
                            "consumption": consumption,
                        },
                    )

            return wrapper

        return request_limiter

    def _check_rate_limits(
        self, user_id: str, tier: str, consumption: int, current_time: float
    ) -> bool:
        """Check if request is within rate limits for all time windows."""
        self._cleanup_expired_entries(user_id, current_time)
        tier_config = self.tier_configs.get(tier, {})
        limits = (
            tier_config.get("limits", [])
            if self.limiter_type == "request"
            else tier_config.get("token_limits", [])
        )

        for window_idx, limit in enumerate(limits):
            current_usage = self._get_window_usage(user_id, window_idx)
            if current_usage + consumption > limit:
                return False

        return True

    def _cleanup_expired_entries(self, user_id: str, current_time: float) -> None:
        """Remove expired entries from user state."""
        if user_id not in self.user_state:
            return

        for window_idx, window_seconds in enumerate(self.time_windows):
            if window_idx in self.user_state[user_id]:
                cutoff_time = current_time - window_seconds
                self.user_state[user_id][window_idx] = [
                    (timestamp, consumption)
                    for timestamp, consumption in self.user_state[user_id][window_idx]
                    if timestamp > cutoff_time
                ]

    def _get_window_usage(self, user_id: str, window_idx: int) -> int:
        """Get current usage for a specific time window."""
        if user_id not in self.user_state or window_idx not in self.user_state[user_id]:
            return 0
        return sum(
            consumption for _, consumption in self.user_state[user_id][window_idx]
        )

    def _record_consumption(
        self, user_id: str, consumption: int, timestamp: float
    ) -> None:
        """Record consumption across all time windows."""
        if user_id not in self.user_state:
            self.user_state[user_id] = {}

        for window_idx in range(len(self.time_windows)):
            if window_idx not in self.user_state[user_id]:
                self.user_state[user_id][window_idx] = []
            self.user_state[user_id][window_idx].append((timestamp, consumption))

    def _calculate_remaining_capacity(
        self, user_id: str, tier: str, current_time: float
    ) -> List[int]:
        """Calculate remaining capacity for each time window."""
        self._cleanup_expired_entries(user_id, current_time)
        tier_config = self.tier_configs.get(tier, {})
        limits = (
            tier_config.get("limits", [])
            if self.limiter_type == "request"
            else tier_config.get("token_limits", [])
        )

        remaining = []
        for window_idx, limit in enumerate(limits):
            current_usage = self._get_window_usage(user_id, window_idx)
            remaining.append(max(0, limit - current_usage))

        return remaining

    def _add_to_queue(
        self, user_id: str, tier: str, request_data: Dict
    ) -> Dict[str, Any]:
        """Add request to priority queue."""
        current_time = time.time()
        priority = self._priority_map.get(tier, 999)

        queue_position = (
            sum(
                1
                for p, t, _, _ in self.request_queue
                if p < priority or (p == priority and t < current_time)
            )
            + 1
        )

        heapq.heappush(
            self.request_queue, (priority, current_time, user_id, request_data)
        )

        estimated_wait_time = min(self.time_windows)

        return {
            "status": "queued",
            "queue_position": queue_position,
            "estimated_wait_time": estimated_wait_time,
        }

    def process_queue(self) -> List[Dict]:
        """Process queued requests that can now be executed."""
        processed = []
        current_time = time.time()

        while self.request_queue:
            priority, timestamp, user_id, request_data = self.request_queue[0]
            tier = self.user_tiers.get(user_id, "unknown")
            if tier == "unknown":
                heapq.heappop(self.request_queue)
                continue

            if self._check_rate_limits(
                user_id, tier, request_data["consumption"], current_time
            ):
                heapq.heappop(self.request_queue)
                self._record_consumption(
                    user_id, request_data["consumption"], current_time
                )
                processed.append(
                    {
                        "user_id": user_id,
                        "tier": tier,
                        "operation": request_data["operation"],
                        "content": request_data["content"],
                        "processed": True,
                    }
                )
            else:
                break

        return processed

## Optional code to run test cases, and check main file for issue

def generate_text(user_id: str, tier: str, operation: str, content: str) -> str:
    """Mock function that generates text."""
    return content


def run_examples():
    """Run the examples from the problem statement."""
    results = []

    # Example 1: Request-based rate limiting
    methods = [
        "AIRateLimiter",
        "create_limiter",
        "generate_text",
        "generate_text",
        "generate_text",
    ]
    parameters = [
        [{"pro": {"limits": [2, 10], "priority": 2}}, [1, 60], {}, "request"],
        [],
        ["user1", "pro", "text_gen", "hello"],
        ["user1", "pro", "text_gen", "world"],
        ["user1", "pro", "text_gen", "test"],
    ]

    # Execute methods
    limiter = None
    decorator_func = None

    for i, (method, params) in enumerate(zip(methods, parameters)):
        if method == "AIRateLimiter":
            limiter = AIRateLimiter(*params)
            results.append(None)
        elif method == "create_limiter":
            decorator_func = limiter.create_limiter()
            results.append("decorator_function")
        elif method == "generate_text":
            if decorator_func:
                decorated_func = decorator_func(generate_text)
                result = decorated_func(*params)
                results.append(result)

    return results


def run_all_examples():
    """Run all examples from the problem statement."""
    print("=== Testing All Examples ===\n")

    # Example 1: Request-based rate limiting
    print("Example 1: Request-based rate limiting")
    methods1 = [
        "AIRateLimiter",
        "create_limiter",
        "generate_text",
        "generate_text",
        "generate_text",
    ]
    parameters1 = [
        [{"pro": {"limits": [2, 10], "priority": 2}}, [1, 60], {}, "request"],
        [],
        ["user1", "pro", "text_gen", "hello"],
        ["user1", "pro", "text_gen", "world"],
        ["user1", "pro", "text_gen", "test"],
    ]

    results1 = []
    limiter1 = None
    decorator_func1 = None

    for i, (method, params) in enumerate(zip(methods1, parameters1)):
        if method == "AIRateLimiter":
            limiter1 = AIRateLimiter(*params)
            results1.append(None)
        elif method == "create_limiter":
            decorator_func1 = limiter1.create_limiter()
            results1.append("decorator_function")
        elif method == "generate_text":
            if decorator_func1:
                decorated_func1 = decorator_func1(generate_text)
                result = decorated_func1(*params)
                results1.append(result)

    for i, result in enumerate(results1):
        print(f"  {i+1}: {result}")

    # Example 2: Token-based rate limiting
    print("\nExample 2: Token-based rate limiting")
    methods2 = ["AIRateLimiter", "create_limiter", "generate_text"]
    parameters2 = [
        [
            {"pro": {"token_limits": [5, 50], "priority": 2}},
            [1, 60],
            {"text_gen": 2},
            "token",
        ],
        [],
        ["user1", "pro", "text_gen", "one two three"],
    ]

    results2 = []
    limiter2 = None
    decorator_func2 = None

    for i, (method, params) in enumerate(zip(methods2, parameters2)):
        if method == "AIRateLimiter":
            limiter2 = AIRateLimiter(*params)
            results2.append(None)
        elif method == "create_limiter":
            decorator_func2 = limiter2.create_limiter()
            results2.append("decorator_function")
        elif method == "generate_text":
            if decorator_func2:
                decorated_func2 = decorator_func2(generate_text)
                result = decorated_func2(*params)
                results2.append(result)

    for i, result in enumerate(results2):
        print(f"  {i+1}: {result}")

    # Example 3: Successful token consumption
    print("\nExample 3: Successful token consumption")
    methods3 = ["AIRateLimiter", "create_limiter", "get_token_count", "generate_text"]
    parameters3 = [
        [
            {"pro": {"token_limits": [5, 50], "priority": 2}},
            [1, 60],
            {"text_gen": 2},
            "token",
        ],
        [],
        ["hello"],
        ["user1", "pro", "text_gen", "hello"],
    ]

    results3 = []
    limiter3 = None
    decorator_func3 = None

    for i, (method, params) in enumerate(zip(methods3, parameters3)):
        if method == "AIRateLimiter":
            limiter3 = AIRateLimiter(*params)
            results3.append(None)
        elif method == "create_limiter":
            decorator_func3 = limiter3.create_limiter()
            results3.append("decorator_function")
        elif method == "get_token_count":
            token_count = limiter3.get_token_count(*params)
            results3.append(token_count)
        elif method == "generate_text":
            if decorator_func3:
                decorated_func3 = decorator_func3(generate_text)
                result = decorated_func3(*params)
                results3.append(result)

    for i, result in enumerate(results3):
        print(f"  {i+1}: {result}")


if __name__ == "__main__":
    example_results = run_examples()
    print("Example Results:")
    for i, result in enumerate(example_results):
        print(f"  {i+1}: {result}")

    print("\n" + "=" * 50 + "\n")

    # Test all examples
    run_all_examples()

