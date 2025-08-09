"""
GraphQL Schema Adapter.

This module defines a Python class to adapt to GraphQL schema changes.

It uses introspection API and supports schema comparison,
error handling, caching, and memory safety.
"""

import requests
import re
import threading
import copy
import resource


class SchemaFormatError(Exception):
    """Raised when the schema is malformed or missing required keys."""

    pass


class NetworkError(Exception):
    """Raised when there is a network communication issue."""

    pass


class ValidationError(Exception):
    """Raised when validation of a user argument fails."""

    pass


_INTROSPECTION_QUERY = """
query IntrospectionQuery {
  __schema {
    queryType { name }
    mutationType { name }
    subscriptionType { name }
    types {
      ...FullType
    }
    directives {
      name
      description
      locations
      args {
        ...InputValue
      }
    }
  }
}

fragment FullType on __Type {
  kind
  name
  description
  fields(includeDeprecated: true) {
    name
    description
    args {
      ...InputValue
    }
    type {
      ...TypeRef
    }
    isDeprecated
    deprecationReason
  }
  inputFields {
    ...InputValue
  }
  interfaces {
    ...TypeRef
  }
  enumValues(includeDeprecated: true) {
    name
    description
    isDeprecated
    deprecationReason
  }
  possibleTypes {
    ...TypeRef
  }
}

fragment InputValue on __InputValue {
  name
  description
  type { ...TypeRef }
  defaultValue
}

fragment TypeRef on __Type {
  kind
  name
  ofType {
    kind
    name
    ofType {
      kind
      name
      ofType {
        kind
        name
        ofType {
          kind
          name
        }
      }
    }
  }
}
"""


def _is_valid_url(url):
    """Check if the provided URL is valid for HTTP/HTTPS."""
    return bool(re.match(r'^https?://[^\s/$.?#].[^\s]*$', url))


def _build_type_signature(type_obj):
    """Recursively construct a type string from introspection type."""
    if not type_obj:
        return "None"
    kind = type_obj.get("kind")
    name = type_obj.get("name")
    of_type = type_obj.get("ofType")
    if kind == "NON_NULL":
        return f"{_build_type_signature(of_type)}!"
    if kind == "LIST":
        return f"[{_build_type_signature(of_type)}]"
    return name or (_build_type_signature(of_type) if of_type else "Unknown")


def _extract_types(schema):
    """Extract a name->type mapping of types from a schema object."""
    return {
        t.get("name"): t
        for t in schema.get("__schema", {}).get("types", [])
        if t.get("name")
    }


def _extract_fields(type_obj):
    """Extract a mapping of field names to type/args for one GraphQL type."""
    result = {}
    for field in (type_obj.get("fields", []) or []):
        args = {
            a.get("name"): {
                "type": _build_type_signature(a.get("type")),
                "default": a.get("defaultValue")
            }
            for a in (field.get("args", []) or [])
        }
        result[field.get("name")] = {
            "type": _build_type_signature(field.get("type")),
            "args": args
        }
    return result


def _get_memory_usage_mb():
    """Calculate memory usage in MB."""
    try:
        usage = resource.getrusage(resource.RUSAGE_SELF)
        return usage.ru_maxrss / 1024 if hasattr(usage, 'ru_maxrss') else 0
    except Exception:
        return 0


