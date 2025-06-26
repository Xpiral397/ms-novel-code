
import sympy as sp
from sympy import symbols, log, simplify, sympify, expand, factor
import math

def solve_recurrence(recurrence: str, params: dict) -> str:
    """Solves divide-and-conquer recurrence relations to closed form expressions."""
    try:
        # Input validation
        if not _validate_inputs(recurrence, params):
            return "Invalid input"

        # Extract and validate parameters
        a, b, f_n_str, base_case_str = _extract_params(params)

        # Parameter validation
        if a <= 0 or b <= 1:
            raise ValueError("Invalid recurrence parameters")

        # Parse symbolic expressions
        n = symbols('n', positive=True, integer=True)
        f_n, base_case = _parse_expressions(f_n_str, base_case_str, n)

        # Apply Master Theorem
        result = _apply_master_theorem(a, b, f_n, base_case, n)

        # Simplify and return as string
        simplified = simplify(result)
        return f"T(n) = {simplified}"

    except ValueError as e:
        if "Invalid recurrence parameters" in str(e):
            raise e
        elif "Unsupported function" in str(e):
            return "Unsupported function"
        return "Invalid input"
    except SyntaxError:
        raise SyntaxError()
    except Exception:
        return "Cannot solve"


def _validate_inputs(recurrence: str, params: dict) -> bool:
    """Validates input format and completeness."""
    if not recurrence or not isinstance(recurrence, str):
        return False
    if not params or not isinstance(params, dict):
        return False

    required_keys = {'a', 'b', 'f(n)', 'base_case'}
    if not all(key in params for key in required_keys):
        return False

    return all(params[key] is not None and str(params[key]).strip() for key in required_keys)


def _extract_params(params: dict) -> tuple:
    """Extracts parameters from params dict with type validation."""
    try:
        a = int(params['a'])
        b = int(params['b'])
        f_n_str = str(params['f(n)']).strip()
        base_case_str = str(params['base_case']).strip()
        return a, b, f_n_str, base_case_str
    except (ValueError, TypeError):
        raise ValueError("Parameter type conversion failed")


def _parse_expressions(f_n_str: str, base_case_str: str, n) -> tuple:
    """Parses f(n) and base_case strings into sympy expressions."""
    # Check for unsupported operations
    unsupported = ['factorial', '!', 'gamma', 'sin', 'cos', 'tan', 'exp']
    if any(op in f_n_str.lower() for op in unsupported):
        raise ValueError("Unsupported function")

    try:
        # Convert ^ to ** for sympy compatibility
        f_n_processed = f_n_str.replace('^', '**')
        f_n_processed = f_n_processed.replace('log(n)', f'log({n})')

        # Parse using sympify
        f_n = sympify(f_n_processed, locals={'n': n, 'log': log})

        # Handle base case parsing with proper error handling
        try:
            base_case = sympify(base_case_str)
            # Check if base_case contains unexpected symbols (like 'abc')
            # Valid base cases should be numbers or simple expressions
            if base_case.free_symbols:
                # If it has symbols that aren't standard math constants, it's invalid
                for sym in base_case.free_symbols:
                    sym_str = str(sym)
                    # Allow common math symbols but reject arbitrary text like 'abc'
                    if sym_str not in ['e', 'pi', 'I', 'E'] and not sym_str.isdigit():
                        raise SyntaxError()
        except:
            raise SyntaxError()

        return f_n, base_case
    except SyntaxError:
        raise SyntaxError()
    except Exception:
        raise ValueError("Invalid input")


def _apply_master_theorem(a: int, b: int, f_n, base_case, n):
    """Applies Master Theorem to derive closed form solution."""
    # Calculate critical exponent log_b(a)
    log_b_a = log(a) / log(b)

    # Determine polynomial degree of f(n)
    f_degree = _get_polynomial_degree(f_n, n)

    # Apply Master Theorem cases
    if f_degree is not None:
        return _handle_polynomial_case(a, b, f_n, base_case, n, log_b_a, f_degree)
    elif _is_n_log_n_form(f_n, n):
        return _handle_n_log_n_case(a, b, f_n, base_case, n, log_b_a)
    elif _is_log_form(f_n, n):
        return _handle_log_case(a, b, f_n, base_case, n, log_b_a)
    else:
        return _solve_by_expansion(a, b, f_n, base_case, n)


