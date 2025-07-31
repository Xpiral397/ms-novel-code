
"""
Advanced Flask Security Headers Module

This module provides comprehensive security header management for Flask
applications with per-route configuration and dynamic CSP nonce support.
"""

import secrets
import copy
from typing import Dict, Any, Optional, List
from flask import Flask, g, request
from flask_talisman import Talisman


def apply_advanced_secure_headers(
    app: Flask,
    default_config: Optional[Dict[str, Any]] = None,
    route_config: Optional[Dict[str, Dict[str, Any]]] = None
) -> None:
    """
    Apply secure HTTP headers to Flask app with per-route configuration.

    Args:
        app: Flask application instance to secure
        default_config: Global security configuration dictionary with keys:
            - 'csp': Dict of CSP directives (e.g., {'default-src': ["'self'"]})
            - 'hsts': Integer for HSTS max-age in seconds (>= 0)
            - 'x_content_type_options': Boolean for X-Content-Type-Options
        route_config: Dict mapping route paths/endpoints to per-route configs
            with same structure as default_config

    Raises:
        ValueError: If configuration contains invalid values
        TypeError: If configuration contains invalid types

    Example:
        >>> app = Flask(__name__)
        >>> default_cfg = {
        ...     'csp': {'default-src': ["'self'"]},
        ...     'hsts': 86400,
        ...     'x_content_type_options': True
        ... }
        >>> route_cfg = {
        ...     '/api': {'hsts': 0},
        ...     '/dashboard': {
        ...         'csp': {'script-src': ["'self'", "'nonce-{nonce}'"]}
        ...     }
        ... }
        >>> apply_advanced_secure_headers(app, default_cfg, route_cfg)
    """
    if default_config is None:
        default_config = {}
    if route_config is None:
        route_config = {}

    # Validate configurations early
    _validate_config("default_config", default_config)
    for route_key, config in route_config.items():
        _validate_config(f"route_config['{route_key}']", config)

    # Store validated configs in app extensions
    if not hasattr(app, 'extensions'):
        app.extensions = {}
    app.extensions['advanced_secure_headers'] = {
        'default_config': default_config,
        'route_config': route_config
    }

    # Initialize base Talisman with minimal configuration
    # We'll override headers in our custom handlers
    Talisman(
        app,
        force_https=False,  # We'll handle this per-route
        strict_transport_security=False,  # We'll handle this per-route
        content_security_policy=False,  # We'll handle this per-route
        content_security_policy_nonce_in=[],  # We manage nonces ourselves
    )

    @app.before_request
    def _generate_nonce_for_request() -> None:
        """
        Generate cryptographically secure nonce for each request.

        The nonce is stored in Flask's g object and made available for
        template context and CSP header generation.
        """
        # Check if current route needs a nonce
        merged_config = _get_merged_config_for_request(app)
        csp_config = merged_config.get('csp', {})

        if _csp_requires_nonce(csp_config):
            g.csp_nonce = secrets.token_urlsafe(16)

    @app.after_request
    def _apply_security_headers(response):
        """
        Apply security headers based on merged route configuration.

        Args:
            response: Flask response object

        Returns:
            Modified response with appropriate security headers
        """
        merged_config = _get_merged_config_for_request(app)

        # Apply HSTS
        hsts_max_age = merged_config.get('hsts', 0)
        if hsts_max_age > 0:
            response.headers['Strict-Transport-Security'] = (
                f'max-age={hsts_max_age}'
            )
        else:
            # Remove HSTS header if disabled for this route
            response.headers.pop('Strict-Transport-Security', None)

        # Apply X-Content-Type-Options
        if merged_config.get('x_content_type_options', False):
            response.headers['X-Content-Type-Options'] = 'nosniff'
        else:
            response.headers.pop('X-Content-Type-Options', None)

        # Apply CSP
        csp_config = merged_config.get('csp')
        if csp_config is not None:
            csp_header = _build_csp_header(csp_config, get_current_nonce())
            if csp_header:
                response.headers['Content-Security-Policy'] = csp_header
        else:
            # CSP explicitly disabled for this route
            response.headers.pop('Content-Security-Policy', None)

        return response

    @app.context_processor
    def _inject_nonce_context() -> Dict[str, Any]:
        """
        Inject nonce into template context for easy access.

        Returns:
            Dictionary containing nonce value for template use
        """
        return {'nonce': get_current_nonce()}


def get_current_nonce() -> Optional[str]:
    """
    Return the current request's CSP nonce.

    Returns:
        Cryptographically secure nonce string or None if not generated

    Example:
        >>> # In a view function or template
        >>> nonce = get_current_nonce()
        >>> # nonce might be 'abc123def456' or None
    """
    return getattr(g, 'csp_nonce', None)


