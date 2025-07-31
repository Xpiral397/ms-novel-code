"""Calculate the expected number of dishes in the chef competition."""
import itertools

# Global memoization dictionary to store results of subproblems.
memo = {}

# Global dictionary to store skill values S(k) for each chef.
S_values = {}

# Global list to store Fibonacci numbers.
fib_sequence_global = []


def get_fib_sequence(n_max: int) -> list[int]:
    """
    Calculate Fibonacci numbers up to F(n_max + 1) inclusive.

    Base cases:
        F1 = 1, F2 = 1

    Args:
        n_max: The maximum index for which Fibonacci numbers are needed.

    Returns:
        A list where fib[k] corresponds to F_k.
    """
    fib = [0] * (n_max + 2)
    if n_max >= 1:
        fib[1] = 1
    if n_max >= 2:
        fib[2] = 1
    for i in range(3, n_max + 2):
        fib[i] = fib[i - 1] + fib[i - 2]
    return fib


def product(iterable):
    """
    Calculate the product of all elements in an iterable.

    Args:
        iterable: An iterable of numeric values.

    Returns:
        The product as a float.
    """
    res = 1.0
    for x in iterable:
        res *= x
    return res


def expected_dishes(n: int) -> str:
    """
    Calculate the expected number of dishes in the chef competition.

    Args:
        n: The number of chefs at the start (1 <= n <= 14).

    Returns:
        The expected number of dishes as a string, rounded to 8 decimals.
    """
    global memo, S_values, fib_sequence_global

    if n <= 0:
        raise ValueError("n must be a positive integer (n >= 1)")

    if n == 1:
        return f"{1.0:.8f}"

    memo = {}
    fib_sequence_global = get_fib_sequence(n + 1)
    S_values = {
        k: fib_sequence_global[k] / fib_sequence_global[n + 1]
        for k in range(1, n + 1)
    }

    for chef_id in range(1, n + 1):
        win_probs_base = {c_id: 0.0 for c_id in range(1, n + 1)}
        win_probs_base[chef_id] = 1.0
        memo[((chef_id,), 0)] = (win_probs_base, 0.0)

    for num_chefs in range(2, n + 1):
        for chefs in itertools.combinations(range(1, n + 1), num_chefs):
            chefs = tuple(sorted(chefs))

            p_coeff = [0.0] * num_chefs
            q_terms = [0.0] * num_chefs
            r_terms = {c_id: [0.0] * num_chefs for c_id in range(1, n + 1)}

            for k in range(num_chefs):
                chef_id = chefs[k]
                skill = S_values[chef_id]
                p_coeff[k] = 1 - skill

                best_win = -1.0
                optimal_choices = []

                for i in range(num_chefs):
                    elim_id = chefs[i]
                    if elim_id == chef_id:
                        continue
                    next_chefs = [c for c in chefs if c != elim_id]
                    next_tuple = tuple(sorted(next_chefs))
                    idx = next_chefs.index(chef_id)
                    next_turn = (idx + 1) % len(next_chefs)

                    temp_probs, _ = memo[(next_tuple, next_turn)]
                    win_prob = temp_probs[chef_id]

                    if win_prob > best_win:
                        best_win = win_prob
                        optimal_choices = [(elim_id, next_tuple, next_turn)]
                    elif win_prob == best_win:
                        optimal_choices.append(
                            (elim_id, next_tuple, next_turn))

                chosen = None
                for d in range(1, num_chefs):
                    idx = (k + d) % num_chefs
                    target_id = chefs[idx]
                    for eid, tup, tix in optimal_choices:
                        if eid == target_id:
                            chosen = (eid, tup, tix)
                            break
                    if chosen:
                        break
                if not chosen and optimal_choices:
                    chosen = optimal_choices[0]
                elif not optimal_choices and num_chefs > 1:
                    raise ValueError("No valid elimination found")

                _, fav_chefs, fav_idx = chosen
                fav_probs, fav_expect = memo[(fav_chefs, fav_idx)]

                q_terms[k] = 1 + skill * fav_expect
                for cid in range(1, n + 1):
                    r_terms[cid][k] = skill * fav_probs.get(cid, 0.0)

            prod_p = 1.0
            for val in p_coeff:
                prod_p *= val

            denom = 1.0 - prod_p
            if abs(denom) < 1e-12:
                raise ValueError("Denominator too small")

            e_vals = [0.0] * num_chefs
            w_vals = {cid: [0.0] * num_chefs for cid in range(1, n + 1)}

            sum_q = sum(
                q_terms[j] * product(p_coeff[m] for m in range(j))
                for j in range(num_chefs)
            )
            e_vals[0] = sum_q / denom

            for cid in range(1, n + 1):
                sum_r = sum(
                    r_terms[cid][j] * product(p_coeff[m] for m in range(j))
                    for j in range(num_chefs)
                )
                w_vals[cid][0] = sum_r / denom

            for k in range(num_chefs - 1, 0, -1):
                nxt = (k + 1) % num_chefs
                e_vals[k] = q_terms[k] + p_coeff[k] * e_vals[nxt]
                for cid in range(1, n + 1):
                    w_vals[cid][k] = (
                        r_terms[cid][k] + p_coeff[k] * w_vals[cid][nxt]
                    )

            for k in range(num_chefs):
                win_probs = {cid: w_vals[cid][k] for cid in range(1, n + 1)}
                memo[(chefs, k)] = (win_probs, e_vals[k])

    full_chefs = tuple(range(1, n + 1))
    _, result = memo[(full_chefs, 0)]
    return f"{result:.8f}"


if __name__ == "__main__":
    for i in range(1, 15):
        res = expected_dishes(i)
        print(res, type(res))

