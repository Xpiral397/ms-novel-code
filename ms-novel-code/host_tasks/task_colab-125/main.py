
import ast


def analyze_control_flow(source_lines):
    """
    Analyze Python source code and return control flow metrics.

    Args:
        source_lines: List of strings representing Python source code

    Returns:
        tuple: (blocks_count, decision_points, max_depth, unreachable_blocks,
                loop_status)
    """
    # Parse the source code into an Abstract Syntax Tree (AST)
    # Handle potential syntax errors gracefully
    try:
        tree = ast.parse("\n".join(source_lines))
    except SyntaxError:
        # If the code cannot be parsed, return safe defaults
        return (0, 0, 0, "NONE", "FINITE")

    # Initialize global counters and tracking variables
    block_counter = 0  # Counter for assigning unique block IDs
    decision_points = 0  # Counter for branching constructs
    max_depth = 0  # Maximum nesting depth encountered
    unreachable_blocks = set()  # Set of unreachable block IDs
    loop_status = "FINITE"  # Status of loops (FINITE or INFINITE)

    def new_block_id():
        """Generate a new unique block ID and increment counter."""
        nonlocal block_counter
        bid = block_counter
        block_counter += 1
        return bid

    def body_forcibly_ends(body):
        """
        Check if a body of statements forcibly ends execution in all paths.

        Returns True if the body definitely ends (return or raise) for all
        possible execution paths.

        Args:
            body: List of AST statements

        Returns:
            bool: True if all paths end forcibly, False otherwise
        """
        # Empty body doesn't forcibly end
        if not body:
            return False

        # Check for single return/raise statement
        if len(body) == 1 and isinstance(body[0], (ast.Return, ast.Raise)):
            return True

        # Check if first statement is an if-elif-else chain that covers all paths
        if isinstance(body[0], ast.If):
            if_node = body[0]

            # Collect all branches in the if-elif-else chain
            branches = []

            def collect_if_branches(node):
                """Recursively collect all if-elif-else branches."""
                # Add the if/elif body
                branches.append(node.body)

                # Check if there's an elif (represented as nested If in orelse)
                if len(node.orelse) == 1 and isinstance(node.orelse[0], ast.If):
                    # This is an elif - recurse
                    collect_if_branches(node.orelse[0])
                else:
                    # This is the final else clause
                    if node.orelse:
                        branches.append(node.orelse)

            collect_if_branches(if_node)

            # Need at least 2 branches to have complete coverage (if + else)
            if len(branches) < 2:
                return False

            # Check if each branch forcibly ends
            for branch in branches:
                if not body_forcibly_ends(branch):
                    return False

            # If there are statements after the if-elif-else, execution can't
            # reach them, so they would be unreachable
            if len(body) > 1:
                return False

            return True

        return False

    def count_elif_else(if_node):
        """
        Count decision points in an if-elif-else chain.

        Returns the total number of decision points:
        - 1 for the initial if
        - 1 for each elif
        - 1 for the else (if present)

        Args:
            if_node: AST If node

        Returns:
            int: Number of decision points
        """
        # Start with 1 for the initial if statement
        count = 1

        def traverse_orelse(node):
            """Recursively traverse elif/else chain."""
            nonlocal count

            # Check if orelse contains an elif (represented as nested If)
            if len(node.orelse) == 1 and isinstance(node.orelse[0], ast.If):
                # This is an elif - add 1 and recurse
                count += 1
                traverse_orelse(node.orelse[0])
            else:
                # This is a final else clause - add 1 if present
                if node.orelse:
                    count += 1

        traverse_orelse(if_node)
        return count

    def is_while_infinite(while_node):
        """
        Detect potential infinite loops using naive pattern matching.

        Looks for patterns like:
            while True:
            while x > 0:
                x += 1

        Args:
            while_node: AST While node

        Returns:
            bool: True if potentially infinite loop detected
        """
        # Check for while True pattern
        if isinstance(while_node.test, ast.Constant) and while_node.test.value is True:
            return True

        # Check for while True pattern (older Python versions use ast.NameConstant)
        if hasattr(ast, 'NameConstant') and isinstance(while_node.test, ast.NameConstant) and while_node.test.value is True:
            return True

        # Check if the loop condition is a comparison
        if isinstance(while_node.test, ast.Compare):
            comp = while_node.test

            # Look for pattern: variable > constant
            if (isinstance(comp.left, ast.Name) and
                len(comp.ops) == 1 and
                len(comp.comparators) == 1 and
                isinstance(comp.comparators[0], ast.Constant)):

                var_name = comp.left.id  # Variable being compared
                op = comp.ops[0]  # Comparison operator
                cval = comp.comparators[0].value  # Constant value

                # Check for greater than comparison with numeric constant
                if (isinstance(op, (ast.Gt, ast.GtE)) and
                    isinstance(cval, (int, float))):

                    # Search loop body for increments of the same variable
                    for stmt in while_node.body:
                        # Check for augmented assignment (var += value)
                        if isinstance(stmt, ast.AugAssign):
                            if (isinstance(stmt.target, ast.Name) and
                                stmt.target.id == var_name and
                                isinstance(stmt.op, ast.Add)):

                                # Check if increment is positive constant
                                if (isinstance(stmt.value, ast.Constant) and
                                    isinstance(stmt.value.value, (int, float)) and
                                    stmt.value.value > 0):
                                    return True

                        # Check for regular assignment (var = var + value)
                        elif isinstance(stmt, ast.Assign):
                            if (len(stmt.targets) == 1 and
                                isinstance(stmt.targets[0], ast.Name) and
                                stmt.targets[0].id == var_name):

                                # Check if RHS is var + positive_constant
                                if isinstance(stmt.value, ast.BinOp):
                                    binop = stmt.value
                                    if (isinstance(binop.op, ast.Add) and
                                        isinstance(binop.left, ast.Name) and
                                        binop.left.id == var_name and
                                        isinstance(binop.right, ast.Constant) and
                                        isinstance(binop.right.value, (int, float)) and
                                        binop.right.value > 0):
                                        return True
        return False

    def visit_statements(stmts, depth=1, in_unreachable=False):
        """
        Recursively traverse and analyze a list of statements.

        Args:
            stmts: List of AST statements to analyze
            depth: Current nesting depth
            in_unreachable: Whether we're in unreachable code

        Returns:
            bool: True if this block forcibly ends execution
        """
        nonlocal max_depth, decision_points, loop_status

        forced_end_here = False
        i = 0

        # Process each statement in the list
        while i < len(stmts):
            node = stmts[i]

            # Create a new block for this statement
            current_block = new_block_id()

            # Mark as unreachable if we're in unreachable code
            if in_unreachable:
                unreachable_blocks.add(current_block)

            # Update maximum depth tracking
            if depth > max_depth:
                max_depth = depth

            # Handle different types of statements
            if isinstance(node, ast.Return) or isinstance(node, ast.Raise):
                # This block forcibly ends execution
                forced_end_here = True

                # Mark all subsequent statements as unreachable
                i += 1
                while i < len(stmts):
                    unreachable_block = new_block_id()
                    unreachable_blocks.add(unreachable_block)
                    i += 1
                break

            elif isinstance(node, ast.If):
                # Count decision points for if-elif-else chain
                decision_point_count = count_elif_else(node)
                decision_points += decision_point_count

                # Collect forced-end status for each branch
                def collect_if_forced_end(n, d):
                    """Collect forced-end status for all branches."""
                    results = []

                    # Analyze if branch
                    if_end = visit_statements(n.body, d + 1,
                                            in_unreachable=False)
                    results.append(if_end)

                    # Handle elif/else chain
                    if (len(n.orelse) == 1 and
                        isinstance(n.orelse[0], ast.If)):
                        # This is an elif - recurse
                        results.extend(collect_if_forced_end(n.orelse[0], d))
                    else:
                        # This is a final else clause
                        if n.orelse:
                            else_end = visit_statements(n.orelse, d + 1,
                                                      in_unreachable=False)
                            results.append(else_end)

                    return results

                # Get forced-end status for all branches
                forced_branch_results = collect_if_forced_end(node, depth)

                # Check if there's a final else clause
                def has_final_else(n):
                    """Check if if-elif chain has a final else."""
                    if not n.orelse:
                        return False
                    if (len(n.orelse) == 1 and
                        isinstance(n.orelse[0], ast.If)):
                        return has_final_else(n.orelse[0])
                    return True

                has_else = has_final_else(node)

                # If all branches forcibly end and there's an else,
                # code after this if-elif-else is unreachable
                if has_else and all(forced_branch_results):
                    forced_end_here = True

                    # Mark subsequent statements as unreachable
                    i += 1
                    while i < len(stmts):
                        unreachable_block = new_block_id()
                        unreachable_blocks.add(unreachable_block)
                        i += 1
                    break

            elif isinstance(node, ast.For):
                # For loop is a decision point
                decision_points += 1

                # Analyze loop body
                visit_statements(node.body, depth + 1, in_unreachable=False)

                # Analyze else clause (executes if loop completes normally)
                visit_statements(node.orelse, depth + 1, in_unreachable=False)

            elif isinstance(node, ast.While):
                # While loop is a decision point
                decision_points += 1

                # Check for potential infinite loop
                if loop_status == "FINITE" and is_while_infinite(node):
                    loop_status = "INFINITE"

                # Analyze loop body
                visit_statements(node.body, depth + 1, in_unreachable=False)

                # Analyze else clause (executes if loop completes normally)
                visit_statements(node.orelse, depth + 1, in_unreachable=False)

            elif isinstance(node, ast.Try):
                # Try block is a decision point
                decision_points += 1

                # Each except handler is also a decision point
                for handler in node.handlers:
                    decision_points += 1

                # Analyze try body
                visit_statements(node.body, depth + 1, in_unreachable=False)

                # Analyze exception handlers
                for handler in node.handlers:
                    visit_statements(handler.body, depth + 1,
                                   in_unreachable=False)

                # Analyze else clause (executes if no exception)
                visit_statements(node.orelse, depth + 1, in_unreachable=False)

                # Analyze finally clause (always executes)
                visit_statements(node.finalbody, depth + 1,
                               in_unreachable=False)

            else:
                # Regular statement (assignment, expression, etc.)
                # No special handling needed
                pass

            i += 1

        return forced_end_here

    # Analyze all function definitions in the AST
    for node in tree.body:
        if isinstance(node, ast.FunctionDef):
            # Create a block for the function definition itself
            func_block = new_block_id()

            # Recursively analyze the function body
            visit_statements(node.body, depth=1, in_unreachable=False)

    # Format unreachable blocks for output
    if len(unreachable_blocks) == 0:
        unreachable_str = "NONE"
    elif len(unreachable_blocks) == 1:
        # FIXED: Return int for single unreachable block
        unreachable_str = list(unreachable_blocks)[0]
    else:
        # Sort block IDs and join with spaces for multiple blocks
        unreachable_str = " ".join(str(b) for b in sorted(unreachable_blocks))

    # Return the analysis results
    return (
        block_counter,  # Total number of blocks
        decision_points,  # Total number of decision points
        max_depth if max_depth > 0 else 0,  # Maximum nesting depth
        unreachable_str,  # Unreachable block IDs or "NONE"
        loop_status  # "FINITE" or "INFINITE"
    )


