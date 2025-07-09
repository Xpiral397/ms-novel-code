
def generate_sqlalchemy_model(columns: list[dict]) -> str:
    """
    Generates a SQLAlchemy model class using declarative base syntax
    from the given list of column definitions.

    Args:
        columns: List of dictionaries where each dictionary represents a column
                 with metadata such as name, type, nullability, primary key flag,
                 and server default configuration.

    Returns:
        A string containing the generated SQLAlchemy model class.
    """
    imports = set()
    type_imports = set()
    uses_text = False
    uses_func = False
    uses_postgresql = False
    lines = []

    INDENT = " " * 4

    for column in columns:
        name = column.get("name")
        col_type = column.get("type")
        primary_key = column.get("primary_key", False)
        nullable = column.get("nullable", True)
        server_default = column.get("server_default", False)
        default_function = column.get("default_function")

        if not name or not col_type:
            continue  # Skip malformed column definitions

        # Determine the SQLAlchemy type and import
        if col_type == "String":
            sa_type = "String"
            type_imports.add("String")
        elif col_type == "Integer":
            sa_type = "Integer"
            type_imports.add("Integer")
        elif col_type == "DateTime":
            sa_type = "DateTime"
            type_imports.add("DateTime")
        elif col_type == "Boolean":
            sa_type = "Boolean"
            type_imports.add("Boolean")
        elif col_type == "Float":
            sa_type = "Float"
            type_imports.add("Float")
        elif col_type == "UUID":
            sa_type = "UUID"
            type_imports.add("UUID")
            uses_postgresql = True
        else:
            continue  # Unsupported type

        # Build column definition
        col_parts = [f"{name} = Column({sa_type}"]

        if primary_key:
            col_parts.append("primary_key=True")
        if not nullable:
            col_parts.append("nullable=False")

        # Handle server_default
        if server_default:
            if isinstance(default_function, str):
                # Check for known SQL function defaults
                lowered = default_function.lower()
                if lowered in {"now", "current_timestamp", "uuid_generate_v4", "gen_random_uuid"}:
                    col_parts.append(f"server_default=func.{lowered}()")
                    uses_func = True
                else:
                    # Treat as raw SQL string literal
                    col_parts.append(f"server_default=text({default_function})")
                    uses_text = True
            elif isinstance(default_function, (int, float, bool)):
                val = str(default_function).upper() if isinstance(default_function, bool) else str(default_function)
                col_parts.append(f"server_default=text('{val}')")
                uses_text = True

        col_parts_str = ", ".join(col_parts) + ")"
        lines.append(INDENT + col_parts_str)

    # Prepare import lines
    imports.add("from sqlalchemy import Column")
    if type_imports:
        imports.add(f"from sqlalchemy import {', '.join(sorted(type_imports - {'UUID'}))}")
    if uses_text:
        imports.add("from sqlalchemy import text")
    if uses_func:
        imports.add("from sqlalchemy.sql import func")
    if uses_postgresql:
        imports.add("from sqlalchemy.dialects.postgresql import UUID")
    imports.add("from sqlalchemy.ext.declarative import declarative_base")

    # Assemble final output
    output = []
    output.extend(sorted(imports))
    output.append("")
    output.append("Base = declarative_base()")
    output.append("")
    output.append("class GeneratedModel(Base):")
    output.append(INDENT + "__tablename__ = 'generated_model'")
    if lines:
        output.extend(lines)
    else:
        output.append(INDENT + "pass")

    return "\n".join(output)
