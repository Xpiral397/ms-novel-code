# tests

import unittest
from main import detect_arbitrage


class TestDetectArbitrage(unittest.TestCase):
    def test_problem_statement_example(self):
        """Test using exact example from problem statement"""
        streams = {
            "exchange_A": "a-b|",
            "exchange_B": "a-c|",
            "exchange_C": "a-d|"
        }
        price_map = {
            "a": 100, "b": 105, "c": 101, "d": 110
        }
        result = detect_arbitrage(streams, price_map)

        # Should find multiple opportunities as per problem statement
        self.assertGreater(len(result["opportunities"]), 0)
        # Check highest profit opportunity (exchange_B to exchange_C: 8.91%)
        highest_profit_opp = result["opportunities"][0]
        self.assertEqual(highest_profit_opp["timestamp"], 200)
        self.assertEqual(highest_profit_opp["buy_price"], 101)
        self.assertEqual(highest_profit_opp["sell_price"], 110)
        self.assertAlmostEqual(highest_profit_opp["profit_percent"], 8.91, places=2)
        self.assertEqual(result["marble_diagrams"]["arbitrage"], "-O|")

    def test_single_opportunity_simple(self):
        """Test with simple case that produces only one opportunity"""
        streams = {
            "exchange_A": "a-b|",
            "exchange_B": "a-a|",  # No price change
            "exchange_C": "a-a|"   # No price change
        }
        price_map = {
            "a": 100, "b": 102  # Only 2% profit between A at different times
        }
        result = detect_arbitrage(streams, price_map)

        # Should find exactly one opportunity
        self.assertEqual(len(result["opportunities"]), 1)
        opp = result["opportunities"][0]
        self.assertEqual(opp["timestamp"], 200)
        self.assertAlmostEqual(opp["profit_percent"], 2.0, places=2)
        self.assertEqual(result["marble_diagrams"]["arbitrage"], "-O|")

    def test_no_opportunities_due_to_low_spread(self):
        streams = {
            "exchange_A": "a-b-c|",
            "exchange_B": "a-b-c|",
            "exchange_C": "a-b-c|"
        }
        price_map = {
            "a": 50000, "b": 50100, "c": 50200
        }
        result = detect_arbitrage(streams, price_map)

        self.assertEqual(result["opportunities"], [])
        self.assertEqual(result["marble_diagrams"]["arbitrage"], "---|")

    def test_multiple_opportunities_with_ordering(self):
        streams = {
            "exchange_A": "a-b-c---e|",
            "exchange_B": "a-b-d---f|",
            "exchange_C": "a-b-e---g|"
        }
        price_map = {
            "a": 50000, "b": 50200, "c": 51000,
            "d": 51100, "e": 52000, "f": 53000, "g": 54000
        }
        result = detect_arbitrage(streams, price_map)

        opps = result["opportunities"]
        self.assertTrue(all(o["profit_percent"] >= 1.0 for o in opps))
        self.assertGreaterEqual(len(opps), 2)
        # Check descending profit order
        profits = [o["profit_percent"] for o in opps]
        self.assertEqual(profits, sorted(profits, reverse=True))

    def test_missing_price_mapping_is_skipped(self):
        streams = {
            "exchange_A": "a-b-c|",
            "exchange_B": "a-x-c|",
            "exchange_C": "a-b-c|"
        }
        price_map = {
            "a": 50000, "b": 50500, "c": 51000  # 'x' is missing
        }
        result = detect_arbitrage(streams, price_map)

        # Should ignore 'x' and not crash
        self.assertIn("x", streams["exchange_B"])
        self.assertIsInstance(result, dict)
        self.assertTrue("opportunities" in result)

    def test_custom_profit_threshold(self):
        streams = {
            "exchange_A": "a-b-c|",
            "exchange_B": "a-b-d|",
            "exchange_C": "a-b-e|"
        }
        price_map = {
            "a": 50000, "b": 50500, "c": 50800,
            "d": 50900, "e": 50950
        }
        # With threshold 0.2%, only one or two opportunities
        result = detect_arbitrage(streams, price_map, profit_threshold=0.2)
        self.assertGreaterEqual(len(result["opportunities"]), 1)

        # With threshold 2%, none should qualify
        result_high = detect_arbitrage(streams, price_map, profit_threshold=2.0)
        self.assertEqual(result_high["opportunities"], [])

    def test_stream_completion_limits_processing(self):
        streams = {
            "exchange_A": "a-b-c-d|",
            "exchange_B": "a-b-c-d|",
            "exchange_C": "a-b|"
        }
        price_map = {
            "a": 50000, "b": 50100, "c": 51000,
            "d": 52000
        }
        result = detect_arbitrage(streams, price_map)

        # Since exchange_C ends early, processing should stop at 200ms
        self.assertEqual(result["marble_diagrams"]["arbitrage"].count("O"), 0)
        self.assertTrue(result["marble_diagrams"]["arbitrage"].endswith("|"))

    def test_invalid_stream_lengths_raise_error(self):
        streams = {
            "exchange_A": "a-b|",
            "exchange_B": "a-b|"
            # Only 2 exchanges
        }
        price_map = {
            "a": 50000, "b": 50100
        }
        with self.assertRaises(ValueError):
            detect_arbitrage(streams, price_map)

    def test_max_stream_length(self):
        # 50 characters (~5 seconds)
        long_stream = "-".join(["a"] * 25) + "|"
        streams = {
            "exchange_A": long_stream,
            "exchange_B": long_stream,
            "exchange_C": long_stream
        }
        price_map = {"a": 50000}
        result = detect_arbitrage(streams, price_map)
        self.assertEqual(len(result["marble_diagrams"]["exchange_A"]), 50)
        self.assertEqual(result["opportunities"], [])

    def test_opportunity_exactly_at_1_percent(self):
        streams = {
            "exchange_A": "a--|",
            "exchange_B": "b--|",
            "exchange_C": "c--|"
        }
        price_map = {
            "a": 50000,
            "b": 50500,  # exactly 1%
            "c": 50200
        }
        result = detect_arbitrage(streams, price_map, profit_threshold=1.0)
        self.assertTrue(any(o["profit_percent"] >= 1.0 for o in result["opportunities"]))

    def test_empty_streams_return_empty_results(self):
        streams = {
            "exchange_A": "|",
            "exchange_B": "|",
            "exchange_C": "|"
        }
        price_map = {}
        result = detect_arbitrage(streams, price_map)
        self.assertEqual(result["opportunities"], [])
        self.assertEqual(result["marble_diagrams"]["arbitrage"], "|")
