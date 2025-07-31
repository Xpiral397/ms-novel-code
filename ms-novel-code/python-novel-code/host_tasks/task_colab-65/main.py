import re


class AspectMeta(type):
    """Metaclass for aspect weaving simulation."""

    def __new__(mcs, name, bases, dct):
        """Create class normally - weaving logic would be inserted here."""
        cls = super().__new__(mcs, name, bases, dct)
        return cls

    def __init__(cls, name, bases, dct):
        """Initialize class after creation."""
        super().__init__(name, bases, dct)


def c3_linearization(class_name, parent_lists, visited=None):
    """Compute C3 linearization (MRO) for the given class."""
    if visited is None:
        visited = set()
    if class_name in visited:
        return None
    visited.add(class_name)
    parents = parent_lists.get(class_name, [])
    if not parents:
        visited.remove(class_name)
        return [class_name]
    parent_mros = []
    for parent in parents:
        if parent == class_name:
            return None
        parent_mro = c3_linearization(parent, parent_lists, visited)
        if parent_mro is None:
            return None
        parent_mros.append(parent_mro)
    parent_mros.append(parents)
    mro = []
    sequences = [list(mro_seq) for mro_seq in parent_mros]
    while True:
        sequences = [seq for seq in sequences if seq]
        if not sequences:
            break
        candidate_found = None
        for sequence in sequences:
            candidate = sequence[0]
            appears_in_tail = any(
                candidate in seq[1:] for seq in sequences
            )
            if not appears_in_tail:
                candidate_found = candidate
                break
        if candidate_found is None:
            return None
        mro.append(candidate_found)
        for sequence in sequences:
            if sequence and sequence[0] == candidate_found:
                sequence.pop(0)
    visited.remove(class_name)
    return [class_name] + mro


def is_valid_pointcut_expression(expr):
    """Validate pointcut expression for syntax correctness."""
    if '||' in expr:
        return False
    patterns = expr.split('|')
    for pattern in patterns:
        if not pattern.strip():
            return False
    return True


def match_pointcut(expression, target):
    """Check if the target matches the pointcut expression."""
    sub_expressions = expression.split('|')
    target_parts = target.split('.')
    method_name = target_parts[-1] if target_parts else target
    for subexpr in sub_expressions:
        subexpr = subexpr.strip()
        if not subexpr:
            continue
        pattern = '^' + re.escape(subexpr).replace('\\*', '.*') + '$'
        try:
            if re.match(pattern, target):
                return True
            if re.match(pattern, method_name):
                return True
        except re.error:
            continue
    return False


def process_aspect_weaving(services, pointcuts, execution_events):
    """Main function to process aspect weaving based on services and events."""
    class_parents = {}
    method_aspects_map = {}
    class_mro = {}
    all_classes = set()
    for service in services:
        module_name = service['module_name']
        base_class_names = service.get('base_classes', [])
        class_defs = service.get('class_definitions', [])
        method_aspects = service.get('method_aspects', {})
        for method_name, aspect_name in method_aspects.items():
            method_aspects_map[(module_name, method_name)] = aspect_name
        for base_class in base_class_names:
            key = (module_name, base_class)
            if key not in class_parents:
                class_parents[key] = []
                all_classes.add(key)
        for class_def in class_defs:
            class_name = class_def['name']
            parents = class_def.get('parents', [])
            key = (module_name, class_name)
            class_parents[key] = parents
            all_classes.add(key)
            for parent in parents:
                parent_key = (module_name, parent)
                if parent_key not in class_parents:
                    class_parents[parent_key] = []
                    all_classes.add(parent_key)
    for (module, class_name) in class_parents.keys():
        if (module, class_name) not in class_mro:
            mro_list = c3_linearization_for_module(
                module, class_name, class_parents
            )
            class_mro[(module, class_name)] = mro_list
    valid_pointcuts = []
    for pointcut in pointcuts:
        pid = pointcut['pointcut_id']
        expr = pointcut['expression']
        priority = pointcut['priority']
        if not is_valid_pointcut_expression(expr):
            continue
        valid_pointcuts.append((pid, expr, priority))
    results = []
    for event in execution_events:
        parts = event.split('.')
        if len(parts) != 3:
            results.append("ERROR: METHOD_NOT_FOUND")
            continue
        module, class_name, method_name = parts
        if (module, class_name) not in all_classes:
            results.append("ERROR: METHOD_NOT_FOUND")
            continue
        mro_list = class_mro.get((module, class_name), None)
        if mro_list is None:
            results.append("ERROR: CIRCULAR_INHERITANCE")
            continue
        if (module, method_name) not in method_aspects_map:
            results.append("ERROR: METHOD_NOT_FOUND")
            continue
        target_fqn = f"{module}.{class_name}.{method_name}"
        matched_pointcuts = []
        for (pid, expr, prio) in valid_pointcuts:
            if match_pointcut(expr, target_fqn):
                matched_pointcuts.append((pid, prio))
        matched_pointcuts.sort(key=lambda x: (x[1], x[0]))
        if not matched_pointcuts:
            results.append(f"DIRECT: TARGET[{method_name}]")
        else:
            chain_parts = [f"{pid}[{prio}]" for (pid, prio) in matched_pointcuts]
            chain_parts.append(f"TARGET[{method_name}]")
            chain = " -> ".join(chain_parts)
            results.append(f"WEAVE: {chain}")
    return results


def c3_linearization_for_module(module, class_name, class_parents):
    """Compute MRO for classes restricted to a specific module."""
    local_parents = {
        cls: class_parents[(mod, cls)]
        for (mod, cls) in class_parents if mod == module
    }
    return c3_linearization(class_name, local_parents)


if __name__ == "__main__":
    services_example = [
        {
            'module_name': 'auth_system',
            'base_classes': ['Authenticator', 'Logger', 'Validator'],
            'class_definitions': [
                {
                    'name': 'AuthHandler',
                    'parents': ['Authenticator', 'Logger']
                },
                {
                    'name': 'SecureAuth',
                    'parents': ['AuthHandler', 'Validator']
                }
            ],
            'method_aspects': {
                'login': 'security_aspect',
                'validate': 'audit_aspect'
            }
        },
        {
            'module_name': 'data_system',
            'base_classes': ['DataAccess', 'Monitor', 'Cache'],
            'class_definitions': [
                {
                    'name': 'DataManager',
                    'parents': ['DataAccess', 'Monitor']
                }
            ],
            'method_aspects': {
                'read': 'perf_aspect',
                'write': 'perf_aspect'
            }
        }
    ]

    pointcuts_example = [
        {
            'pointcut_id': 'security_check',
            'expression': 'auth_system.*login*',
            'priority': 1
        },
        {
            'pointcut_id': 'audit_trail',
            'expression': '*validate*',
            'priority': 2
        },
        {
            'pointcut_id': 'performance_monitor',
            'expression': 'data_system.*read*|*write*',
            'priority': 3
        }
    ]

    execution_events_example = [
        'auth_system.AuthHandler.login',
        'auth_system.SecureAuth.validate',
        'data_system.DataManager.read',
        'auth_system.SecureAuth.login',
        'data_system.DataManager.write'
    ]

    output = process_aspect_weaving(
        services_example,
        pointcuts_example,
        execution_events_example
    )

    print("\n".join(output))

