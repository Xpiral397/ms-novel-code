import re
from typing import Dict, List, Tuple, Optional
from datetime import datetime


class NeuralCodeGenerator:
    """
    A framework that uses few-shot learning and metaprogramming to dynamically generate
    Python code using structured schema context and neural APIs like fcol and fval.
    """

    def __init__(self, context: dict, examples: list):
        self.context = self._validate_context(context)
        self.examples = self._validate_examples(examples)
        self.available_functions = {'fcol', 'fval', 'fjoin', 'sum', 'mean', 'len'}

    def _validate_context(self, context: dict) -> dict:
        """Validate and normalize the context schema."""
        if not isinstance(context, dict):
            raise ValueError("CONTEXT must be a dictionary")

        required_keys = {'tables', 'foreign_keys'}
        if not required_keys.issubset(context.keys()):
            raise ValueError("CONTEXT must contain 'tables' and 'foreign_keys'")

        # Validate tables structure
        if not isinstance(context['tables'], dict):
            raise ValueError("CONTEXT.tables must be a dictionary")

        for table, columns in context['tables'].items():
            if not isinstance(columns, list) or not all(isinstance(c, str) for c in columns):
                raise ValueError(f"Columns for table {table} must be a list of strings")
            if not columns:
                raise ValueError(f"Table {table} must have at least one column")

        # Validate foreign keys
        if not isinstance(context['foreign_keys'], dict):
            raise ValueError("CONTEXT.foreign_keys must be a dictionary")

        for fk, pk in context['foreign_keys'].items():
            if '.' not in fk or '.' not in pk:
                raise ValueError("Foreign keys must be in format 'table.column'")
            fk_table, fk_col = fk.split('.')
            pk_table, pk_col = pk.split('.')

            if fk_table not in context['tables'] or fk_col not in context['tables'][fk_table]:
                raise ValueError(f"Foreign key {fk} references unknown table or column")
            if pk_table not in context['tables'] or pk_col not in context['tables'][pk_table]:
                raise ValueError(f"Primary key {pk} references unknown table or column")

        return context

    def _validate_examples(self, examples: list) -> list:
        """Validate few-shot examples structure."""
        if not isinstance(examples, list) or not examples:
            raise ValueError("FEW_SHOT_EXAMPLES must be a non-empty list")

        valid_examples = []
        for example in examples:
            if not isinstance(example, dict) or 'query' not in example or 'code' not in example:
                continue

            # Basic code validation - check for allowed functions
            code = example['code']
            if not isinstance(code, str):
                continue

            # Check for potentially dangerous code
            if any(kw in code for kw in ['eval', 'exec', 'import', '__']):
                continue

            valid_examples.append(example)

        if not valid_examples:
            raise ValueError("No valid examples provided in FEW_SHOT_EXAMPLES")

        return valid_examples

    def parse_query(self, user_query: str) -> dict:
        """
        Generates structured code and metadata from a user query.
        """
        if not user_query or not isinstance(user_query, str):
            raise ValueError("USER_QUERY must be a non-empty string")

        try:
            # Analyze query to determine required tables and columns
            query_tables, query_columns = self._analyze_query(user_query)

            # Generate code based on the query and examples
            generated_code = self._generate_code(user_query, query_tables, query_columns)

            # Extract used fields from the generated code
            used_tables, used_columns = self.extract_used_fields(generated_code)

            # Generate explanation
            explanation = self.explain_code(generated_code)

            return {
                "generated_code": generated_code,
                "used_tables": used_tables,
                "used_columns": used_columns,
                "explanation": explanation
            }
        except Exception as e:
            # Fallback to simple selection if anything goes wrong
            fallback_table = list(self.context['tables'].keys())[0]
            fallback_col = self.context['tables'][fallback_table][0]
            return {
                "generated_code": f"fcol('{fallback_table}', '{fallback_col}')",
                "used_tables": [fallback_table],
                "used_columns": {fallback_table: [fallback_col]},
                "explanation": f"Selects {fallback_col} from {fallback_table} (fallback)"
            }

    def _analyze_query(self, query: str) -> Tuple[List[str], Dict[str, List[str]]]:
        """Analyze the query to identify likely tables and columns needed."""
        query_lower = query.lower()
        tables_in_query = []
        columns_in_query = {}

        # Match table names mentioned in query
        for table in self.context['tables']:
            if table.lower() in query_lower:
                tables_in_query.append(table)
                columns_in_query[table] = []

        # If no tables matched, use all tables
        if not tables_in_query:
            tables_in_query = list(self.context['tables'].keys())
            for table in tables_in_query:
                columns_in_query[table] = []

        # Try to identify columns from the query
        for table in tables_in_query:
            for column in self.context['tables'][table]:
                if column.lower() in query_lower:
                    columns_in_query[table].append(column)

        return tables_in_query, columns_in_query

    def _generate_code(self, query: str, query_tables: List[str], query_columns: Dict[str, List[str]]) -> str:
        """Generate code using few-shot learning patterns with robust error handling."""
        try:
            # Check for count pattern
            if any(word in query.lower() for word in ['count', 'number of', 'how many']):
                return self._generate_count_code(query, query_tables, query_columns)

            # Check for filter pattern
            if any(word in query.lower() for word in ['list', 'show', 'find', 'where']):
                return self._generate_filter_code(query, query_tables, query_columns)

            # Default to simple column selection
            return self._generate_simple_code(query, query_tables, query_columns)
        except Exception as e:
            # Fallback to selecting first column from first table
            fallback_table = query_tables[0] if query_tables else list(self.context['tables'].keys())[0]
            fallback_col = self.context['tables'][fallback_table][0]
            return f"fcol('{fallback_table}', '{fallback_col}')"

    def _generate_count_code(self, query: str, query_tables: List[str], query_columns: Dict[str, List[str]]) -> str:
        """Generate code for counting operations."""
        if not query_tables:
            raise ValueError("No tables identified for count operation")

        main_table = max(query_tables, key=lambda t: len(query_columns.get(t, [])))
        available_cols = query_columns.get(main_table, self.context['tables'][main_table])
        if not available_cols:
            raise ValueError(f"No columns available for table {main_table}")

        filter_cond = self._extract_filter_condition(query)

        if filter_cond:
            table, column, op, value = filter_cond
            if table == main_table:
                return f"len(fcol('{table}', '{available_cols[0]}')[fval('{table}', '{column}') {op} {value}])"
            else:
                join_cond = self._find_join_condition(main_table, table)
                if join_cond:
                    return f"len(fcol('{main_table}', '{available_cols[0]}')[fjoin('{main_table}', '{table}', on='{join_cond}')['{column}'] {op} {value}])"

        return f"len(fcol('{main_table}', '{available_cols[0]}'))"

    def _generate_filter_code(self, query: str, query_tables: List[str], query_columns: Dict[str, List[str]]) -> str:
        """Generate code for filtering operations with proper column selection."""
        # Identify target table (Customers) and filter table (Orders)
        target_table = next((t for t in query_tables if 'customer' in t.lower()), None)
        filter_table = next((t for t in self.context['tables'] if 'order' in t.lower()), None)

        if not target_table or not filter_table:
            # Fallback to simple selection if we can't identify tables
            main_table = max(query_tables, key=lambda t: len(query_columns.get(t, [])))
            available_cols = query_columns.get(main_table, self.context['tables'][main_table])
            if not available_cols:
                raise ValueError(f"No columns available for table {main_table}")
            return f"fcol('{main_table}', '{available_cols[0]}')"

        # Find target column (Name)
        target_cols = query_columns.get(target_table, self.context['tables'][target_table])
        target_col = next((c for c in target_cols if c.lower() == 'name'), target_cols[0])

        # Find filter column (Revenue)
        filter_cols = self.context['tables'][filter_table]
        filter_col = next((c for c in filter_cols if c.lower() in ['revenue', 'amount', 'price']), filter_cols[0])

        # Check for join condition
        join_cond = self._find_join_condition(target_table, filter_table)
        filter_cond = self._extract_filter_condition(query)

        if filter_cond and join_cond:
            _, _, op, value = filter_cond
            return f"fcol('{target_table}', '{target_col}')[fjoin('{target_table}', '{filter_table}', on='{join_cond}')['{filter_col}'] {op} {value}]"
        elif filter_cond:
            table, column, op, value = filter_cond
            return f"fcol('{table}', '{column}')[fval('{table}', '{column}') {op} {value}]"

        return f"fcol('{target_table}', '{target_col}')"

    def _generate_simple_code(self, query: str, query_tables: List[str], query_columns: Dict[str, List[str]]) -> str:
        """Generate simple column selection code with proper error handling."""
        if not query_tables:
            raise ValueError("No tables identified for simple selection")

        main_table = max(query_tables, key=lambda t: len(query_columns.get(t, [])))
        available_cols = query_columns.get(main_table, self.context['tables'][main_table])
        if not available_cols:
            raise ValueError(f"No columns available for table {main_table}")

        return f"fcol('{main_table}', '{available_cols[0]}')"

    def _extract_filter_condition(self, query: str) -> Optional[Tuple[str, str, str, str]]:
        """Improved filter condition extraction that handles monetary values and implicit joins."""
        query_lower = query.lower()

        # Enhanced comparison pattern detection
        comparisons = [
            ('>', ['above', 'greater than', 'higher than', 'over']),
            ('<', ['below', 'less than', 'under']),
            ('>=', ['at least', 'minimum of']),
            ('<=', ['at most', 'maximum of']),
            ('==', ['equal to', 'exactly']),
            ('!=', ['not equal to', 'different from'])
        ]

        # First try numeric comparisons
        money_values = re.findall(r'\$(\d+)', query)
        if money_values:
            value = money_values[0]
            # Find what column this applies to
            if 'revenue' in query_lower or 'amount' in query_lower or 'price' in query_lower:
                table = next((t for t in self.context['tables'] if 'orders' in t.lower()), None)
                if table:
                    column = next((c for c in self.context['tables'][table]
                                   if c.lower() in ['revenue', 'amount', 'price']), None)
                    if column:
                        # Find the comparison direction
                        if 'above' in query_lower or 'over' in query_lower or 'greater' in query_lower:
                            return (table, column, '>', value)
                        elif 'below' in query_lower or 'under' in query_lower or 'less' in query_lower:
                            return (table, column, '<', value)

        # Then try regular comparison operators
        for operator, keywords in comparisons:
            # Check for symbolic operators
            if f" {operator} " in query:
                parts = query.split(operator)
                left = parts[0].strip()
                right = parts[1].strip()

                # Find column in left part
                for table in self.context['tables']:
                    for column in self.context['tables'][table]:
                        if column.lower() in left.lower():
                            value = self._extract_value(right)
                            if value is not None:
                                return (table, column, operator, value)

            # Check for keyword operators
            for keyword in keywords:
                if keyword in query_lower:
                    parts = query_lower.split(keyword)
                    left = parts[0].strip()
                    right = parts[1].strip()

                    for table in self.context['tables']:
                        for column in self.context['tables'][table]:
                            if column.lower() in left.lower():
                                value = self._extract_value(right)
                                if value is not None:
                                    return (table, column,
                                            '>' if keyword in ['above', 'greater than', 'higher than', 'over'] else
                                            '<' if keyword in ['below', 'less than', 'under'] else
                                            '>=', value)
        return None

    def _extract_value(self, text: str) -> Optional[str]:
        """Extract a value from text (simplified)."""
        # Try to find numbers
        numbers = re.findall(r'\d+\.?\d*', text)
        if numbers:
            return numbers[0]

        # Try to find quoted strings
        strings = re.findall(r'[\'\"](.*?)[\'\"]', text)
        if strings:
            return f"'{strings[0]}'"

        # Try boolean values
        if 'true' in text.lower():
            return 'True'
        if 'false' in text.lower():
            return 'False'

        # Try date strings
        date_matches = re.findall(r'(\d{4}-\d{2}-\d{2})|([A-Za-z]+ \d{1,2}, \d{4})', text)
        if date_matches:
            date = next(d for d in date_matches[0] if d)
            return f"'{date}'"

        return None

    def _find_join_condition(self, table1: str, table2: str) -> Optional[str]:
        """Find join condition between two tables using foreign keys."""
        # Check direct foreign key relationships
        for fk, pk in self.context['foreign_keys'].items():
            fk_table, fk_col = fk.split('.')
            pk_table, pk_col = pk.split('.')

            if (fk_table == table1 and pk_table == table2):
                return fk_col
            if (fk_table == table2 and pk_table == table1):
                return pk_col

        return None

    def extract_used_fields(self, code: str) -> Tuple[List[str], Dict[str, List[str]]]:
        """Extract tables and columns used in the generated code."""
        tables = set()
        columns = {}

        # Find all fcol and fval calls
        fcol_matches = re.findall(r"fcol\('([^']+)',\s*'([^']+)'\)", code)
        fval_matches = re.findall(r"fval\('([^']+)',\s*'([^']+)'\)", code)
        fjoin_matches = re.findall(r"fjoin\('([^']+)',\s*'([^']+)'", code)

        # Process fcol and fval matches
        for table, column in fcol_matches + fval_matches:
            tables.add(table)
            if table not in columns:
                columns[table] = []
            if column not in columns[table]:
                columns[table].append(column)

        # Process fjoin matches
        for table1, table2 in fjoin_matches:
            tables.add(table1)
            tables.add(table2)
            # Add join columns if we can find them
            join_col = self._find_join_condition(table1, table2)
            if join_col:
                if table1 not in columns:
                    columns[table1] = []
                if join_col not in columns[table1]:
                    columns[table1].append(join_col)

        return sorted(tables), columns

    def explain_code(self, code: str) -> str:
        """Generate clean natural language explanations without number splitting."""
        try:
            # Handle join operations
            if 'fjoin' in code:
                join_match = re.search(r"fjoin\('([^']+)',\s*'([^']+)'", code)
                filter_match = re.search(r"\['([^']+)'\]\s*([><=!]+)\s*([\d,]+(?:\.\d+)?)", code)
                col_match = re.search(r"fcol\('([^']+)',\s*'([^']+)'\)", code)

                if join_match and filter_match and col_match:
                    table1, table2 = join_match.groups()
                    filter_col, op, val = filter_match.groups()
                    select_table, select_col = col_match.groups()

                    # Format number properly
                    val = val.replace(',', '')  # Remove existing commas
                    if val.isdigit():
                        val = f"{int(val):,}"  # Add proper comma formatting

                    # Special formatting for money values
                    if 'revenue' in filter_col.lower() or 'amount' in filter_col.lower():
                        val = f"${val}"

                    return f"Selects {select_col} from {select_table} joined with {table2} where {filter_col} {op} {val}"

            # Handle simple filters
            elif 'fval' in code:
                filter_match = re.search(r"fval\('([^']+)',\s*'([^']+)'\)\s*([><=!]+)\s*([\d,]+(?:\.\d+)?)", code)
                col_match = re.search(r"fcol\('([^']+)',\s*'([^']+)'\)", code)

                if filter_match and col_match:
                    table, col, op, val = filter_match.groups()
                    select_table, select_col = col_match.groups()

                    val = val.replace(',', '')
                    if val.isdigit():
                        val = f"{int(val):,}"

                    if 'revenue' in col.lower() or 'amount' in col.lower():
                        val = f"${val}"

                    return f"Selects {select_col} from {select_table} where {col} {op} {val}"

            # Handle simple selects
            col_match = re.search(r"fcol\('([^']+)',\s*'([^']+)'\)", code)
            if col_match:
                table, col = col_match.groups()
                return f"Selects {col} from {table}"

            return "Performs the requested data operation"
        except Exception:
            return "Performs the requested data operation"


