
import pulp
from typing import List, Tuple


def optimal_rideshare_assignment(
    num_drivers: int,
    num_passengers: int,
    cost_matrix: List[List[int]],
    max_assignments_per_driver: int,
    max_assignments_per_passenger: int,
    allow_multiple_assignments: bool
) -> List[Tuple[int, int]]:
    """Solve optimal rideshare assignment using Integer Linear Programming."""

    # Input validation, return empty list for invalid inputs
    if (num_drivers <= 0 or num_passengers <= 0 or
        max_assignments_per_driver < 1 or max_assignments_per_passenger < 1):
        return []

    # Validate cost matrix dimensions and type
    if (not cost_matrix or len(cost_matrix) != num_drivers):
        return []

    for i, row in enumerate(cost_matrix):
        if (not row or len(row) != num_passengers):
            return []
        for cost in row:
            if not isinstance(cost, int):
                return []

    # Step 1: Find maximum number of assignments possible
    prob1 = pulp.LpProblem("MaxAssignments", pulp.LpMaximize)

    # Binary decision variables
    x = {}
    for i in range(num_drivers):
        for j in range(num_passengers):
            x[i, j] = pulp.LpVariable(f"x_{i}_{j}", cat='Binary')

    # maximize total assignments
    prob1 += pulp.lpSum(x[i, j] for i in range(num_drivers) for j in range(num_passengers))

    # Driver assignment constraints
    for i in range(num_drivers):
        prob1 += pulp.lpSum(x[i, j] for j in range(num_passengers)) <= max_assignments_per_driver

    # Passenger assignment constraints based on allow_multiple_assignments flag
    for j in range(num_passengers):
        if allow_multiple_assignments:
            prob1 += pulp.lpSum(x[i, j] for i in range(num_drivers)) <= max_assignments_per_passenger
        else:

            prob1 += pulp.lpSum(x[i, j] for i in range(num_drivers)) <= 1

    # Solve for maximum assignments
    try:
        prob1.solve(pulp.PULP_CBC_CMD(msg=0))
    except:
        return []

    if prob1.status != pulp.LpStatusOptimal:
        return []

    # Get maximum number of assignments
    max_assignments = int(prob1.objective.value())

    if max_assignments == 0:
        return []

    # Step 2: Among all solutions with maximum assignments, find minimum cost
    prob2 = pulp.LpProblem("MinCostWithMaxAssignments", pulp.LpMinimize)

    # Same binary decision variables
    y = {}
    for i in range(num_drivers):
        for j in range(num_passengers):
            y[i, j] = pulp.LpVariable(f"y_{i}_{j}", cat='Binary')

    # Objective: minimize total cost
    prob2 += pulp.lpSum(cost_matrix[i][j] * y[i, j]
                       for i in range(num_drivers)
                       for j in range(num_passengers))

    # Constraint: must achieve maximum assignments
    prob2 += pulp.lpSum(y[i, j] for i in range(num_drivers) for j in range(num_passengers)) == max_assignments

    # Driver assignment constraints
    for i in range(num_drivers):
        prob2 += pulp.lpSum(y[i, j] for j in range(num_passengers)) <= max_assignments_per_driver

    # Passenger assignment constraints
    for j in range(num_passengers):
        if allow_multiple_assignments:
            prob2 += pulp.lpSum(y[i, j] for i in range(num_drivers)) <= max_assignments_per_passenger
        else:
            prob2 += pulp.lpSum(y[i, j] for i in range(num_drivers)) <= 1

    # Solve for minimum cost with maximum assignments
    try:
        prob2.solve(pulp.PULP_CBC_CMD(msg=0))
    except:
        return []

    if prob2.status != pulp.LpStatusOptimal:
        return []

    # Extract assignments from solution
    assignments = []
    for i in range(num_drivers):
        for j in range(num_passengers):
            if y[i, j].varValue and abs(y[i, j].varValue - 1) < 1e-9:
                assignments.append((i, j))

    # Sort by driver_id first, then passenger_id as required
    assignments.sort()

    return assignments