def _validate_config(config_name: str, config: Dict[str, Any]) -> None:
    """
    Validate security configuration dictionary.

    Args:
        config_name: Name of config for error messages
        config: Configuration dictionary to validate

    Raises:
        TypeError: If config values have wrong types
        ValueError: If config values are invalid
    """
    if not isinstance(config, dict):
        raise TypeError(f"{config_name} must be a dictionary")

    # Validate HSTS
    if 'hsts' in config:
        hsts_value = config['hsts']
        if not isinstance(hsts_value, int):
            raise TypeError(
                f"{config_name}['hsts'] must be an integer (seconds)"
            )
        if hsts_value < 0:
            raise ValueError(
                f"{config_name}['hsts'] must be non-negative"
            )

    # Validate X-Content-Type-Options
    if 'x_content_type_options' in config:
        xcto_value = config['x_content_type_options']
        if not isinstance(xcto_value, bool):
            raise TypeError(
                f"{config_name}['x_content_type_options'] must be a boolean"
            )

    # Validate CSP
    if 'csp' in config:
        csp_value = config['csp']
        if csp_value is not None and not isinstance(csp_value, dict):
            raise TypeError(
                f"{config_name}['csp'] must be a dictionary or None"
            )
        if isinstance(csp_value, dict):
            _validate_csp_config(config_name, csp_value)

    # Check for unknown keys
    valid_keys = {'csp', 'hsts', 'x_content_type_options'}
    unknown_keys = set(config.keys()) - valid_keys
    if unknown_keys:
        raise ValueError(
            f"{config_name} contains unknown keys: {unknown_keys}"
        )


def _validate_csp_config(config_name: str, csp_config: Dict[str, Any]) -> None:
    """
    Validate CSP configuration dictionary.

    Args:
        config_name: Name of config for error messages
        csp_config: CSP configuration dictionary

    Raises:
        TypeError: If CSP directive values have wrong types
        ValueError: If CSP directive values are invalid
    """
    for directive, sources in csp_config.items():
        if not isinstance(directive, str):
            raise TypeError(
                f"{config_name}['csp'] directive keys must be strings"
            )

        if not isinstance(sources, (list, tuple)):
            raise TypeError(
                f"{config_name}['csp']['{directive}'] must be a list or tuple"
            )

        for i, source in enumerate(sources):
            if not isinstance(source, str):
                raise TypeError(
                    f"{config_name}['csp']['{directive}'][{i}] must be a string"
                )


def _get_merged_config_for_request(app: Flask) -> Dict[str, Any]:
    """
    Get merged configuration for current request.

    Combines default configuration with route-specific overrides,
    performing deep merge for CSP directives.

    Args:
        app: Flask application instance

    Returns:
        Merged configuration dictionary for current request
    """
    config_data = app.extensions.get('advanced_secure_headers', {})
    default_config = config_data.get('default_config', {})
    route_config = config_data.get('route_config', {})

    # Start with deep copy of defaults
    merged = copy.deepcopy(default_config)

    # Find route-specific overrides
    endpoint = request.endpoint
    path = request.path

    # Check both endpoint name and path (path takes precedence)
    route_override = {}
    if endpoint and endpoint in route_config:
        route_override = route_config[endpoint]
    if path in route_config:
        route_override = route_config[path]

    # Merge overrides
    if route_override:
        merged = _deep_merge_configs(merged, route_override)

    return merged


def _deep_merge_configs(
    base_config: Dict[str, Any],
    override_config: Dict[str, Any]
) -> Dict[str, Any]:
    """
    Deep merge two configuration dictionaries.

    Special handling for CSP: merges at directive level rather than
    replacing entire CSP dictionary.

    Args:
        base_config: Base configuration dictionary
        override_config: Override configuration dictionary

    Returns:
        New dictionary with merged configuration
    """
    result = copy.deepcopy(base_config)

    for key, override_value in override_config.items():
        if key == 'csp' and isinstance(override_value, dict):
            # Deep merge CSP directives
            if 'csp' not in result:
                result['csp'] = {}
            elif result['csp'] is None:
                result['csp'] = {}

            # Merge each CSP directive
            base_csp = result.get('csp', {}) or {}
            merged_csp = copy.deepcopy(base_csp)
            merged_csp.update(override_value)
            result['csp'] = merged_csp
        else:
            # Regular override for non-CSP keys
            result[key] = override_value

    return result


def _csp_requires_nonce(csp_config: Dict[str, Any]) -> bool:
    """
    Check if CSP configuration requires nonce generation.

    Args:
        csp_config: CSP configuration dictionary

    Returns:
        True if any directive contains nonce placeholder
    """
    if not isinstance(csp_config, dict):
        return False

    for directive_sources in csp_config.values():
        if isinstance(directive_sources, (list, tuple)):
            for source in directive_sources:
                if isinstance(source, str) and '{nonce}' in source:
                    return True

    return False


def _build_csp_header(
    csp_config: Dict[str, List[str]],
    nonce: Optional[str]
) -> str:
    """
    Build CSP header string from configuration dictionary.

    Args:
        csp_config: Dictionary mapping CSP directives to source lists
        nonce: Current request nonce for substitution

    Returns:
        Complete CSP header string

    Example:
        >>> config = {'default-src': ["'self'"], 'script-src': ["'nonce-{nonce}'"]}
        >>> _build_csp_header(config, 'abc123')
        "default-src 'self'; script-src 'nonce-abc123'"
    """
    if not csp_config:
        return ""

    directive_strings = []

    for directive, sources in csp_config.items():
        if not sources:
            continue

        # Process each source, substituting nonce if needed
        processed_sources = []
        for source in sources:
            if nonce and '{nonce}' in source:
                processed_source = source.replace('{nonce}', nonce)
            else:
                processed_source = source
            processed_sources.append(processed_source)

        # Join sources for this directive
        sources_str = ' '.join(processed_sources)
        directive_strings.append(f"{directive} {sources_str}")

    return '; '.join(directive_strings)