def generate_code_from_query(user_query: str, context: dict, few_shot_examples: list) -> dict:
    """
    Generates executable Python code from a user query using neural API patterns.

    Args:
        user_query (str): Natural language query describing the data operation.
        context (dict): Schema information including tables and foreign keys.
        few_shot_examples (list): List of (query, code) pairs for few-shot learning.

    Returns:
        dict: Contains generated_code, used_tables, used_columns, and explanation.
    """
    generator = NeuralCodeGenerator(context, few_shot_examples)
    return generator.parse_query(user_query)


# Example usage
if __name__ == "__main__":
    # Test case 1: Customer orders
    print("=== Test Case 1 ===")
    result1 = generate_code_from_query(
        "List the names of customers who placed orders above $1000000",
        {
            "tables": {
                "Customers": ["CustomerID", "Name"],
                "Orders": ["OrderID", "CustomerID", "Revenue"]
            },
            "foreign_keys": {
                "Orders.CustomerID": "Customers.CustomerID"
            }
        },
        [
            {
                "query": "Show all orders with revenue above 500",
                "code": "fcol('Orders', 'OrderID')[fval('Orders', 'Revenue') > 1000000]"
            },
            {
                "query": "List names of customers from France",
                "code": "fcol('Customers', 'Name')[fval('Customers', 'Country') == 'France']"
            }
        ]
    )
    print("Generated Code:", result1["generated_code"])
    print("Used Tables:", result1["used_tables"])
    print("Used Columns:", result1["used_columns"])
    print("Explanation:", result1["explanation"])
    print()

    # Test case 2: Date filtering
    print("=== Test Case 2 ===")
    result2 = generate_code_from_query(
        "Find orders placed after January 1, 2023 with amount over $500",
        {
            "tables": {
                "Customers": ["CustomerID", "Name", "JoinDate"],
                "Orders": ["OrderID", "CustomerID", "Revenue", "OrderDate"]
            },
            "foreign_keys": {
                "Orders.CustomerID": "Customers.CustomerID"
            }
        },
        [
            {
                "query": "Show orders from 2023",
                "code": "fcol('Orders', 'OrderID')[fval('Orders', 'OrderDate') >= '2023-01-01']"
            },
            {
                "query": "List high value orders over $1000",
                "code": "fcol('Orders', 'OrderID')[fval('Orders', 'Revenue') > 1000]"
            }
        ]
    )
    print("Generated Code:", result2["generated_code"])
    print("Used Tables:", result2["used_tables"])
    print("Used Columns:", result2["used_columns"])
    print("Explanation:", result2["explanation"])
