
def min_sprinklers_to_activate(m, n, ranges):
    sprinklers = []
    i = 0
    while i < m:
        j = 0
        while j < n:
            r = ranges[i][j]
            if r > 0:
                covered = set()
                dx = -r
                while dx <= r:
                    dy_range = r - abs(dx)
                    dy = -dy_range
                    while dy <= dy_range:
                        x, y = i + dx, j + dy
                        if 0 <= x < m and 0 <= y < n:
                            covered.add((x, y))
                        dy += 1
                    dx += 1
                sprinklers.append(((i, j), covered))
            j += 1
        i += 1

    total_cells = set()
    i = 0
    while i < m:
        j = 0
        while j < n:
            total_cells.add((i, j))
            j += 1
        i += 1
    covered_cells = set()
    used = set()
    result = 0

    while covered_cells != total_cells:
        best_choice = None
        max_new = 0

        idx = 0
        while idx < len(sprinklers):
            if idx in used:
                idx += 1
                continue
            pos, area = sprinklers[idx]
            new_coverage = len(area - covered_cells)
            if new_coverage > max_new:
                max_new = new_coverage
                best_choice = idx
            idx += 1


        if best_choice is None:
            return -1

        used.add(best_choice)
        covered_cells.update(sprinklers[best_choice][1])
        result += 1

    return result


# Sample test cases
print(min_sprinklers_to_activate(3, 4, [[0, 2, 0, 0], [0, 0, 0, 3], [0, 0, 0, 0]]))  # Output: -1
print(min_sprinklers_to_activate(3, 3, [[2, 0, 2], [0, 0, 0], [2, 0, 2]]))  # Output: 2
