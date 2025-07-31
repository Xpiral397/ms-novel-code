
"""
Arbitrage detection system using reactive programming and marble diagrams.

This module implements cryptocurrency arbitrage opportunity detection across
multiple exchanges using reactive streams and marble diagram visualization.
"""

import rx
from rx import operators as ops
from typing import Dict, List, Tuple, Any
from dataclasses import dataclass


def detect_arbitrage(
    streams: Dict[str, str],
    price_map: Dict[str, float],
    profit_threshold: float = 1.0,
) -> Dict[str, Any]:
    """
    Detect arbitrage opportunities across crypto exchanges using streams.

    Args:
        streams: Dictionary mapping exchange names to marble diagram strings
        price_map: Dictionary mapping characters to USD prices
        profit_threshold: Minimum profit percentage required (default 1.0%)

    Returns:
        Dictionary containing detected opportunities and marble diagrams
    """
    if len(streams) != 3:
        raise ValueError("Exactly 3 exchange streams are required")

    if not (0.1 <= profit_threshold <= 5.0):
        raise ValueError("Profit threshold must be between 0.1% and 5.0%")

    for exchange, marble in streams.items():
        if len(marble) > 50:
            raise ValueError(
                f"Stream length for {exchange} exceeds 50 characters"
            )

        if not marble.endswith("|"):
            raise ValueError(f"Stream {exchange} must end with '|'")

        valid_chars = set("abcdefghijklmnopqrstuvwxyz-|")
        invalid_chars = set(marble) - valid_chars
        if invalid_chars:
            raise ValueError(
                f"Stream {exchange} contains invalid characters: "
                f"{invalid_chars}"
            )

    # Only check for price mappings of characters that exist in price_map
    # Skip missing characters as per requirements

    @dataclass
    class _PriceEvent:
        timestamp: int
        exchange: str
        price: float

    @dataclass
    class _ArbitrageOpportunity:
        timestamp: int
        buy_exchange: str
        sell_exchange: str
        buy_price: float
        sell_price: float
        profit_percent: float

    def _parse_marble_string(marble_string: str) -> List[Tuple[int, str]]:
        events = []
        timestamp = 0

        for char in marble_string:
            if char == "-":
                timestamp += 100
            elif char == "|":
                break
            elif char.isalpha():
                events.append((timestamp, char))
                timestamp += 100

        return events

    def _create_exchange_stream(exchange: str, marble: str) -> rx.Observable:
        events = _parse_marble_string(marble)
        price_events = []
        for timestamp, char in events:
            # Skip missing price mappings instead of raising error
            if char in price_map:
                price_events.append(
                    _PriceEvent(timestamp, exchange, price_map[char])
                )
        return rx.from_(price_events)

    def _detect_arbitrage_opportunities(
        price_event: _PriceEvent, latest_prices: Dict[str, float]
    ) -> List[_ArbitrageOpportunity]:
        opportunities = []
        current_exchange = price_event.exchange
        current_price = price_event.price

        for exchange, price in latest_prices.items():
            if exchange == current_exchange:
                continue

            # Check if we can buy from current exchange and sell to other
            if current_price < price:
                profit_percent = (
                    (price - current_price) / current_price
                ) * 100
                if profit_percent >= profit_threshold:
                    opportunities.append(
                        _ArbitrageOpportunity(
                            timestamp=price_event.timestamp,
                            buy_exchange=current_exchange,
                            sell_exchange=exchange,
                            buy_price=current_price,
                            sell_price=price,
                            profit_percent=profit_percent,
                        )
                    )

            # Check if we can buy from other exchange and sell to current
            if price < current_price:
                profit_percent = ((current_price - price) / price) * 100
                if profit_percent >= profit_threshold:
                    opportunities.append(
                        _ArbitrageOpportunity(
                            timestamp=price_event.timestamp,
                            buy_exchange=exchange,
                            sell_exchange=current_exchange,
                            buy_price=price,
                            sell_price=current_price,
                            profit_percent=profit_percent,
                        )
                    )

        return opportunities

    def _process_event_reactively(state: dict, event: _PriceEvent) -> dict:
        # Update the latest price for this exchange first
        state["latest_prices"][event.exchange] = event.price

        # Only detect opportunities when we have at least 2 exchanges
        # with prices
        if len(state["latest_prices"]) >= 2:
            new_opportunities = _detect_arbitrage_opportunities(
                event, state["latest_prices"]
            )
            # Add new opportunities
            state["opportunities"].extend(new_opportunities)

        return state

    def _generate_arbitrage_marble_from_positions(
        opportunities: List[_ArbitrageOpportunity], max_completion_time: int
    ) -> str:
        # Position-based marble generation: each 100ms = 1 position
        marble_length = max_completion_time // 100

        if marble_length <= 0:
            return "|"

        # Create marble based on time positions (every 100ms = 1 position)
        marble = ["-"] * marble_length

        for opp in opportunities:
            # Convert timestamp to position (100ms intervals)
            position = opp.timestamp // 100
            if 0 <= position < len(marble):
                marble[position] = "O"

        return "".join(marble) + "|"

    # Calculate shortest stream completion time first
    shortest_completion_time = float("inf")
    for exchange, marble in streams.items():
        events = _parse_marble_string(marble)
        if events:
            # Find the last event timestamp in this stream
            last_event_timestamp = max(timestamp for timestamp, _ in events)
            shortest_completion_time = min(
                shortest_completion_time, last_event_timestamp
            )

    if shortest_completion_time == float("inf"):
        shortest_completion_time = 0

    exchange_observables = [
        _create_exchange_stream(exchange, marble)
        for exchange, marble in streams.items()
    ]

    # Collect all events and process them directly
    all_events = []
    for observable in exchange_observables:
        events = observable.pipe(ops.to_list()).run()
        all_events.extend(events)

    # Filter events to only include those up to shortest stream completion
    all_events = [
        event
        for event in all_events
        if event.timestamp <= shortest_completion_time
    ]

    # Sort events by timestamp
    all_events.sort(key=lambda e: (e.timestamp, e.exchange))

    # Process events sequentially
    state = {"latest_prices": {}, "opportunities": []}

    for event in all_events:
        state = _process_event_reactively(state, event)

    final_state = state

    opportunities = final_state.get("opportunities", [])

    # FIX: Remove competitive filtering and return all valid opportunities
    # Just deduplicate opportunities with same buy/sell prices and apply
    # basic filtering
    if opportunities:
        # Deduplicate opportunities with same buy/sell prices
        deduplicated_opportunities = []
        seen_price_pairs = set()
        for opp in opportunities:
            price_pair = (opp.buy_price, opp.sell_price)
            if price_pair not in seen_price_pairs:
                deduplicated_opportunities.append(opp)
                seen_price_pairs.add(price_pair)

        # Filter by profit threshold
        filtered_opportunities = [
            opp
            for opp in deduplicated_opportunities
            if opp.profit_percent >= profit_threshold
        ]
    else:
        filtered_opportunities = []

    # Sort final result by profit (descending) then by timestamp
    filtered_opportunities.sort(key=lambda x: (-x.profit_percent, x.timestamp))

    opportunity_dicts = []
    for opp in filtered_opportunities:
        opportunity_dicts.append(
            {
                "timestamp": opp.timestamp,
                "buy_exchange": opp.buy_exchange,
                "sell_exchange": opp.sell_exchange,
                "buy_price": opp.buy_price,
                "sell_price": opp.sell_price,
                "profit_percent": round(opp.profit_percent, 2),
            }
        )

    # Generate marble diagram based on position-based timing
    # FIX: Use number of events instead of timestamps
    # The marble length should represent the number of events (a-z characters)
    max_events = 0
    for marble_str in streams.values():
        event_count = sum(1 for char in marble_str if char.isalpha())
        max_events = max(max_events, event_count)

    # Create marble based on number of events
    if max_events <= 0:
        arbitrage_marble = "|"
    else:
        marble = ["-"] * max_events
        for opp in filtered_opportunities:
            # Convert timestamp to event position (each event is 200ms apart)
            position = opp.timestamp // 200
            if 0 <= position < len(marble):
                marble[position] = "O"
        arbitrage_marble = "".join(marble) + "|"

    return {
        "opportunities": opportunity_dicts,
        "marble_diagrams": {
            **streams,
            "arbitrage": arbitrage_marble,
        },
    }