class GraphQLSchemaAdapter:
    """Adapter for dynamic GraphQL schema introspection, change detection."""

    _schema_cache = {}
    _cache_lock = threading.Lock()

    def __init__(self, endpoint, headers=None, config=None):
        """Initialize the adapter with an endpoint, headers, and configuration.

        Args:
            endpoint (str): GraphQL endpoint URL (must be valid HTTP/HTTPS).
            headers (dict): Optional HTTP headers.
            config (dict): Optional config flags.
        Raises:
            ValidationError: If the endpoint is not valid.
        """
        if not (isinstance(endpoint, str) and _is_valid_url(endpoint)):
            raise ValidationError("Invalid GraphQL endpoint URL.")
        self.endpoint = endpoint
        self.headers = headers if headers and isinstance(headers, dict) else {}
        self.config = {
            "validate_changes": True,
            "print_diff": False,
            "update_internal_state": True,
        }
        if config:
            for key in config:
                if key in self.config:
                    self.config[key] = config[key]
                else:
                    raise ValidationError(f"Unsupported config key: {key}")
        self.internal_state = None

    def fetch_current_schema(self):
        """Perform an introspection query and return the current schema.

        Returns:
            dict: Introspection schema object as returned from endpoint.

        Raises:
            NetworkError, SchemaFormatError, MemoryError
        """
        cache_key = (self.endpoint, frozenset(self.headers.items()))
        with GraphQLSchemaAdapter._cache_lock:
            cached = GraphQLSchemaAdapter._schema_cache.get(cache_key)
            if cached:
                return copy.deepcopy(cached)
        try:
            resp = requests.post(
                self.endpoint,
                json={"query": _INTROSPECTION_QUERY},
                headers=self.headers,
                timeout=10,
            )
            if resp.status_code == 401:
                raise NetworkError("Unauthorized access"
                                   " to the endpoint (401).")
            resp.raise_for_status()
        except requests.exceptions.RequestException as exc:
            raise NetworkError(f"Failed to fetch schema from endpoint: {exc}")

        try:
            data = resp.json()
        except Exception as exc:
            raise SchemaFormatError(
                f"Failed to parse JSON from schema response: {exc}"
            )

        if (
            not isinstance(data, dict)
            or "data" not in data
            or "__schema" not in data["data"]
        ):
            raise SchemaFormatError("Introspection result "
                                    "missing '__schema' key.")
        schema = {"__schema": data["data"]["__schema"]}

        with GraphQLSchemaAdapter._cache_lock:
            GraphQLSchemaAdapter._schema_cache[
                cache_key] = copy.deepcopy(schema)

        if _get_memory_usage_mb() > 100:
            raise MemoryError(
                "Memory usage exceeded 100 MB limit during schema fetch."
            )

        return schema

    def load_previous_schema(self, source):
        """Validate and return the provided previous schema dict."""
        if not source:
            return None
        if not (isinstance(source, dict) and "__schema" in source):
            raise SchemaFormatError(
                "Provided previous schema must"
                " be a dict with a '__schema' key."
            )
        return source

    def compare_schemas(self, old_schema, new_schema):
        """Compare old and new schemas and return a diff.

        Args:
            old_schema (dict): Previous schema object.
            new_schema (dict): Latest schema object.

        Returns:
            dict: Diff dict with 'added_types',
            'removed_types', and 'changed_fields'.
        """
        old_types = _extract_types(old_schema) if old_schema else {}
        new_types = _extract_types(new_schema)

        added_types = []
        removed_types = []
        changed_fields = []

        for t_name, t in new_types.items():
            if t_name not in old_types:
                added_types.append({"type": t_name, "kind": t.get("kind")})

        for t_name, t in old_types.items():
            if t_name not in new_types:
                removed_types.append({"type": t_name, "kind": t.get("kind")})

        for t_name in new_types:
            if t_name not in old_types:
                continue
            old_fields = _extract_fields(old_types[t_name])
            new_fields = _extract_fields(new_types[t_name])

            for f_name, f_data in new_fields.items():
                if f_name not in old_fields:
                    added_types.append(
                        {"type": t_name, "field": f_name, "action": "added"}
                    )
            for f_name in old_fields:
                if f_name not in new_fields:
                    removed_types.append(
                        {"type": t_name, "field": f_name, "action": "removed"}
                    )
            for f_name in old_fields:
                if f_name in new_fields:
                    old_f = old_fields[f_name]
                    new_f = new_fields[f_name]
                    if (old_f["type"] != new_f["type"]) or (
                        old_f["args"] != new_f["args"]
                    ):
                        changed_fields.append(
                            {
                                "type": t_name,
                                "field": f_name,
                                "old_type": old_f["type"],
                                "new_type": new_f["type"],
                                "old_args": old_f["args"],
                                "new_args": new_f["args"],
                            }
                        )

        diff = {
            "added_types": added_types,
            "removed_types": removed_types,
            "changed_fields": changed_fields,
        }

        if _get_memory_usage_mb() > 100:
            raise MemoryError(
                "Memory usage exceeded 100 MB during schema comparison."
            )

        return diff

    def update_internal_state(self, schema_diff):
        """Update the object's state with schema_diff, if configured."""
        if self.config.get("update_internal_state", True):
            self.internal_state = copy.deepcopy(schema_diff)

    def run(self, old_schema=None):
        """Orchestrate schema fetch, diff, state update, and return results.

        Args:
            old_schema (dict): Previous schema, or None.

        Returns:
            dict: Result, including 'current_schema' and, if present, the diff.
        """
        current_schema = self.fetch_current_schema()
        result = {"current_schema": copy.deepcopy(current_schema)}
        if old_schema:
            old_loaded = self.load_previous_schema(old_schema)
            diff = self.compare_schemas(old_loaded, current_schema)
            result.update(diff)
            if self.config.get("update_internal_state", True):
                self.update_internal_state(diff)
        return result

