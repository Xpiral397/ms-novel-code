# tests


"""
Unit-test suite for a full-spec reactive e-commerce core.

The tests assume that the public API

    process_events(lines: list[str]) -> list[str]

is available for import. Adjust the import if your module name differs.
"""

from __future__ import annotations
import unittest

# import the solution under test
from main import process_events    # <-- change if needed

class ReactiveDashboardTests(unittest.TestCase):
    """Covers every feature in the prompt / requirements."""

    def test_stock_price_view(self) -> None:
        events = [
            "stock A 5",
            "price A 10.0",
            "subscribe V1 A",
            "view V1",
        ]
        exp = ["V1 A:5 A:10.00 50.00"]
        self.assertEqual(process_events(events), exp)

    def test_bundle_discount_subscription(self) -> None:
        events = [
            "bundle B1 A X",
            "stock A 2",
            "stock X 3",
            "price A 10",
            "price X 20",
            "discount B1 10",
            "subscribe bndl B1",       # view id = bndl, target bundle B1
            "view bndl",
            "stock A 1",               # triggers auto push
        ]
        exp = [
            "bndl A:2,X:3 A:9.00,X:18.00 72.00",
            "bndl A:3,X:3 A:9.00,X:18.00 81.00",
        ]
        self.assertEqual(process_events(events), exp)

    def test_bundle_redefinition(self) -> None:
        events = [
            "bundle B A",
            "subscribe V2 B",
            "view V2",
            "bundle B A X",   # redefine adds X
            "stock X 1",
        ]
        exp = [
            "V2 A:0 A:0.00 0.00",
            "V2 A:0,X:1 A:0.00,X:0.00 0.00",
        ]
        self.assertEqual(process_events(events), exp)

    def test_currency_and_fx(self) -> None:
        events = [
            "currency A EUR",
            "rate EUR 1.2",     # 1 EUR = 1.2 USD
            "stock A 1",
            "price A 100",      # 100 EUR
            "subscribe V3 A",
            "view V3",
            "rate EUR 1.1",     # FX change pushes
        ]
        exp = [
            "V3 A:1 A:120.00 120.00",
            "V3 A:1 A:110.00 110.00",
        ]
        self.assertEqual(process_events(events), exp)

    def test_window(self) -> None:
        events = [
            "stock A 1",
            "price A 10",
            "subscribe W A",
            "window W 2",
            "view W",       # tick 1
            "stock A 1",    # tick 2
            "view W",       # tick 3 (window keeps last 2 s)
        ]
        exp = [
            "W A:1 A:10.00 10.00",
            "W A:2 A:10.00 20.00",
        ]
        self.assertEqual(process_events(events), exp)

    def test_alert_predicate(self) -> None:
        events = [
            "stock A 4",
            "price A 10",
            "subscribe Z A",
            "alert Z total_value>50 High!",
            "stock A 2",     # crosses 50, fires once
            "stock A 1",     # still > 50, no repeat
            "stock A -7",    # drops below, resets
            "stock A 6",     # crosses again, fires again
        ]
        out = process_events(events)
        alerts = [ln for ln in out if ln.startswith("ALERT")]
        self.assertEqual(alerts, ["ALERT Z High!", "ALERT Z High!"])

    def test_transaction_commit_and_rollback(self) -> None:
        # commit: one consolidated push
        events_commit = [
            "subscribe T A",
            "begin",
            "stock A 5",
            "price A 2",
            "commit",
        ]
        self.assertEqual(
            process_events(events_commit),
            ["T A:5 A:2.00 10.00"],
        )
        # rollback: no push, manual view only
        events_rollback = [
            "subscribe R A",
            "begin",
            "stock A 5",
            "rollback",
            "view R",
        ]
        self.assertEqual(
            process_events(events_rollback),
            ["R A:0 A:0.00 0.00"],
        )

    def test_unsubscribe(self) -> None:
        events = [
            "subscribe U A",
            "stock A 1",
            "unsubscribe U",
            "stock A 1",   # should not emit
            "view U",      # manual view ignored
        ]
        self.assertEqual(process_events(events), ["U A:1 A:0.00 0.00"])


if __name__ == "__main__":
    unittest.main(exit=False)
