
from __future__ import annotations
from dataclasses import dataclass, field
from typing import Tuple, List, Callable, Dict, Optional, Set, Union
import math

###############################################################################
# Event definition and parsing
###############################################################################

@dataclass(frozen=True, slots=True)
class Event:
  # <Issue>: Event needs exactly three fields (kind: str, item: str, arg: int|float) per spec
    kind: str               # e.g. "stock", "price", "subscribe", etc.
    args: Tuple[str, ...]   # subsequent tokens

def parse_event(line: str) -> Event:
    """
    Parse a single line into an Event structure.
    Raises ValueError if format is invalid or unknown kind.
    """
    tokens = line.split()
    if not tokens:
        raise ValueError("Empty line cannot be parsed.")
    kind = tokens[0].lower()
    args = tuple(tokens[1:])
    # Basic sanity check for known kinds:
    valid_kinds = {
        "stock", "price", "currency", "rate", "bundle", 
        "discount", "subscribe", "unsubscribe", "view",
        "window", "alert", "begin", "commit", "rollback"
    }
    if kind not in valid_kinds:
        raise ValueError(f"Unknown event kind: {kind}")
    return Event(kind, args)

###############################################################################
# ReactiveCell for basic observer functionality
###############################################################################

# <Issue>: This should be named ReactiveVar and accept int|float (not just float) per spec
class ReactiveCell:
    """
    A minimal reactive cell holding a float value and supporting subscribers.
    Whenever set(...) is called outside a transaction or at commit time,
    it notifies its subscribers (unless still in open transaction).
    """
    __slots__ = ("_value", "_subscribers")

    def __init__(self, value: float) -> None:
        self._value = value
        self._subscribers: List[Callable[[], None]] = []

    @property
    def value(self) -> float:
        return self._value

    def set(self, v: float) -> None:
        if math.isclose(self._value, v):
            return  # no change => no notification
        self._value = v
        for fn in list(self._subscribers):
            fn()

    def subscribe(self, fn: Callable[[], None]) -> None:
        if fn not in self._subscribers:
            self._subscribers.append(fn)

    def unsubscribe(self, fn: Callable[[], None]) -> None:
        if fn in self._subscribers:
            self._subscribers.remove(fn)

###############################################################################
# Main reactive system state and dispatcher
###############################################################################

