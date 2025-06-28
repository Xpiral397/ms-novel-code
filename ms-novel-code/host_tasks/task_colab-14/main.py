"""Module to compute the distance for tangent circle radius triples."""

import math
from typing import List, Tuple


def compute_expected_d(radius_triples: List[Tuple[int, int, int]]) -> float:
    """
    Compute the distance for tangent circle radius triples.

    Args:
        radius_triples: A list of integer triples (ra, rb, rc), where each
            triple represents the radii of three mutually and externally
            tangent circles with ra < rb < rc.

    Returns:
        The expected value of d = |DE|, the Euclidean distance between D and E,
        averaged over all input triples and rounded to 8 decimal places.
        Returns 0.0 for an empty input list.
    """
    if not radius_triples:
        return 0.0

    total_d = 0.0
    num_triples = len(radius_triples)

    for triple in radius_triples:
        ra, rb, rc = float(triple[0]), float(triple[1]), float(triple[2])

        if not (1 <= ra < rb < rc <= 1000):
            raise ValueError(
                "Each triple must satisfy 1 <= ra < rb < rc <= 1000"
            )

        # Step 1: Compute (x,y) of Cc by intersecting two distance constraints
        xc_num = ra**2 + ra * rc + ra * rb - rb * rc
        xc_den = ra + rb
        x_c = xc_num / xc_den

        yc_squared = (ra + rc)**2 - x_c**2
        y_c = math.sqrt(max(0.0, yc_squared))

        # Step 2: Compute tangency points
        tab = (ra, 0.0)

        tac_x = (ra * x_c) / (ra + rc)
        tac_y = (ra * y_c) / (ra + rc)
        tac = (tac_x, tac_y)

        tbc_x = (ra + rb) + (rb / (rb + rc)) * (x_c - (ra + rb))
        tbc_y = (rb / (rb + rc)) * y_c
        tbc = (tbc_x, tbc_y)

        # Step 3: Compute circumcenter D
        ax, ay = tab
        bx, by = tac
        cx, cy = tbc

        denom_d = 2 * (
            ax * (by - cy) + bx * (cy - ay) + cx * (ay - by)
        )

        dx_num = (
            (ax**2 + ay**2) * (by - cy)
            + (bx**2 + by**2) * (cy - ay)
            + (cx**2 + cy**2) * (ay - by)
        )

        dy_num = (
            (ax**2 + ay**2) * (cx - bx)
            + (bx**2 + by**2) * (ax - cx)
            + (cx**2 + cy**2) * (bx - ax)
        )

        dx = dx_num / denom_d
        dy = dy_num / denom_d

        # Step 4: Compute Soddy circle center E
        k_a, k_b, k_c = 1 / ra, 1 / rb, 1 / rc

        sqrt_term = math.sqrt(k_a * k_b + k_b * k_c + k_c * k_a)
        k_g = k_a + k_b + k_c + 2 * sqrt_term
        r_g = 1 / k_g

        ex_num = ra * (ra + rb) - r_g * (rb - ra)
        ex_den = ra + rb
        e_x = ex_num / ex_den

        ey_num = -e_x * x_c + ra * (ra + rc) - r_g * (rc - ra)
        e_y = ey_num / y_c

        # Step 5: Compute Euclidean distance |DE|
        dx_e = dx - e_x
        dy_e = dy - e_y
        d = math.sqrt(dx_e**2 + dy_e**2)

        total_d += d

    expected_d = total_d / num_triples
    return round(expected_d, 8)


# --- Example Usage ---

radius_triples_1 = [(1, 2, 3)]
result_1 = compute_expected_d(radius_triples_1)
print(f"Input: {radius_triples_1}")
print(f"Output: {result_1:.8f}\n")  # Expected: 0.15676310

radius_triples_2 = [(2, 3, 4), (3, 4, 5)]
result_2 = compute_expected_d(radius_triples_2)
print(f"Input: {radius_triples_2}")
print(f"Output: {result_2:.8f}\n")

radius_triples_empty = []
result_empty = compute_expected_d(radius_triples_empty)
print(f"Input: {radius_triples_empty}")
print(f"Output: {result_empty:.8f}\n")

radius_triples_large = [(98, 99, 100)]
result_large = compute_expected_d(radius_triples_large)
print(f"Input: {radius_triples_large}")
print(f"Output: {result_large:.8f}\n")

