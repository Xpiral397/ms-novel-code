
from typing import List, Dict, Any, Optional
import random

__all__ = ["bootstrap", "query"]

_store: Optional[Dict[str, List[Dict[str, Any]]]] = None


def bootstrap(tenants: List[str], rng_seed: Optional[int] = None) -> None:
    """
    Initialize (or reinitialize) the multi-tenant data store.

    Generates exactly 50 mock records per tenant, each record containing:
      - tenant_id: str
      - obj_id:   str (32-character hexadecimal)
      - value:    int (0–999)

    Args:
        tenants:  List of unique tenant identifiers.
        rng_seed: Optional seed for reproducible randomness.

    Raises:
        ValueError: If `tenants` contains duplicates.
    """
    global _store

    # Detect duplicate tenant IDs
    if len(tenants) != len(set(tenants)):
        raise ValueError("Duplicate tenant IDs are not allowed")

    # Build a fresh store with a private RNG
    rng = random.Random(rng_seed)
    new_store: Dict[str, List[Dict[str, Any]]] = {}

    for tenant_id in tenants:
        new_store[tenant_id] = _generate_records(tenant_id, rng)

    _store = new_store


def query(
    user_ctx: Dict[str, Any],
    *,
    value_min: Optional[int] = None,
    value_max: Optional[int] = None
) -> List[Dict[str, Any]]:
    """
    Retrieve records for the tenant specified in user_ctx["tenant_id"],
    optionally filtered by a numeric range on the `value` field.

    Args:
        user_ctx:   Dict containing at least the key "tenant_id".
        value_min:  Inclusive lower bound on record["value"], if provided.
        value_max:  Inclusive upper bound on record["value"], if provided.

    Returns:
        List of record dicts matching the tenant and value filters.

    Raises:
        RuntimeError: If bootstrap() has not yet been called.
        KeyError:     If "tenant_id" is missing or not recognized.
        ValueError:   If value_min > value_max.
    """
    global _store

    # Must initialize first
    if _store is None:
        raise RuntimeError("bootstrap() must be called before query()")

    # Validate and extract tenant_id
    if "tenant_id" not in user_ctx:
        raise KeyError("tenant_id")
    tenant_id = user_ctx["tenant_id"]
    if tenant_id not in _store:
        raise KeyError(tenant_id)

    # Validate range parameters
    if value_min is not None and value_max is not None and value_min > value_max:
        raise ValueError("value_min cannot be greater than value_max")

    # Filter and return shallow copies
    results: List[Dict[str, Any]] = []
    for record in _store[tenant_id]:
        val = record["value"]
        if value_min is not None and val < value_min:
            continue
        if value_max is not None and val > value_max:
            continue
        results.append(record.copy())

    return results


def _generate_records(
    tenant_id: str,
    rng: random.Random
) -> List[Dict[str, Any]]:
    """
    Helper to generate 50 mock records for a single tenant.

    Args:
        tenant_id: The tenant identifier to embed in each record.
        rng:       A private Random instance for reproducibility.

    Returns:
        A list of 50 record dicts.
    """
    records: List[Dict[str, Any]] = []
    for _ in range(50):
        obj_id = "".join(rng.choice("0123456789abcdef") for _ in range(32))
        value = rng.randint(0, 999)
        records.append({
            "tenant_id": tenant_id,
            "obj_id":     obj_id,
            "value":      value
        })
    return records

