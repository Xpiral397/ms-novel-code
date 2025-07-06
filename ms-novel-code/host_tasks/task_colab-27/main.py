

import time

def find_nested_radical_pair(a: int, b: int, c: int) -> bool:

    def cube_root(n):
        if n == 0:
            return 0.0
        elif n > 0:
            return n ** (1/3)
        else:
            return -((-n) ** (1/3))

    if a == 0 and b == 0 and c == 0:
        return True

    target = cube_root(a) + cube_root(b) + cube_root(c)
    target_cubed = target ** 3

    def recursive_search(x_start, x_end, depth=0):
        if depth > 25:
            return False

        if x_end - x_start <= 200:
            for x in range(x_start, x_end + 1):
                try:
                    y = (target_cubed - cube_root(x)) ** 3
                    for y_int in [int(y), round(y)]:
                        if -1000 <= y_int <= 20000:
                            result = cube_root(cube_root(x) + cube_root(y_int))
                            if abs(result - target) < 1e-9:
                                return True
                except:
                    continue
            return False

        mid = (x_start + x_end) // 2
        return (recursive_search(x_start, mid, depth + 1) or
                recursive_search(mid + 1, x_end, depth + 1))

    return recursive_search(-1000, 20000)


if __name__ == "__main__":
    test_cases = [
        (0, 0, 0, True),
        (0, 0, 1, True),
        (1, 1, 1, True),
        (2, 2, 2, True),
        (10, 20, 30, False),
        (1000, 1000, 1000, False),
        (-100, -100, -100, False),
        (50, -50, 0, True),
    ]

    for a, b, c, expected in test_cases:
        actual = find_nested_radical_pair(a, b, c)
        print(f"a={a}, b={b}, c={c} - Expected: {expected}, Actual: {actual}")