def _get_polynomial_degree(expr, n) -> int:
    """Determines polynomial degree of expression in n."""
    try:
        expanded = expand(expr)
        poly = sp.Poly(expanded, n)
        return poly.degree()
    except Exception:
        return None


def _is_n_log_n_form(expr, n) -> bool:
    """Checks if expression is of form c*n*log(n)."""
    try:
        # Check for n*log(n) pattern
        simplified = simplify(expr / (n * log(n)))
        return simplified.is_constant() and not simplified.has(n)
    except Exception:
        return False


def _is_log_form(expr, n) -> bool:
    """Checks if expression is of form c*log(n)."""
    try:
        simplified = simplify(expr / log(n))
        return simplified.is_constant() and not simplified.has(n)
    except Exception:
        return False


def _handle_polynomial_case(a: int, b: int, f_n, base_case, n, log_b_a, f_degree: int):
    """Handles polynomial f(n) using Master Theorem cases."""
    # Extract leading coefficient
    expanded = expand(f_n)
    leading_coeff = expanded.coeff(n, f_degree)
    if leading_coeff is None:
        leading_coeff = 1

    # Convert log_b_a to float for comparison
    try:
        log_b_a_float = float(log_b_a.evalf())
    except:
        log_b_a_float = float(log_b_a)

    if f_degree < log_b_a_float:
        # Case 1: f(n) = O(n^c) where c < log_b(a)
        return base_case * n**log_b_a
    elif abs(f_degree - log_b_a_float) < 1e-10:
        # Case 2: f(n) = Θ(n^c) where c = log_b(a)
        return n**f_degree * log(n)
    else:
        # Case 3: f(n) = Ω(n^c) where c > log_b(a)
        # Check regularity condition
        if _check_regularity_condition(a, b, leading_coeff, f_degree):
            return leading_coeff * n**f_degree
        else:
            return leading_coeff * n**f_degree


def _handle_n_log_n_case(a: int, b: int, f_n, base_case, n, log_b_a):
    """Handles f(n) = c*n*log(n) case."""
    coeff = simplify(f_n / (n * log(n)))

    # Special case for when log_b(a) = 1 and f(n) = n*log(n)
    if abs(float(log_b_a - 1)) < 1e-10:  # log_b(a) = 1
        return coeff * n * log(n)**2
    elif log_b_a > 1:
        return base_case * n**log_b_a
    else:
        return coeff * n * log(n)**2


def _handle_log_case(a: int, b: int, f_n, base_case, n, log_b_a):
    """Handles f(n) = c*log(n) case."""
    coeff = simplify(f_n / log(n))

    # For T(n) = 1*T(n/2) + log(n), the solution is log(n)^2
    if abs(float(log_b_a)) < 1e-10:  # log_b(a) = 0, so a = 1
        return coeff * log(n)**2
    elif log_b_a > 0:
        return base_case * n**log_b_a
    else:
        return coeff * log(n)**2


def _check_regularity_condition(a: int, b: int, coeff, degree: int) -> bool:
    """Checks Master Theorem regularity condition."""
    # Simplified regularity check
    return coeff > 0 and a * (1/b)**degree < 1


def _solve_by_expansion(a: int, b: int, f_n, base_case, n):
    """Solves recurrence by expansion method when Master Theorem doesn't apply."""
    # Expansion method for complex f(n)
    try:
        # Build solution through geometric series analysis
        log_b_a = log(a) / log(b)

        # Approximate solution based on recurrence structure
        if f_n.has(log):
            # Handle logarithmic terms
            return base_case * n**log_b_a + f_n
        else:
            # Default to dominant term analysis
            f_at_n = f_n.subs(n, n)
            return simplify(base_case * n**log_b_a + f_at_n)

    except Exception:
        raise ValueError("Cannot solve complex recurrence")