def process_events(events: List[str]) -> List[str]:
    """
    Process a list of event-lines synchronously and return the list
    of emitted outputs (snapshots, alerts) in order.
    """

    # -------------------------------------------------------------------------
    # Global data structures
    # -------------------------------------------------------------------------

    # Ticks will increment each time we process an event.  We'll use tick
    # numbers for sliding-window support and for "last updated" tracking.
    current_tick = 0

    # Transaction state.
    in_transaction = False
    transaction_buffer: List[Event] = []

    # Reactive data for items (and bundles). For each item/bundle ID:
    #  - stock, price, discountMultiplier are ReactiveCells to allow
    #    easy observer pattern usage if needed.  
    #  - currency is stored as a string (with a separate set of exchange rates).
    #  - last_update_tick records the last tick in which something relevant changed.
    # Items default to stock=0, price=0.0, discount=1.0, currency="USD".
    stock_cells: Dict[str, ReactiveCell] = {}
    price_cells: Dict[str, ReactiveCell] = {}
    discount_cells: Dict[str, ReactiveCell] = {}
    currency_of: Dict[str, str] = {}
    last_update_tick: Dict[str, int] = {}

    # Exchange rates: code -> rate-to-USD
    # Default if missing is 1.0
    exchange_rates: Dict[str, float] = {}

    # Bundles: adjacency lists.  For a given ID, we store the set of direct children.
    # Bundles can contain items or other bundles.
    bundle_members: Dict[str, Set[str]] = {}

    # We also track parent sets for each item/bundle, so we can do upward discount accumulation.
    # This helps re-compute final discount or to see who is inside whose bundles, etc.
    parents_of: Dict[str, Set[str]] = {}

    # Subscription views:
    #   view_id -> {
    #       "target": str (the ID of item or bundle we watch)
    #       "window": int  (the number of ticks for sliding window)
    #       "alerts": list of (predicateFunction, message, lastFiredBoolean)
    #   }
    # A "predicateFunction" is a callable that, given a snapshot structure,
    # returns True or False. We only emit an alert on a rising edge.
    active_views: Dict[str, dict] = {}

    # We'll accumulate output lines in a list and return at the end.
    output_lines: List[str] = []

    # -------------------------------------------------------------------------
    # Helper utility to ensure a key exists in dictionaries
    # -------------------------------------------------------------------------
    def ensure_exists(item_id: str) -> None:
        if item_id not in stock_cells:
            stock_cells[item_id] = ReactiveCell(0.0)
            price_cells[item_id] = ReactiveCell(0.0)
            discount_cells[item_id] = ReactiveCell(1.0)
            currency_of[item_id] = "USD"
            last_update_tick[item_id] = current_tick
        # If we missed anything else, fix here.

    # -------------------------------------------------------------------------
    # Helper to recursively gather all items within a target (which could be
    # an item or a bundle).  We'll do a DFS to get the "leaf items".
    # For sorting deterministically, we will collect items in a set, then sort.
    # -------------------------------------------------------------------------
    def gather_all_items(target_id: str, visited: Optional[Set[str]] = None) -> List[str]:
        """
        Return the sorted list of all leaf items that are contained by target_id
        (including target_id if it is itself an item).
        """
        if visited is None:
            visited = set()
        if target_id in visited:
            return []
        visited.add(target_id)

        # If target_id is in bundle_members, we gather recursively from children.
        # If not, we treat it as an item.
        if target_id in bundle_members:
            result_set: Set[str] = set()
            for child in bundle_members[target_id]:
                for leaf in gather_all_items(child, visited):
                    result_set.add(leaf)
            return sorted(result_set)
        else:
            # It's an item (or possibly an empty membership if not in dictionary)
            ensure_exists(target_id)
            return [target_id]

    # -------------------------------------------------------------------------
    # Helper to compute the final discount multiplier for a single item
    # by traversing upward (the item can have multiple ancestor bundles).
    # Each ancestor might have its own discount cell. We'll multiply them all.
    # -------------------------------------------------------------------------
    def compute_discount(item_id: str) -> float:
        visited = set()
        product = 1.0
        stack = [item_id]
        while stack:
            nid = stack.pop()
            if nid in visited:
                continue
            visited.add(nid)
            ensure_exists(nid)
            product *= discount_cells[nid].value
            # then push all parents
            for p in parents_of.get(nid, []):
                stack.append(p)
        return product

    # -------------------------------------------------------------------------
    # Helper to find the "effective stock" of an item for a given view's window.
    # We interpret "sliding window" to mean: if last_update_tick[item] is too old
    # relative to (current_tick - window), we treat it as zero/ignored.
    # For stock, we either take the real stock if it's within the window,
    # or zero if it's outside the window. You could adapt different logic.
    # -------------------------------------------------------------------------
    def get_windowed_stock(item_id: str, window: int) -> float:
        if window < 0:
            return stock_cells[item_id].value  # no window restriction
        # If the last update is too old, treat as 0
        if (current_tick - last_update_tick[item_id]) > window:
            return 0.0
        return stock_cells[item_id].value

    # -------------------------------------------------------------------------
    # Helper to produce a snapshot line for a given view
    # -------------------------------------------------------------------------
    def produce_snapshot(view_id: str) -> str:
        vinfo = active_views[view_id]
        target_id = vinfo["target"]
        window = vinfo["window"]
        items = gather_all_items(target_id)
        # Build "item1:qty,... item1:priceUSD,... total_valueUSD"
        # in sorted order of item IDs
        parts_qty = []
        parts_price = []
        total_value = 0.0

        for itm in items:
            # Check if item is inside this view's time window
            qty = get_windowed_stock(itm, window)
            if abs(qty) < 1e-9 and window >= 0:
                # If effectively zero AND we are using a finite window,
                # we skip it from the listing. (Spec is somewhat open here.)
                continue
            # currency
            code = currency_of[itm]
            rate = exchange_rates.get(code, 1.0)
            base_price = price_cells[itm].value
            disc_mult = compute_discount(itm)
            final_price = base_price * (1.0 - disc_mult + 1.0e-15 if disc_mult<1 else 1.0/disc_mult + 1e-15) \
                          if False else base_price * disc_mult
            # The above line is just to remind that you might interpret "discount" as
            #  (price * (1-discount)) or (price*discountMult).  
            # By the problem statement "discounts multiply cumulatively," 
            # so if you have a 10% discount => multiplier=0.9.  Another 10% => 0.9 * 0.9 = 0.81, etc.
            # We'll interpret discountCells as that final multiplier. E.g. 10% off => 0.9.
            final_price = base_price * compute_discount(itm)
            price_usd = final_price * rate
            value_usd = qty * price_usd
            parts_qty.append(f"{itm}:{int(qty)}")
            # We can show float prices with e.g. 2 decimals
            parts_price.append(f"{itm}:{price_usd:.2f}")
            total_value += value_usd

        # Build the final string
        # If no items, we can just show empty lists
        joined_qty = ",".join(parts_qty) if parts_qty else ""
        joined_price = ",".join(parts_price) if parts_price else ""
        return f"{view_id} {joined_qty} {joined_price} {total_value:.2f}"

    # -------------------------------------------------------------------------
    # Evaluate any alert conditions for a given view immediately after a change
    # -------------------------------------------------------------------------
    def check_alerts(view_id: str) -> None:
        vinfo = active_views[view_id]
        # Produce a quick snapshot in a dict form. Then test each predicate.
        snapshot_line = produce_snapshot(view_id)
        # We'll parse out the total_value from that final field; or re-run logic
        # in a simpler "calc" routine. For quickness, let's parse from the line:
        #   <view_id> <qtyString> <priceString> <total_value>
        # The total_value is the last token.
        tokens = snapshot_line.split()
        try:
            total_value = float(tokens[-1])
        except:
            total_value = 0.0

        # We'll also parse the <item:qty> to build a dictionary
        # (somewhat hacky but works for demonstration)
        item_qty_map: Dict[str, float] = {}
        if len(tokens) >= 2:
            qty_part = tokens[1]
            if qty_part:
                # Could be multiple "item:qty" separated by commas
                for seg in qty_part.split(","):
                    if seg.strip():
                        i, q = seg.split(":")
                        item_qty_map[i] = float(q)

        # Now run each alert
        for alert_info in vinfo["alerts"]:
            check_fn, message, last_state = alert_info
            # Evaluate current state
            now_state = check_fn(total_value, item_qty_map)
            if (not last_state) and now_state:
                # rising edge
                output_lines.append(f"ALERT {view_id} {message}")
            # Update lastFiredBoolean
            alert_info[2] = now_state

    # -------------------------------------------------------------------------
    # After applying any changes (immediately or at commit), we re‐emit to all
    # subscribed views. Except we do so only if not in an open transaction.
    # -------------------------------------------------------------------------
    def propagate_updates():
        if in_transaction:
            return
        # For each view, produce snapshot, append to output, then check alerts
        for vid in sorted(active_views.keys()):
            out_line = produce_snapshot(vid)
            output_lines.append(out_line)
            check_alerts(vid)

    # -------------------------------------------------------------------------
    # Dispatch logic for events
    # -------------------------------------------------------------------------
    def dispatch_event(ev: Event, is_replaying_tx: bool=False) -> None:
        nonlocal in_transaction, current_tick

        kind = ev.kind
        args = ev.args

        # ---------- Transaction control ----------
        if kind == "begin":
            if in_transaction:
                raise ValueError("Nested transaction not allowed.")
            in_transaction = True
            # transaction_buffer is already maintained
            return

        if kind == "commit":
            if not in_transaction:
                raise ValueError("commit with no open transaction")
            # Execute all buffered events "for real"
            tx_events = list(transaction_buffer)
            transaction_buffer.clear()
            in_transaction = False
            for tx_ev in tx_events:
                # re-run dispatch with is_replaying_tx=True
                dispatch_event(tx_ev, is_replaying_tx=True)
            # Now that everything is applied, produce a single consolidated update
            propagate_updates()
            return

        if kind == "rollback":
            if not in_transaction:
                raise ValueError("rollback with no open transaction")
            transaction_buffer.clear()
            in_transaction = False
            # No updates emitted
            return

        # If we are in a transaction and not replaying, buffer this event.
        if in_transaction and not is_replaying_tx:
            transaction_buffer.append(ev)
            return

        # ---------- Normal events ----------

        if kind == "stock":
            # stock <item_id> <delta>
            item_id = args[0]
            delta = float(args[1])
            ensure_exists(item_id)
            new_val = stock_cells[item_id].value + delta
            stock_cells[item_id].set(new_val)
            last_update_tick[item_id] = current_tick

        elif kind == "price":
            # price <item_id> <new_price>
            item_id = args[0]
            new_price = float(args[1])
            ensure_exists(item_id)
            price_cells[item_id].set(new_price)
            last_update_tick[item_id] = current_tick

        elif kind == "currency":
            # currency <item_id> <code>
            item_id = args[0]
            code = args[1].upper()
            ensure_exists(item_id)
            currency_of[item_id] = code
            last_update_tick[item_id] = current_tick

        elif kind == "rate":
            # rate <code> <to_USD_rate>
            code = args[0].upper()
            to_usd = float(args[1])
            exchange_rates[code] = to_usd
            # This doesn't directly mark items as updated, but in a real reactive
            # system we'd propagate to items in that currency.  For demonstration,
            # we'll just do a global re‐emit.
            # However, for window logic, note that effectively all items with that
            # currency have changed.  We'll set last_update_tick for them:
            for itm, ccy in currency_of.items():
                if ccy == code:
                    last_update_tick[itm] = current_tick

        elif kind == "bundle":
            # bundle <bundle_id> <member1> <member2> …
            bundle_id = args[0]
            members = args[1:]
            ensure_exists(bundle_id)
            # Clear existing membership:
            bundle_members[bundle_id] = set()
            # We'll also need to remove old parent links
            # from anything that was previously a child of this bundle
            # so we can rebuild them.
            for x, pset in parents_of.items():
                if bundle_id in pset:
                    pset.remove(bundle_id)

            # Build new membership
            for m in members:
                ensure_exists(m)
                bundle_members[bundle_id].add(m)
                # add parent link
                if m not in parents_of:
                    parents_of[m] = set()
                parents_of[m].add(bundle_id)

            last_update_tick[bundle_id] = current_tick
            # Also mark all nested items as updated.
            # We'll just do a gather and set last_update_tick for them:
            for leaf in gather_all_items(bundle_id):
                last_update_tick[leaf] = current_tick

        elif kind == "discount":
            # discount <target_id> <percent>
            # a 10 means 10% off => multiplier = 0.90
            target_id = args[0]
            pct = float(args[1])
            ensure_exists(target_id)
            # The spec: "Apply a percentage off (10 => 10%) to every direct or indirect member;
            # discounts multiply." We interpret that discountCells store a product factor
            # representing the discount.  If discount=10 => factor=0.90
            factor = 1.0 - (pct / 100.0)
            # We apply this to the target's discountCells, i.e. multiply them:
            current_d = discount_cells[target_id].value
            discount_cells[target_id].set(current_d * factor)

            last_update_tick[target_id] = current_tick
            # also recursively all children if target is a bundle
            for leaf in gather_all_items(target_id):
                last_update_tick[leaf] = current_tick

        elif kind == "subscribe":
            # subscribe <view_id> <target_id>
            view_id = args[0]
            target_id = args[1]
            # If the view_id is already active, we either re‐target it or raise error.
            # We'll assume re‐subscribe means just overwrite.
            active_views[view_id] = {
                "target": target_id,
                "window": -1,   # means "no window set" => unlimited
                "alerts": [],
            }
            # produce an immediate snapshot
            output_lines.append(produce_snapshot(view_id))
            check_alerts(view_id)

        elif kind == "unsubscribe":
            # unsubscribe <view_id>
            view_id = args[0]
            if view_id in active_views:
                del active_views[view_id]
            # no immediate output

        elif kind == "view":
            # view <view_id>
            view_id = args[0]
            # Force-emit the current snapshot
            if view_id in active_views:
                snap = produce_snapshot(view_id)
                output_lines.append(snap)
                check_alerts(view_id)
            # else ignore

        elif kind == "window":
            # window <view_id> <seconds>
            view_id = args[0]
            secs = int(args[1])
            if view_id in active_views:
                active_views[view_id]["window"] = secs
                # Changing the window is effectively an update. We can re‐emit:
                if not in_transaction:
                    snap = produce_snapshot(view_id)
                    output_lines.append(snap)
                    check_alerts(view_id)

        elif kind == "alert":
            # alert <view_id> <condition> <message>
            # e.g. alert myView "total_value>10000" "TooLarge"
            view_id = args[0]
            condition = args[1]
            message = args[2]

            # We support conditions of the form:
            #    total_value>10000
            # or qty(itemX)<5
            # We'll parse them quickly:
            def make_predicate(cond_str: str):
                # cond could be "total_value>10000" or "qty(itemX)<5"
                if cond_str.startswith("total_value"):
                    # e.g. total_value>10000
                    # We'll parse operator and number
                    import re
                    m = re.match(r"total_value([<>]=?)([\d\.]+)", cond_str)
                    if not m:
                        raise ValueError(f"Unknown condition syntax: {cond_str}")
                    op = m.group(1)
                    thresh = float(m.group(2))

                    def check_fn(total_val: float, item_qty: Dict[str, float]) -> bool:
                        if op == ">":
                            return total_val > thresh
                        elif op == "<":
                            return total_val < thresh
                        elif op == ">=":
                            return total_val >= thresh
                        elif op == "<=":
                            return total_val <= thresh
                        else:
                            return False

                    return check_fn

                elif cond_str.startswith("qty("):
                    # e.g. qty(itemX)<5
                    import re
                    m = re.match(r"qty\(([^)]+)\)([<>]=?)([\d\.]+)", cond_str)
                    if not m:
                        raise ValueError(f"Unknown condition syntax: {cond_str}")
                    item_name = m.group(1)
                    op = m.group(2)
                    thresh = float(m.group(3))

                    def check_fn(total_val: float, item_qty: Dict[str, float]) -> bool:
                        val = item_qty.get(item_name, 0.0)
                        if op == ">":
                            return val > thresh
                        elif op == "<":
                            return val < thresh
                        elif op == ">=":
                            return val >= thresh
                        elif op == "<=":
                            return val <= thresh
                        else:
                            return False

                    return check_fn
                else:
                    raise ValueError(f"Unsupported alert condition: {cond_str}")

            pred = make_predicate(condition)
            if view_id not in active_views:
                # If the user sets alert before subscribe, we can create a minimal record
                active_views[view_id] = {
                    "target": "",  # No real target yet
                    "window": -1,
                    "alerts": [],
                }
            active_views[view_id]["alerts"].append([pred, message, False])
            # Evaluate right away
            if not in_transaction:
                check_alerts(view_id)

        else:
            # Should never happen due to earlier validation
            raise ValueError(f"Unknown event kind: {kind}")

        # If we are not in transaction, we propagate updates immediately
        if not in_transaction:
            propagate_updates()

    # -------------------------------------------------------------------------
    # Main event loop
    # -------------------------------------------------------------------------
    for line in events:
        ev = parse_event(line)
        current_tick += 1
        dispatch_event(ev)

    return output_lines