def driver_code(source_lines):
    """
    Driver function that formats the analysis results for output.

    Args:
        source_lines: List of strings representing Python source code

    Returns:
        str: Formatted output string matching problem requirements
    """
    # Get analysis results
    (blocks_count, decision_points, max_depth,
     unreachable_blocks, loop_status) = analyze_control_flow(source_lines)

    # Format output according to problem specification
    if unreachable_blocks == "NONE":
        out_str = (f"({blocks_count}, {decision_points}, {max_depth}, "
                  f"NONE, {loop_status})")
    else:
        out_str = (f"({blocks_count}, {decision_points}, {max_depth}, "
                  f"{unreachable_blocks}, {loop_status})")

    return out_str


# Self-test examples (uncomment to run)
if __name__ == "__main__":
    # Example 1: Basic if-else with unreachable code
    src1 = [
        "def calculate(x):",
        "    if x > 0:",
        "        return x * 2",
        "    else:",
        "        return 0",
        "    print(\"unreachable\")"
    ]
    print(driver_code(src1))
    # Expected: (5, 2, 2, 4, FINITE)

    # Example 2: For loop with try-except
    src2 = [
        "def process_data(items):",
        "    for item in items:",
        "        if not item:",
        "            continue",
        "        try:",
        "            result = item.process()",
        "        except:",
        "            pass",
        "    return \"done\""
    ]
    print(driver_code(src2))
    # Expected: (8, 4, 3, NONE, FINITE)

    # Example 3: Infinite while loop
    src3 = [
        "def loop_test():",
        "    x = 1",
        "    while x > 0:",
        "        x += 1",
        "    return x"
    ]
    print(driver_code(src3))
    # Expected: (5, 1, 2, NONE, INFINITE)

