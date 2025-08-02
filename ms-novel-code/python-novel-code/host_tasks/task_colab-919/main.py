import os
import json
import time
import hashlib
import logging
from datetime import datetime, timezone
from typing import Set, Union

import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

# Configure logging
logger = logging.getLogger(__name__)


class GraphQLAdaptiveError(Exception):
    """Raised for any GraphQL adaptive client error."""
    pass


class AdaptiveClient:
    """Self-adapting GraphQL client that handles evolving schemas."""

    INTROSPECTION_QUERY = """
    query IntrospectionQuery {
      __schema {
        queryType { name }
        mutationType { name }
        subscriptionType { name }
        types {
          kind
          name
          description
          fields(includeDeprecated: true) {
            name
            description
            args {
              name
              type { ...TypeRef }
              defaultValue
            }
            type { ...TypeRef }
            isDeprecated
            deprecationReason
          }
          inputFields {
            name
            description
            type { ...TypeRef }
            defaultValue
          }
          interfaces { ...TypeRef }
          enumValues(includeDeprecated: true) {
            name
            description
            isDeprecated
            deprecationReason
          }
          possibleTypes { ...TypeRef }
        }
        directives {
          name
          description
          locations
          args {
            name
            description
            type { ...TypeRef }
            defaultValue
          }
        }
      }
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
        }
      }
    }
    """

    SCALAR_TYPES = {
        'Int', 'Float', 'String', 'Boolean', 'ID'
    }

    def __init__(self,
                 endpoint: str,
                 headers: dict | None = None,
                 refresh_interval_seconds: int = 0):
        """Initialize the adaptive GraphQL client."""
        if not endpoint.startswith('https://'):
            raise GraphQLAdaptiveError("Endpoint must use HTTPS")

        self._endpoint = endpoint
        self._headers = headers or {}
        self._refresh_interval = refresh_interval_seconds

        # Schema cache
        self._schema_raw = None
        self._schema_hash = None
        self._schema_timestamp = 0
        self._schema_types = {}

        # Setup session with retry strategy
        self._session = self._create_session()

    def _create_session(self) -> requests.Session:
        """Create requests session with retry logic and proper configuration."""
        session = requests.Session()

        # Configure retry strategy for 429 and 503 only
        retry_strategy = Retry(
            total=3,
            status_forcelist=[429, 503],
            backoff_factor=1,  # 1s, 2s, 4s progression
            raise_on_status=False
        )

        adapter = HTTPAdapter(max_retries=retry_strategy)
        session.mount('https://', adapter)

        # Set default headers
        session.headers.update({
            'Content-Type': 'application/json',
            **self._headers
        })

        return session

    def _check_offline_mode(self) -> None:
        """Check if offline mode is enabled via environment variable."""
        if os.environ.get('ADAPTIVE_GQL_OFFLINE') == '1':
            raise GraphQLAdaptiveError(
                "Offline mode enabled - network calls disabled")

    def _should_refresh_schema(self, force: bool) -> bool:
        """Determine if schema should be refreshed."""
        if force:
            return True

        if self._schema_raw is None:
            return True

        if self._refresh_interval == 0:
            return False

        elapsed = time.time() - self._schema_timestamp
        return elapsed >= self._refresh_interval

    def _execute_request(self, payload: dict) -> dict:
        """Execute GraphQL request with proper error handling."""
        self._check_offline_mode()

        start_time = time.time()

        try:
            response = self._session.post(
                self._endpoint,
                json=payload,
                timeout=5.0
            )
            response.raise_for_status()

            result = response.json()

            # Check for GraphQL errors
            if 'errors' in result:
                error_msg = '; '.join(err.get('message', 'Unknown error')
                                      for err in result['errors'])
                raise GraphQLAdaptiveError(f"GraphQL errors: {error_msg}")

            if 'data' not in result:
                raise GraphQLAdaptiveError("No data in GraphQL response")

            return result

        except requests.exceptions.RequestException as e:
            raise GraphQLAdaptiveError(f"Network error: {e}")
        except json.JSONDecodeError as e:
            raise GraphQLAdaptiveError(f"Invalid JSON response: {e}")
        finally:
            duration_ms = (time.time() - start_time) * 1000
            logger.info(f"GraphQL request completed in {duration_ms:.2f}ms")

    def _compute_schema_hash(self, schema_data: dict) -> str:
        """Compute SHA-256 hash of schema data."""
        schema_json = json.dumps(
            schema_data, separators=(',', ':'), sort_keys=True)
        return hashlib.sha256(schema_json.encode('utf-8')).hexdigest()

    def _parse_type_ref(self, type_ref: dict) -> tuple[str, bool]:
        """Parse GraphQL type reference to get type name and nullability."""
        if type_ref['kind'] == 'NON_NULL':
            inner_type, _ = self._parse_type_ref(type_ref['ofType'])
            return inner_type, False  # Non-nullable
        elif type_ref['kind'] == 'LIST':
            inner_type, nullable = self._parse_type_ref(type_ref['ofType'])
            return f"[{inner_type}]", True  # Lists are nullable by default
        else:
            return type_ref['name'], True  # Nullable

    def _is_scalar_type(self, type_name: str) -> bool:
        """Check if a type is a scalar type."""
        if type_name in self.SCALAR_TYPES:
            return True

        # Check if it's a custom scalar
        type_info = self._schema_types.get(type_name, {})
        return type_info.get('kind') == 'SCALAR'

    def _parse_schema(self, schema_data: dict) -> None:
        """Parse introspection schema into internal representation."""
        self._schema_types = {}

        for type_def in schema_data['__schema']['types']:
            type_name = type_def['name']

            # Skip GraphQL internal types
            if type_name.startswith('__'):
                continue

            parsed_type = {
                'kind': type_def['kind'],
                'name': type_name,
                'fields': {}
            }

            # Parse fields for OBJECT and INTERFACE types
            if type_def['kind'] in ('OBJECT', 'INTERFACE') and type_def.get('fields'):
                for field in type_def['fields']:
                    field_name = field['name']
                    field_type, nullable = self._parse_type_ref(field['type'])

                    # Check if field requires arguments (other than id)
                    args = field.get('args', [])
                    requires_args = any(arg['name'] != 'id' for arg in args)

                    parsed_type['fields'][field_name] = {
                        'type': field_type,
                        'nullable': nullable,
                        'requires_args': requires_args
                    }

            self._schema_types[type_name] = parsed_type

    def refresh_schema(self, force: bool = False) -> None:
        """Refresh schema from GraphQL endpoint."""
        if not self._should_refresh_schema(force):
            return

        start_time = time.time()
        timestamp_str = datetime.now(
            timezone.utc).strftime('%Y-%m-%dT%H:%M:%S.%fZ')

        logger.info(f"Starting schema refresh at {timestamp_str}")

        payload = {
            'query': self.INTROSPECTION_QUERY,
            'variables': {}
        }

        try:
            result = self._execute_request(payload)
            schema_data = result['data']

            # Check if schema actually changed
            new_hash = self._compute_schema_hash(schema_data)

            if self._schema_hash and self._schema_hash != new_hash:
                logger.info(
                    "Schema hash changed - rebuilding internal structures")
            elif self._schema_hash == new_hash:
                logger.info("Schema unchanged - using cached structures")
                self._schema_timestamp = time.time()
                return

            # Parse and store new schema
            self._parse_schema(schema_data)
            self._schema_raw = schema_data
            self._schema_hash = new_hash
            self._schema_timestamp = time.time()

            duration_ms = (time.time() - start_time) * 1000
            logger.info(f"Schema refresh completed in {duration_ms:.2f}ms")

        except Exception as e:
            if isinstance(e, GraphQLAdaptiveError):
                if "Introspection" in str(e):
                    raise GraphQLAdaptiveError(
                        "GraphQL introspection is disabled on this server")
                raise
            raise GraphQLAdaptiveError(f"Schema refresh failed: {e}")

    def _build_scalar_query(self, object_type: str, visited: Set[str] = None) -> str:
        """Build query string for all scalar fields of an object type."""
        if visited is None:
            visited = set()

        if object_type in visited:
            return ""  # Prevent infinite recursion

        visited.add(object_type)

        type_info = self._schema_types.get(object_type)
        if not type_info:
            raise GraphQLAdaptiveError(f"Unknown object type: {object_type}")

        if type_info['kind'] not in ('OBJECT', 'INTERFACE'):
            raise GraphQLAdaptiveError(f"Type {object_type} is not queryable")

        fields = []

        # Get all fields in alphabetical order for deterministic output
        for field_name in sorted(type_info['fields'].keys()):
            field_info = type_info['fields'][field_name]

            # Skip fields that require arguments (except id)
            if field_info['requires_args']:
                continue

            field_type = field_info['type']

            # Handle list types
            if field_type.startswith('[') and field_type.endswith(']'):
                inner_type = field_type[1:-1]
                if self._is_scalar_type(inner_type):
                    fields.append(field_name)
            elif self._is_scalar_type(field_type):
                # Direct scalar field
                fields.append(field_name)
            elif not field_info['nullable']:
                # Non-nullable object field - include nested scalars
                try:
                    nested_query = self._build_scalar_query(
                        field_type, visited.copy())
                    if nested_query:
                        fields.append(f"{field_name} {{ {nested_query} }}")
                except GraphQLAdaptiveError:
                    # Skip if nested type not found or not queryable
                    pass

        return ' '.join(fields)

    def fetch_by_id(self, object_type: str, object_id: Union[int, str]) -> dict:
        """Fetch object by ID with all scalar fields."""
        # Ensure schema is fresh
        self.refresh_schema()

        # Build the query
        scalar_fields = self._build_scalar_query(object_type)
        if not scalar_fields:
            raise GraphQLAdaptiveError(
                f"No queryable scalar fields found for type {object_type}")

        query = f"""
        query FetchById($id: ID!) {{
          {object_type.lower()}(id: $id) {{
            {scalar_fields}
          }}
        }}
        """.strip()

        variables = {'id': str(object_id)}

        # Log the generated query
        query_compact = ' '.join(query.split())
        logger.info(f"Generated query: {query_compact}")
        logger.info(
            f"Variables: {json.dumps(variables, separators=(',', ':'))}")

        result = self.run_raw(query, variables)

        # Extract the specific object from response
        data = result.get('data', {})
        object_data = data.get(object_type.lower())

        if object_data is None:
            raise GraphQLAdaptiveError(
                f"No {object_type} found with id {object_id}")

        return object_data

    def run_raw(self, query: str, variables: dict | None = None) -> dict:
        """Execute raw GraphQL query."""
        payload = {
            'query': query,
            'variables': variables or {}
        }

        # Use deterministic JSON serialization
        payload_json = json.dumps(
            payload, separators=(',', ':'), sort_keys=True)
        logger.info(f"Executing query with payload: {payload_json}")

        return self._execute_request(payload)

